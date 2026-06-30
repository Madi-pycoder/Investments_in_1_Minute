import asyncio
from aiogram import F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ProjectDataBase.analytics import AnalyticsService
from ProfileData.profile_states import ProfileSetup
from ProfileData.user_profile import update_user_profile, update_portfolio_profile
from Portfolio_Handlers.portfolio_auto_handler import build_auto_invest_response
from ProjectDataBase import backend as rq
from VisualFeatures import keyboards as kb


class Reg(StatesGroup):
    name = State()
    name_demo = State()

class Log(StatesGroup):
    name = State()
    name_demo = State()

class GoalSetup(StatesGroup):
    name = State()
    amount = State()
    years = State()
    priority = State()
    compliance = State()

class GoalQuiz(StatesGroup):
    waiting_goal = State()
    waiting_amount = State()
    waiting_timeline = State()
    waiting_compliance = State()
    custom_goal_name = State()
    custom_goal_amount = State()
    custom_goal_timeline = State()

router = Router()

@router.callback_query(F.data == "portfolio_hub")
async def portfolio_hub(callback: CallbackQuery):
    demos = await rq.get_user_portfolios(callback.from_user.id)
    if not demos:
        text = (
            "💼 Создайте учебный портфель\n\n"
            "Он поможет вам:\n"
            "• Следить за инвестициями\n"
            "• Получать рекомендации\n"
            "• Планировать вложения\n"
            "• Ставить финансовые цели\n"
            "• Проверять состав портфеля")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Создать портфель",
                        callback_data="create_demo")]])
        await callback.message.answer(
            text,
            reply_markup=keyboard)
        return
    keyboard = []
    for demo, portfolio in demos:
        keyboard.append([
            InlineKeyboardButton(
                text=f"💼 {demo.name} • ${round(portfolio.cash, 2)}",
                callback_data=f"select_portfolio_{portfolio.id}"),])
    keyboard.append([
        InlineKeyboardButton(
            text="➕ Создать новый портфель",
            callback_data="create_demo")])
    keyboard.append([
        InlineKeyboardButton(
            text="🗑 Удалить портфель",
            callback_data="delete_portfolio_menu")])
    await callback.message.answer(
        "📂 Выберите портфель:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("select_portfolio_"))
async def select_portfolio(callback: CallbackQuery, state: FSMContext):
    portfolio_id = int(callback.data.split("_")[-1])
    portfolio = await rq.get_portfolio(portfolio_id)
    if not portfolio:
        await callback.message.answer("❌ Портфель не найден")
        return
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="portfolio.opened",
            category="funnel",
            event_data={
                "portfolio_id": portfolio_id}))
    await state.set_data({"portfolio_id": portfolio_id})
    positions = await rq.get_positions(portfolio_id)
    goals = await rq.get_goals(portfolio_id)
    print("PORTFOLIO ID:", portfolio_id)
    print("GOALS COUNT:", len(goals))
    total_positions = len(positions)
    text = (
        f"💼 Портфель открыт\n\n"
        f"💵 Свободные средства: ${portfolio.cash:,.2f}\n"
        f"📦 Активов: {total_positions}\n"
        f"🎯 Целей: {len(goals)}\n\n")
    if not goals:
        text += ("🎯 Следующий шаг:\n"
                 "Добавтье первую цель")
    elif not positions:
        text += ("📈 Следующий шаг:\n"
                 "Добавьте первый актив")
    else:
        text += ("⚡ Следующий шаг:\n"
                 "Посмотрите рекомендации")
    await callback.message.answer(text,
        reply_markup=kb.portfolio_dashboard)


