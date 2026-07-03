import secrets
import string
from typing import Optional
from sqlalchemy import select, update, delete, desc, func
from ProjectDataBase.models import async_session, Owner, ReferralCode, Referral


class ReferralService:
    CODE_LENGTH = 10
    @staticmethod
    def _generate_code(length: int = CODE_LENGTH) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(
            secrets.choice(alphabet)
            for _ in range(length))

    @classmethod
    async def _generate_unique_code(cls) -> str:
        while True:
            code = cls._generate_code()
            exists = await cls.code_exists(code)
            if not exists:
                return code

    @staticmethod
    async def owner_exists(user_id: int) -> bool:
        async with async_session() as session:
            owner = await session.scalar(
                select(Owner).where(Owner.tg_id == user_id))
            return owner is not None

    @staticmethod
    async def code_exists(code: str) -> bool:
        async with async_session() as session:
            row = await session.scalar(
                select(ReferralCode).where(ReferralCode.code == code))
            return row is not None

    @staticmethod
    async def get_code(code: str) -> Optional[ReferralCode]:
        async with async_session() as session:
            return await session.scalar(
                select(ReferralCode).where(ReferralCode.code == code))

    @staticmethod
    async def get_code_by_user(user_id: int) -> Optional[ReferralCode]:
        async with async_session() as session:
            return await session.scalar(
                select(ReferralCode).where(ReferralCode.owner_id == user_id))

    @classmethod
    async def create_code(cls, user_id: int) -> ReferralCode:
        if not await cls.owner_exists(user_id):
            raise ValueError("Owner does not exist.")
        existing = await cls.get_code_by_user(user_id)
        if existing:
            return existing
        code = await cls._generate_unique_code()
        async with async_session() as session:
            obj = ReferralCode(owner_id=user_id, code=code,
                clicks=0, uses=0, reward_given=False)
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    @classmethod
    async def get_or_create_code(cls, user_id: int) -> ReferralCode:
        existing = await cls.get_code_by_user(user_id)
        if existing:
            return existing
        return await cls.create_code(user_id)

    @classmethod
    async def regenerate_code(cls, user_id: int) -> ReferralCode:
        new_code = await cls._generate_unique_code()
        async with async_session() as session:
            await session.execute(
                update(ReferralCode)
                .where(ReferralCode.owner_id == user_id)
                .values(code=new_code))
            await session.commit()
            return await session.scalar(
                select(ReferralCode)
                .where(ReferralCode.owner_id == user_id))

    @staticmethod
    async def delete_code(user_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(
                delete(ReferralCode)
                .where(ReferralCode.owner_id == user_id))
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def increment_click(user_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(
                update(ReferralCode)
                .where(ReferralCode.owner_id == user_id)
                .values(clicks=ReferralCode.clicks + 1))
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def increment_use(user_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(
                update(ReferralCode)
                .where(ReferralCode.owner_id == user_id)
                .values(uses=ReferralCode.uses + 1))
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def decrement_click(user_id: int) -> bool:
        async with async_session() as session:
            row = await session.scalar(
                select(ReferralCode)
                .where(ReferralCode.owner_id == user_id))
            if row is None:
                return False
            new_clicks = max(0, row.clicks - 1)
            await session.execute(
                update(ReferralCode)
                .where(ReferralCode.owner_id == user_id)
                .values(clicks=new_clicks))
            await session.commit()
            return True

    @staticmethod
    async def click_count(user_id: int) -> int:
        row = await ReferralService.get_code_by_user(user_id)
        if row is None:
            return 0
        return row.clicks

    @staticmethod
    async def use_count(user_id: int) -> int:
        row = await ReferralService.get_code_by_user(user_id)
        if row is None:
            return 0
        return row.uses

    @staticmethod
    async def conversion_rate(user_id: int) -> float:
        row = await ReferralService.get_code_by_user(user_id)
        if row is None:
            return 0.0
        if row.clicks == 0:
            return 0.0
        return round(row.uses / row.clicks * 100, 2)

    @staticmethod
    async def statistics(user_id: int) -> dict:
        row = await ReferralService.get_code_by_user(user_id)
        if row is None:
            return {}
        conversion = (round(row.uses/row.clicks * 100, 2)
            if row.clicks else 0)
        return {
            "code": row.code,
            "clicks": row.clicks,
            "uses": row.uses,
            "reward_given": row.reward_given,
            "conversion_rate": conversion}

    @staticmethod
    async def leaderboard(limit: int = 10):
        async with async_session() as session:
            result = await session.scalars(select(ReferralCode)
                .order_by(desc(ReferralCode.uses),
                    desc(ReferralCode.clicks)).limit(limit))
            return list(result)

    @staticmethod
    async def register_referral(
            inviter_id: int,
            invited_id: int) -> Referral:
        if inviter_id == invited_id:
            raise ValueError("Self referral is forbidden.")
        if await ReferralService.invited_already_registered(invited_id):
            raise ValueError("User already invited.")
        if await ReferralService.referral_exists(inviter_id, invited_id):
            raise ValueError("Referral already exists.")
        async with async_session() as session:
            referral = Referral(inviter_id=inviter_id,
                invited_id=invited_id, rewarded=False)
            session.add(referral)
            await session.commit()
            await session.refresh(referral)
            return referral

    @staticmethod
    async def referral_exists(inviter_id: int, invited_id: int) -> bool:
        async with async_session() as session:
            row = await session.scalar(select(Referral)
                .where(Referral.inviter_id == inviter_id,
                    Referral.invited_id == invited_id))
            return row is not None

    @staticmethod
    async def invited_already_registered(invited_id: int) -> bool:
        async with async_session() as session:
            row = await session.scalar(select(Referral)
                .where(Referral.invited_id == invited_id))
            return row is not None

    @staticmethod
    async def inviter_of(invited_id: int) -> Optional[int]:
        async with async_session() as session:
            row = await session.scalar(
                select(Referral)
                .where(Referral.invited_id == invited_id))
            if row is None:
                return None
            return row.inviter_id

    @staticmethod
    async def invited_users(inviter_id: int):
        async with async_session() as session:
            result = await session.scalars(select(Referral)
                .where(Referral.inviter_id == inviter_id)
                .order_by(Referral.created_at.desc()))
            return list(result)

    @staticmethod
    async def invited_count(inviter_id: int) -> int:
        async with async_session() as session:
            result = await session.scalar(select(func.count())
                .select_from(Referral)
                .where(Referral.inviter_id == inviter_id))
            return result or 0

    @staticmethod
    async def delete_referral(invited_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(delete(Referral)
                .where(Referral.invited_id == invited_id))
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def mark_reward_given(invited_id: int):
        async with async_session() as session:
            await session.execute(update(Referral)
                .where(Referral.invited_id == invited_id)
                .values(rewarded=True))
            await session.commit()

    @staticmethod
    async def reward_given(invited_id: int) -> bool:
        async with async_session() as session:
            row = await session.scalar(select(Referral)
                .where(Referral.invited_id == invited_id))
            if row is None:
                return False
            return row.rewarded

    @staticmethod
    async def pending_rewards():
        async with async_session() as session:
            result = await session.scalars(select(Referral)
                .where(Referral.rewarded == False)
                .order_by(Referral.created_at.asc()))
            return list(result)

    @staticmethod
    async def reward_count(inviter_id: int) -> int:
        async with async_session() as session:
            result = await session.scalar(select(func.count())
                .select_from(Referral)
                .where(Referral.inviter_id == inviter_id,
                    Referral.rewarded == True))
            return result or 0

    @staticmethod
    async def validate_code(code: str) -> Optional[ReferralCode]:
        if not code:
            return None
        code = code.strip()
        return await ReferralService.get_code(code)

    @staticmethod
    async def self_referral(user_id: int, code: str) -> bool:
        row = await ReferralService.get_code(code)
        if row is None:
            return False
        return row.owner_id == user_id

    @staticmethod
    async def already_invited(user_id: int) -> bool:
        return await ReferralService.invited_already_registered(user_id)

    @staticmethod
    async def can_use_code(user_id: int, code: str) -> tuple[bool, str]:
        referral = await ReferralService.validate_code(code)
        if referral is None:
            return False, "invalid_code"
        if referral.owner_id == user_id:
            return False, "self_referral"
        if await ReferralService.already_invited(user_id):
            return False, "already_invited"
        return True, "ok"

    @staticmethod
    async def all_codes():
        async with async_session() as session:
            result = await session.scalars(
                select(ReferralCode)
                .order_by(ReferralCode.created_at.desc()))
            return list(result)

    @staticmethod
    async def all_referrals():
        async with async_session() as session:
            result = await session.scalars(
                select(Referral)
                .order_by(Referral.created_at.desc()))
            return list(result)

    @staticmethod
    async def cleanup_invalid() -> int:
        async with async_session() as session:
            codes = await session.scalars(select(ReferralCode))
            removed = 0
            for code in codes:
                owner = await session.scalar(select(Owner)
                    .where(Owner.tg_id == code.owner_id))
                if owner is None:
                    await session.delete(code)
                    removed += 1
            await session.commit()
            return removed

    @staticmethod
    async def reset_statistics(user_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(update(ReferralCode)
                .where(ReferralCode.owner_id == user_id)
                .values(clicks=0, uses=0,
                    reward_given=False))
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def admin_statistics():
        async with async_session() as session:
            codes = await session.scalar(select(func.count()).select_from(ReferralCode))
            clicks = await session.scalar(select(func.coalesce(func.sum(ReferralCode.clicks), 0)))
            uses = await session.scalar(select(func.coalesce(func.sum(ReferralCode.uses), 0)))
            inviters = await session.scalar(select(func.count(func.distinct(Referral.inviter_id))))
            conversion = 0
            if clicks:
                conversion = uses / clicks * 100
            return {
                "codes": codes,
                "clicks": clicks,
                "uses": uses,
                "conversion": conversion,
                "inviters": inviters}