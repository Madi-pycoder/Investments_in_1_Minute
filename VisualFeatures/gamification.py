from datetime import date
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from ProjectDataBase.models import async_session, UserGamification, UserAchievement

router = Router()

XP_ANALYSIS = 30
XP_BUY = 50
XP_SELL = 40
XP_GOAL = 70
XP_PORTFOLIO = 100

LEVELS = {
    1: 0,
    2: 150,
    3: 350,
    4: 700,
    5: 1200,
    6: 2000}

ACHIEVEMENTS = {
    "first_analysis": "Первый анализ",
    "first_etf": "Первый ETF",
    "first_portfolio": "Первый портфель",
    "first_goal": "Первая цель",
    "first_buy": "Первая покупка",
    "analysis_5": "5 анализов",
    "analysis_25": "25 анализов",
    "analysis_100": "100 анализов"}

ANALYSIS_ACHIEVEMENTS = [(1, "first_analysis"),
    (5, "analysis_5"),
    (25, "analysis_25"),
    (100, "analysis_100")]
BUY_ACHIEVEMENTS = [(1, "first_buy")]
SELL_ACHIEVEMENTS = []
GOAL_ACHIEVEMENTS = (1, "first_goal")


def level_from_xp(xp):
    level = 1
    for lvl, required_xp in sorted(LEVELS.items()):
        if xp >= required_xp:
            level = lvl
        else:
            break
    return level


async def ensure_profile(user_id):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile:
            return profile
        profile = UserGamification(
            user_id=user_id, xp=0, level=1, streak_days=0, last_active=None,
            analysis_count=0, buy_count=0, sell_count=0, portfolio_count=0,
            goal_count=0, achievements_count=0)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


async def add_xp(user_id, amount):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        old_level = profile.level
        profile.xp += amount
        profile.level = level_from_xp(profile.xp)
        await session.commit()
        return {
            "old_level": old_level,
            "new_level": profile.level,
            "leveled_up": profile.level > old_level}


async def update_streak(user_id):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        today = date.today()
        if profile.last_active is None:
            profile.streak_days = 1
        else:
            delta = (today - profile.last_active).days
            if delta == 0:
                pass
            elif delta == 1:
                profile.streak_days += 1
            else:
                profile.streak_days = 1
        profile.last_active = today
        await session.commit()
        return profile.streak_days


async def unlock(user_id: int, achievement_key: str):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        exists = await session.scalar(
            select(UserAchievement).where(UserAchievement.user_id == user_id,
                UserAchievement.achievement == achievement_key))
        if exists:
            return False
        session.add(UserAchievement(user_id=user_id, achievement=achievement_key))
        profile.achievement_count += 1
        await session.commit()
        return True


async def _check_counter(user_id: int, current_value: int, achievement_list):
    unlocked = []
    for required, achievement in achievement_list:
        if current_value >= required:
            success = await unlock(user_id, achievement)
            if success:
                unlocked.append(achievement)
    return unlocked


async def check_analysis_achievements(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(
                UserGamification.user_id == user_id))
        if profile is None:
            return []
        return await _check_counter(
            user_id, profile.analysis_count,
            ANALYSIS_ACHIEVEMENTS)


async def check_buy_achievements(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(
                UserGamification.user_id == user_id))
        if profile is None:
            return []
        return await _check_counter(
            user_id, profile.buy_count,
            BUY_ACHIEVEMENTS)


async def check_sell_achievements(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(
                UserGamification.user_id == user_id))
        if profile is None:
            return []
        return await _check_counter(
            user_id, profile.sell_count,
            SELL_ACHIEVEMENTS)


async def check_goal_achievements(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(
                UserGamification.user_id == user_id))
        if profile is None:
            return []
        return await _check_counter(
            user_id, profile.goal_count,
            GOAL_ACHIEVEMENTS)


async def get_profile(user_id):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = await ensure_profile(user_id)
        return profile