@router.callback_query(F.data == "delete_portfolio_menu")
async def delete_portfolio_menu(callback: CallbackQuery):
    demos = await rq.get_user_portfolios(callback.from_user.id)
    keyboard = []
    for demo, portfolio in demos:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🗑 {demo.name}",
                callback_data=f"delete_portfolio_{portfolio.id}")])
    await callback.message.answer(
        "Выберите портфель для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data.startswith("delete_portfolio_"))
async def delete_portfolio(callback: CallbackQuery):
    portfolio_id = int(callback.data.split("_")[-1])
    await rq.delete_portfolio(portfolio_id)
    await callback.message.answer("✅ Портфель удалён")


@router.callback_query(F.data == "create_demo")
async def cmd_create_demo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await rq.set_user(callback.from_user.id)
    await state.set_state(Reg.name)
    await callback.message.answer("👤 Как вас зовут?")

@router.message(Reg.name)
async def cmd_demoname(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Reg.name_demo)
    await message.answer("📝 Придумайте название портфеля")

@router.message(Reg.name_demo)
async def cmd_regend(message: Message, state: FSMContext):
    await state.update_data(name_demo=message.text)
    data = await state.get_data()
    portfolio_id = await rq.create_demo_portfolio(
        tg_id=message.from_user.id,
        demo_name=data['name_demo'])
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=message.from_user.id,
            event_name="portfolio.created",
            category="funnel",
            event_data={"portfolio_id": portfolio_id}))
    await message.answer(
        f"✅ Портфель создан!\n\n"
        f"👤 Владелец: {data['name']}\n"
        f"💼 Название: {data['name_demo']}\n"
        f"💵 Стартовый баланс: $10 000\n"
        f"🆔 ID: {portfolio_id}")
    await state.clear()
    await state.update_data(portfolio_id=portfolio_id)
    await message.answer(
        "🎉 Портфель создан.\n\n"
        "Теперь бот сможет:\n"
        "✅ подсказывать ошибки\n"
        "✅ предлагать улучшения\n"
        "✅ рассчитывать распределение\n\n"
        "👇 Попробуйте первую рекомендацию",
        reply_markup=kb.after_create_demo)

