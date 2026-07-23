from aiogram import F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from ProfileData.user_profile import get_user_profile, create_user_profile, update_user_profile
from ReviewsAndReferrals.referral_service import ReferralService
from VisualFeatures import keyboards as kb
from VisualFeatures.gamification import ensure_profile
from ProjectDataBase import backend as rq
from config import REPRESENTATIVE

router = Router()

class Mode(StatesGroup):
    waiting_for_ticker = State()
class WelcomeQuiz(StatesGroup):
    savings = State()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await rq.set_user(message.from_user.id)
    await ensure_profile(message.from_user.id)
    profile = await get_user_profile(message.from_user.id)
    if profile is None:
        profile = await create_user_profile(message.from_user.id)
    await ReferralService.get_or_create_code(message.from_user.id)
    if command.args:
        code = command.args.strip()
        referral = await ReferralService.get_code(code)
        if referral:
            await ReferralService.increment_click(referral.owner_id)
        ok, reason = await ReferralService.can_use_code(message.from_user.id, code)
        if ok:
            await update_user_profile(message.from_user.id, pending_referral_code=code)
        elif reason == "invalid_code":
            await message.answer("❌ К сожалению, ссылка нерабочая")
        elif reason == "self_referral":
            await message.answer("❌ Нельзя использовать собственную ссылку.")
        elif reason == "already_invited":
            await message.answer("❌ Вы уже зарегистрированы по другой ссылке.")
    if profile.welcome_completed:
        await state.clear()
        await message.answer("👋 С возвращением!", reply_markup=kb.maind)
        return
    elif profile.welcome_seen:
        await state.clear()
        await message.answer("👋 С возвращением!", reply_markup=kb.maind)
    else:
        await update_user_profile(message.from_user.id, welcome_seen=False)
        await state.set_state(WelcomeQuiz.savings)
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Большинство инвесторов теряют деньги\n"
            "не потому что рынок плохой,\n"
            "а потому что покупают активы вслепую.\n\n"
            "Давайте быстро посчитаем,\n"
            "сколько это может стоить именно вам.\n\n"
            "💰 Сколько у вас сейчас накоплений?\n\n",
            reply_markup=kb.representative_keyboard)


@router.callback_query(WelcomeQuiz.savings, F.data.in_(REPRESENTATIVE.keys()))
async def welcome_savings(callback: CallbackQuery, state: FSMContext):
    savings = REPRESENTATIVE[callback.data]
    expected_loss = savings * 0.09
    await callback.answer()
    await callback.message.edit_text(
        f"📉 Если инвестировать случайно,\n"
        "или оставлять сбережения без дела,\n"
        "ошибки могут стоить около\n\n"
        f"≈ ₸{expected_loss:,.0f} в год.\n\n"
        "Хорошая новость —\n"
        "многие ошибки можно увидеть заранее.\n\n"
        "👇 Давайте проверим любую известную компанию.")
    await callback.message.answer(
        "Выберите, что хотите проверить:",
        reply_markup=kb.after_welcome_sequence)
    await state.clear()
    await update_user_profile(callback.from_user.id,
        welcome_completed = True)
    profile = await get_user_profile(callback.from_user.id)
    if profile.pending_referral_code:
        referral = await ReferralService.get_code(profile.pending_referral_code)
        if referral:
            await ReferralService.register_referral(inviter_id=referral.owner_id,
                invited_id=callback.from_user.id)
            await ReferralService.increment_use(referral.owner_id)
            await callback.bot.send_message(referral.owner_id,
                "🎉 Новый пользователь полностью завершил регистрацию по вашей ссылке!")
        await update_user_profile(
            callback.from_user.id,
            pending_referral_code=None)


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        portfolio_id = data.get("portfolio_id")
        await state.clear()
        if portfolio_id is not None:
            await state.set_data({ "portfolio_id": portfolio_id})
        await callback.answer()
        await callback.message.answer(
            "🏠 Главное меню", reply_markup=kb.maind)