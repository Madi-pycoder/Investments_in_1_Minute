from datetime import datetime, timezone, timedelta
from typing import Literal
from sqlalchemy import select, update, and_
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ProjectDataBase.models import async_session, GrowthPromoState
from GrowthSystem.content import get_content, get_config, PromoContent, PROMO_CONTENTS


class GrowthService:
    @staticmethod
    async def _get_or_create_state(user_id: int, promo_type: str) -> GrowthPromoState:
        async with async_session() as session:
            state = await session.scalar(
                select(GrowthPromoState).where(
                    and_(GrowthPromoState.user_id == user_id,
                        GrowthPromoState.promo_type == promo_type)))
            if not state:
                state = GrowthPromoState(
                    user_id=user_id,
                    promo_type=promo_type,
                    show_count=0,
                    content_index=0)
                session.add(state)
                await session.commit()
                await session.refresh(state)
            return state

    @staticmethod
    async def should_show_promo(user_id: int, promo_type: str) -> bool:
        state = await GrowthService._get_or_create_state(user_id, promo_type)
        config = get_config(promo_type)
        now = datetime.now(timezone.utc)
        if state.user_action == "subscribed":
            return False
        if state.user_action == "dismissed":
            return False
        if state.show_count >= config["max_shows"]:
            return False
        if state.cooldown_until and state.cooldown_until > now:
            return False
        return True

    @staticmethod
    async def record_promo_shown(user_id: int, promo_type: str) -> None:
        async with async_session() as session:
            state = await session.scalar(
                select(GrowthPromoState).where(
                    and_(GrowthPromoState.user_id == user_id,
                        GrowthPromoState.promo_type == promo_type)))
            if state:
                state.show_count += 1
                state.last_shown_at = datetime.now(timezone.utc)
                await session.commit()

    @staticmethod
    async def record_user_action(user_id: int, promo_type: str,
        action: Literal["subscribed", "later", "dismissed", "seen"]) -> None:
        async with async_session() as session:
            state = await session.scalar(
                select(GrowthPromoState).where(
                    and_(GrowthPromoState.user_id == user_id,
                        GrowthPromoState.promo_type == promo_type)))
            if not state:
                return
            state.user_action = action
            state.last_action_at = datetime.now(timezone.utc)
            config = get_config(promo_type)
            if action == "later":
                cooldown_days = config.get("later_cooldown_days", 3)
                state.cooldown_until = datetime.now(timezone.utc) + timedelta(days=cooldown_days)
            elif action == "subscribed":
                state.cooldown_until = None
            elif action == "dismissed":
                state.cooldown_until = None
            elif action == "seen":
                cooldown_days = config.get("base_cooldown_days", 7)
                state.cooldown_until = datetime.now(timezone.utc) + timedelta(days=cooldown_days)
            await session.commit()

    @staticmethod
    async def get_next_content(user_id: int, promo_type: str) -> PromoContent:
        state = await GrowthService._get_or_create_state(user_id, promo_type)
        content = get_content(promo_type, state.content_index)
        async with (async_session() as session):
            state_obj = await session.scalar(
                select(GrowthPromoState).where(
                    and_(GrowthPromoState.user_id == user_id,
                        GrowthPromoState.promo_type == promo_type)))
            if state_obj:
                state_obj.content_index = (state_obj.content_index + 1) % len(PROMO_CONTENTS[promo_type])
                await session.commit()
        return content

    @staticmethod
    async def reset_cooldown(user_id: int, promo_type: str) -> None:
        async with async_session() as session:
            await session.execute(
                update(GrowthPromoState)
                .where(and_(GrowthPromoState.user_id == user_id,
                    GrowthPromoState.promo_type == promo_type)).values(cooldown_until=None))
            await session.commit()

    @staticmethod
    async def try_show_promo(message: Message, promo_type: str, trigger: str) -> bool:
        if not await GrowthService.should_show_promo(message.from_user.id, promo_type):
            return False
        content = await GrowthService.get_next_content(message.from_user.id, promo_type)
        keyboard = GrowthService._build_keyboard(promo_type, trigger, content.button_url)
        await message.answer(
            content.text,
            reply_markup=keyboard)
        await GrowthService.record_promo_shown(message.from_user.id, promo_type)
        return True

    @staticmethod
    def _build_keyboard(promo_type: str, trigger: str, button_url: str | None) -> InlineKeyboardMarkup:
        buttons = []
        if button_url:
            buttons.append([
                InlineKeyboardButton(
                    text="📚 Посмотреть канал",
                    url=button_url)])
        buttons.append([
            InlineKeyboardButton(
                text="✅ Уже подписан",
                callback_data=f"growth_{promo_type}_subscribed_{trigger}")])
        buttons.append([
            InlineKeyboardButton(
                text="⏰ Позже",
                callback_data=f"growth_{promo_type}_later_{trigger}")])
        buttons.append([
            InlineKeyboardButton(
                text="🚫 Не предлагать",
                callback_data=f"growth_{promo_type}_dismissed_{trigger}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    async def get_stats(user_id: int, promo_type: str) -> dict:
        async with async_session() as session:
            state = await session.scalar(
                select(GrowthPromoState).where(
                    and_(GrowthPromoState.user_id == user_id,
                        GrowthPromoState.promo_type == promo_type)))
            if not state:
                return {
                    "show_count": 0,
                    "last_shown_at": None,
                    "user_action": None,
                    "cooldown_until": None}
            return {
                "show_count": state.show_count,
                "last_shown_at": state.last_shown_at.isoformat() if state.last_shown_at else None,
                "user_action": state.user_action,
                "cooldown_until": state.cooldown_until.isoformat() if state.cooldown_until else None}