async def get_progress(user_id):
    profile = await get_profile(user_id)
    current_level = profile.level
    current_xp = profile.xp
    levels = sorted(LEVELS.items())
    current_required = LEVELS.get(current_level)
    next_required = None
    for lvl, xp in levels:
        if lvl > current_level:
            next_required = xp
            break
    if next_required is None:
        return {
            "level": current_level,
            "xp": current_xp,
            "current": current_required,
            "next": None,
            "progress": 100,
            "remaining": 0}
    gained = current_xp - current_required
    need = next_required - current_required
    progress = int(gained / need * 100)
    return {
        "level": current_level,
        "xp": current_xp,
        "current": current_required,
        "next": next_required,
        "progress": progress,
        "remaining": next_required - current_xp}


async def add_analysis(user_id):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        profile.analysis_count += 1
        await session.commit()
    await add_xp(user_id, XP_ANALYSIS)
    return await check_analysis_achievements(user_id)


async def add_buy(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        profile.buy_count += 1
        await session.commit()
    await add_xp(user_id, XP_BUY)
    return await check_buy_achievements(user_id)


async def add_sell(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        profile.sell_count += 1
        await session.commit()
    await add_xp(user_id, XP_SELL)
    return await check_sell_achievements(user_id)


async def add_goal(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        profile.goal_count += 1
        await session.commit()
    await add_xp(user_id, XP_GOAL)
    return await check_goal_achievements(user_id)


async def add_portfolio(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserGamification).where(UserGamification.user_id == user_id))
        if profile is None:
            profile = UserGamification(user_id=user_id)
            session.add(profile)
            await session.flush()
        profile.portfolio_count += 1
        await session.commit()
    await add_xp(user_id, XP_PORTFOLIO)
    success = await unlock(user_id, "first_portfolio")
    return success


async def get_achievements(user_id: int):
    async with async_session() as session:
        result = await session.scalars(select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at))
        achievements = []
        for ach in result:
            achievements.append({
                "key": ach.achievement,
                "name": ACHIEVEMENTS.get(
                    ach.achievement,
                    ach.achievement),
                "date": ach.unlocked_at})
        return achievements


def build_progress_bar(percent: int, size: int = 10):
    filled = round(percent / 100 * size)
    empty = size - filled
    return "█" * filled + "░" * empty


@router.callback_query(F.data == "achievements")
async def achievements(callback: CallbackQuery):
    profile = await get_profile(callback.from_user.id)
    progress = await get_progress(callback.from_user.id)
    bar = build_progress_bar(progress["progress"])
    achievements = await get_achievements(callback.from_user.id)
    if not achievements:
        await callback.message.answer("🏆 Пока нет достижений.")
        return
    text = (
        f"👤 Ваш профиль\n\n"
        f"⭐ Уровень {progress['level']}\n\n"
        f"XP\n"
        f"{progress['xp']} / "
        f"{progress['next'] if progress['next'] else 'MAX'}\n"
        f"{bar}\n\n"
        f"{progress['progress']}%\n\n"
        f"🔥 Серия дней: {profile.streak_days}\n"
        f"📈 Анализов: {profile.analysis_count}\n"
        f"💰 Покупок: {profile.buy_count}\n"
        f"💸 Продаж: {profile.sell_count}\n"
        f"🎯 Целей: {profile.goal_count}\n"
        f"🏆 Достижения: \n\n")
    for ach in achievements:
        text += f"✅ {ach['name']}\n"
    await callback.message.answer(text)


async def notify_progress(bot, user_id, xp_result, achievements):
    if xp_result["leveled_up"]:
        await bot.send_message(
            user_id,
            f"🎉 Поздравляем!\n\n"
            f"Вы достигли уровня "
            f"{xp_result['new_level']}!")
    for achievement in achievements:
        await bot.send_message(
            user_id,
            f"🏆 Новое достижение!\n\n"
            f"{ACHIEVEMENTS[achievement]}")