@router.callback_query(F.data == "goal_settings")
async def goal_start(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    if not portfolio_id:
        await callback.message.answer("❌ Портфель не найден. Откройте портфель заново.")
        return
    await state.update_data(portfolio_id=portfolio_id)
    await callback.answer()
    await state.set_state(GoalQuiz.waiting_goal)
    await callback.message.answer(
        "🎯 Для чего вы инвестируете?",
        reply_markup=kb.goal_name_quiz)


@router.callback_query(GoalQuiz.waiting_goal,F.data.startswith("goal_"))
async def goal_pick(callback: CallbackQuery, state: FSMContext):
    goal_name = callback.data.replace("goal_", "")
    if goal_name == "custom":
        await state.set_state(
            GoalQuiz.custom_goal_name)
        await callback.message.answer("✍️ Введите название цели:")
        return
    await state.update_data(goal_name=goal_name)
    await state.set_state(GoalQuiz.waiting_amount)
    await callback.message.answer("💰 Какую сумму хотите накопить?",
        reply_markup=kb.goal_amount_quiz)

@router.message(GoalQuiz.custom_goal_name)
async def custom_goal_name(message: Message, state: FSMContext):
    await state.update_data(goal_name=message.text)
    await state.set_state(GoalQuiz.waiting_amount)
    await message.answer("💰 Какую сумму хотите накопить?",
        reply_markup=kb.goal_amount_quiz)



@router.callback_query(GoalQuiz.waiting_amount,F.data.startswith("amount_"),F.data != "amount_custom")
async def goal_amount(callback: CallbackQuery, state: FSMContext):
    amount = int(callback.data.replace("amount_", ""))
    await state.update_data(goal_amount=amount)
    await state.set_state(GoalQuiz.waiting_timeline)
    await callback.message.answer("⏳ За какой срок хотите достичь цели?",
        reply_markup=kb.goal_timeline)

@router.callback_query(GoalQuiz.waiting_amount, F.data == "amount_custom")
async def custom_goal_amount_start(callback: CallbackQuery,state: FSMContext):
    await state.set_state(GoalQuiz.custom_goal_amount)
    await callback.message.answer("💰 Какую сумму хотите накопить?")

@router.message(GoalQuiz.custom_goal_amount)
async def custom_goal_amount(message: Message,state: FSMContext):
    try:
        amount = float(message.text)
    except Exception:
        await message.answer("❌ Введите корректное число")
        return
    await state.update_data(goal_amount=amount)
    await state.set_state(GoalQuiz.waiting_timeline)
    await message.answer("⏳ За какой срок хотите достичь цели?", reply_markup=kb.goal_timeline)

@router.callback_query(GoalQuiz.waiting_timeline,F.data.startswith("timeline_"))
async def goal_timeline(callback: CallbackQuery, state: FSMContext):
    timeline = callback.data.replace(
        "timeline_",
        "")
    if timeline == "custom":
        await state.set_state(GoalQuiz.custom_goal_timeline)
        await callback.message.answer("⏳ За какой срок хотите достичь цели?\n\n"
            "Введите срок в годах")
        return
    await state.update_data(goal_timeline=int(timeline))
    await state.set_state(GoalQuiz.waiting_compliance)
    await callback.message.answer("🕌 Учитывать исламские ограничения?",
        reply_markup=kb.goal_compliance)

@router.message(GoalQuiz.custom_goal_timeline)
async def custom_goal_timeline(message: Message, state: FSMContext):
    try:
        years = int(message.text)
    except Exception:
        await message.answer("❌ Введите корректное число")
        return
    await state.update_data(goal_timeline=years)
    await state.set_state(GoalQuiz.waiting_compliance)
    await message.answer("🕌 Учитывать исламские ограничения?",
        reply_markup=kb.goal_compliance)

@router.callback_query(GoalQuiz.waiting_compliance,F.data.startswith("compliance_"))
async def goal_finish(callback: CallbackQuery, state: FSMContext):
    compliance = callback.data.replace("compliance_","")
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    goal = {
        "portfolio_id": portfolio_id,
        "name": data["goal_name"],
        "amount": data["goal_amount"],
        "years": data["goal_timeline"],
        "priority": 2,
        "compliance": compliance}
    await rq.add_goal(goal)
    await state.clear()
    await state.set_data({"portfolio_id": portfolio_id})
    await callback.message.answer(
        "🎯 Отлично.\n\n"
        "Теперь портфель знает,\n"
        "ради чего вы инвестируете.\n\n"
        "Теперь можно автоматически проверять,\n"
        "успеваете ли вы к своей цели.",
        reply_markup=kb.after_create_goal)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="goal.created",
            category="portfolio",
            event_data={
                "goal": goal["name"],
                "years": goal["years"],
                "amount": goal["amount"]}))




@router.message(ProfileSetup.income)
async def profile_income(message: Message, state: FSMContext):
    try:
        income = float(message.text)
    except Exception:
        await message.answer("❌ Введите корректное число")
        return
    await update_user_profile(message.from_user.id, income=income)
    await state.set_state(ProfileSetup.budget)
    await message.answer("💸 Сколько готовы инвестировать каждый месяц?")


@router.message(ProfileSetup.budget)
async def profile_budget(message: Message, state: FSMContext):
    try:
        budget = float(message.text)
    except Exception:
        await message.answer("❌ Введите корректное число")
        return
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    await update_portfolio_profile(
        portfolio_id, monthly_budget=budget)
    await state.set_state(ProfileSetup.risk)
    await message.answer(
        "📊 Какой риск вам комфортен?\n\n"
        "🟢 низкий\n"
        "🟡 средний\n"
        "🔴 высокий")



@router.message(ProfileSetup.risk)
async def profile_risk(message: Message, state: FSMContext):
    risk = message.text.lower().strip()
    if risk not in ["низкий", "средний", "высокий"]:
        await message.answer("❌ Выберите: низкий, средний или высокий риск")
        return
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    await update_portfolio_profile(
        portfolio_id, risk_tolerance=risk)
    await state.clear()
    await message.answer("✅ Профиль настроен!\n\n"
        "Составляю ваш инвестиционный план...")
    text, keyboard = await build_auto_invest_response(
        message.from_user.id, portfolio_id)
    await message.answer(text, reply_markup=keyboard)