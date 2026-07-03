from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from ReviewsAndReferrals.referral_service import ReferralService
from VisualFeatures import keyboards as kb
router = Router()

@router.message(Command("referral"))
async def referral(message: Message):
    referral = await ReferralService.get_or_create_code(message.from_user.id)
    bot_name = (await message.bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={referral.code}"
    await message.answer(
        f"🎁 Ваша реферальная ссылка\n\n"
        f"`{link}`\n\n"
        f"Код:\n"
        f"`{referral.code}`\n\n"
        f"🎁 За каждого приглашённого друга:\n\n"
        f"✅ друг получает бесплатный гайд\n\n"
        f"Вы помогаете развитию проекта ❤️",
        reply_markup=kb.referral_menu)


@router.message(Command("refstats"))
async def referral_stats(message: Message):
    stats = await ReferralService.statistics(message.from_user.id)
    if not stats:
        await message.answer("У вас ещё нет реферального кода.")
        return
    await message.answer(
        f"📊 Статистика\n\n"
        f"👆 Клики: {stats['clicks']}\n"
        f"👥 Регистрации: {stats['uses']}\n"
        f"📈 Конверсия: {stats['conversion_rate']}%")


@router.message(Command("reftop"))
async def referral_top(message: Message):
    leaders = await ReferralService.leaderboard()
    if not leaders:
        await message.answer("Пока никто никого не пригласил.")
        return
    text = "🏆 Топ приглашений\n\n"
    for i, user in enumerate(leaders, start=1):
        text += (
            f"{i}. {user.owner_id}\n"
            f"👥 {user.uses} | 👆 {user.clicks}\n\n")
    await message.answer(text)


@router.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery):
    referral = await ReferralService.get_or_create_code(callback.from_user.id)
    bot_name = (await callback.bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={referral.code}"
    await callback.message.edit_text(
        f"🎁 Ваша ссылка\n\n"
        f"`{link}`\n\n"
        f"🎁 За каждого приглашённого друга:\n\n"
        f"✅ друг получает бесплатный гайд\n\n"
        f"Вы помогаете развитию проекта ❤️",
        parse_mode="Markdown",
        reply_markup=kb.referral_menu)
    await callback.answer()


@router.callback_query(F.data == "regenerate_referral")
async def regenerate(callback: CallbackQuery):
    referral = await ReferralService.regenerate_code(callback.from_user.id)
    bot_name = (await callback.bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={referral.code}"
    await callback.message.edit_text(
        "✅ Ссылка обновлена\n\n"
        f"`{link}`\n\n"
        f"🎁 За каждого приглашённого друга:\n\n"
        f"✅ друг получает бесплатный гайд\n\n"
        f"Вы помогаете развитию проекта ❤️",
        parse_mode="Markdown",
        reply_markup=kb.referral_menu)
    await callback.answer("Готово")


@router.callback_query(F.data == "referral_stats")
async def callback_stats(callback: CallbackQuery):
    stats = await ReferralService.statistics(callback.from_user.id)
    if not stats:
        await callback.answer("Нет данных")
        return
    await callback.message.edit_text(
        f"📊 Статистика\n\n"
        f"👆 Клики: {stats['clicks']}\n"
        f"👥 Регистрации: {stats['uses']}\n"
        f"📈 Конверсия: {stats['conversion_rate']}%",
        reply_markup=kb.referral_menu)
    await callback.answer()