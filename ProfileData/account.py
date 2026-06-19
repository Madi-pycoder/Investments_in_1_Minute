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
            "💼 Create your free demo portfolio\n\n"
            
            "With portfolio you can:\n"
            "• Track investments\n"
            "• Get AI advice\n"
            "• Build monthly plans\n"
            "• Set goals\n"
            "• Rebalance automatically")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Create Portfolio",
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
            text="➕ New Portfolio",
            callback_data="create_demo")])
    keyboard.append([
        InlineKeyboardButton(
            text="🗑 Delete Portfolio",
            callback_data="delete_portfolio_menu")])
    await callback.message.answer(
        "📂 Choose portfolio:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("select_portfolio_"))
async def select_portfolio(callback: CallbackQuery, state: FSMContext):
    portfolio_id = int(callback.data.split("_")[-1])
    portfolio = await rq.get_portfolio(portfolio_id)
    if not portfolio:
        await callback.message.answer("❌ Portfolio not found.")
        return
    await state.set_data({"portfolio_id": portfolio_id})
    positions = await rq.get_positions(portfolio_id)
    goals = await rq.get_goals(portfolio_id)
    print("PORTFOLIO ID:", portfolio_id)
    print("GOALS COUNT:", len(goals))
    total_positions = len(positions)
    text = (
        f"💼 Portfolio connected\n\n"
        f"💵 Cash: ${portfolio.cash:,.2f}\n"
        f"📦 Positions: {total_positions}\n"
        f"🎯 Goals: {len(goals)}\n\n")
    if not goals:
        text += "🎯 Next step:\nAdd your first goal"
    elif not positions:
        text += "📈 Next step:\nAdd your first investment"
    else:
        text += "⚡ Next step:\nReview AI recommendations"
    await callback.message.answer(text, reply_markup=kb.portfolio_dashboard)


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
        "Choose portfolio to delete:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data.startswith("delete_portfolio_"))
async def delete_portfolio(callback: CallbackQuery):
    portfolio_id = int(callback.data.split("_")[-1])
    await rq.delete_portfolio(portfolio_id)
    await callback.message.answer("✅ Portfolio deleted.")


@router.callback_query(F.data == "create_demo")
async def cmd_create_demo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await rq.set_user(callback.from_user.id)
    await state.set_state(Reg.name)
    await callback.message.answer("👤 Enter your name:")

@router.message(Reg.name)
async def cmd_demoname(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Reg.name_demo)
    await message.answer("Enter demo-portfolio's full name")

@router.message(Reg.name_demo)
async def cmd_regend(message: Message, state: FSMContext):
    await state.update_data(name_demo=message.text)
    data = await state.get_data()
    portfolio_id = await rq.create_demo_portfolio(
        tg_id=message.from_user.id,
        owner_name=data['name'],
        demo_name=data['name_demo'])
    await message.answer(
        f"✅ Demo-portfolio created!\n\n"
        f"Owner: {data['name']}\n"
        f"Portfolio: {data['name_demo']}\n"
        f"Start balance: $10 000\n"
        f"ID: {portfolio_id}")
    await state.clear()
    await state.update_data(portfolio_id=portfolio_id)
    await message.answer(
        "🚀 Your portfolio is ready!\n\n"
        "You can now:\n"
        "• Analyze portfolio\n"
        "• Get AI recommendations\n"
        "• Set financial goals\n"
        "• Auto-rebalance investments\n"
        "• Build monthly plans",
        reply_markup=kb.portfolio_dashboard)

@router.callback_query(F.data == "goal_settings")
async def goal_start(callback: CallbackQuery,state: FSMContext):
    await callback.answer()
    await state.set_state(GoalQuiz.waiting_goal)
    await callback.message.answer("🎯 Choose your goal:",reply_markup=kb.goal_name_quiz)


@router.callback_query(GoalQuiz.waiting_goal,F.data.startswith("goal_"))
async def goal_pick(callback: CallbackQuery, state: FSMContext):
    goal_name = callback.data.replace("goal_", "")
    if goal_name == "custom":
        await state.set_state(
            GoalQuiz.custom_goal_name)
        await callback.message.answer("Enter custom goal name:")
        return
    await state.update_data(goal_name=goal_name)
    await state.set_state(GoalQuiz.waiting_amount)
    await callback.message.answer("💰 Choose target amount:", reply_markup=kb.goal_amount_quiz)

@router.message(GoalQuiz.custom_goal_name)
async def custom_goal_name(message: Message, state: FSMContext):
    await state.update_data(goal_name=message.text)
    await state.set_state(GoalQuiz.waiting_amount)
    await message.answer("💰 Choose target amount:",
        reply_markup=kb.goal_amount_quiz)



@router.callback_query(GoalQuiz.waiting_amount,F.data.startswith("amount_"),F.data != "amount_custom")
async def goal_amount(callback: CallbackQuery, state: FSMContext):
    amount = int(callback.data.replace("amount_", ""))
    await state.update_data(goal_amount=amount)
    await state.set_state(GoalQuiz.waiting_timeline)
    await callback.message.answer("⏳ Choose timeline:", reply_markup=kb.goal_timeline)

@router.callback_query(GoalQuiz.waiting_amount, F.data == "amount_custom")
async def custom_goal_amount_start(callback: CallbackQuery,state: FSMContext):
    await state.set_state(GoalQuiz.custom_goal_amount)
    await callback.message.answer("💰 Enter custom target amount:")

@router.message(GoalQuiz.custom_goal_amount)
async def custom_goal_amount(message: Message,state: FSMContext):
    try: amount = float(message.text)
    except:
        await message.answer("❌ Enter valid number.")
        return
    await state.update_data(goal_amount=amount)
    await state.set_state(GoalQuiz.waiting_timeline)
    await message.answer("⏳ Choose timeline:", reply_markup=kb.goal_timeline)

@router.callback_query(GoalQuiz.waiting_timeline,F.data.startswith("timeline_"))
async def goal_timeline(callback: CallbackQuery, state: FSMContext):
    timeline = callback.data.replace(
        "timeline_",
        "")
    if timeline == "custom":
        await state.set_state(GoalQuiz.custom_goal_timeline)
        await callback.message.answer("Enter custom timeline in years:")
        return
    await state.update_data(goal_timeline=int(timeline))
    await state.set_state(GoalQuiz.waiting_compliance)
    await callback.message.answer("🕌 Choose compliance:",
        reply_markup=kb.goal_compliance)

@router.message(GoalQuiz.custom_goal_timeline)
async def custom_goal_timeline(message: Message, state: FSMContext):
    try: years = int(message.text)
    except:
        await message.answer("Enter valid number.")
        return
    await state.update_data(goal_timeline=years)
    await state.set_state(GoalQuiz.waiting_compliance)
    await message.answer("🕌 Choose compliance:",
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
        f"✅ Goal created!\n\n"
        f"🎯 {goal['name']}\n"
        f"💰 ${goal['amount']}\n"
        f"⏳ {goal['years']} years\n"
        f"🕌 {compliance.title()}",
        reply_markup=kb.portfolio_dashboard)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="goal_created",
            category="portfolio",
            event_data={
                "goal": goal["name"],
                "years": goal["years"],
                "amount": goal["amount"]}))




@router.message(ProfileSetup.income)
async def profile_income(message: Message, state: FSMContext):
    try:
        income = float(message.text)
    except:
        await message.answer("❌ Enter a valid number")
        return
    await update_user_profile(message.from_user.id, income=income)
    await state.set_state(ProfileSetup.budget)
    await message.answer(
        "💸 How much do you want to invest monthly?")


@router.message(ProfileSetup.budget)
async def profile_budget(message: Message, state: FSMContext):
    try:
        budget = float(message.text)
    except:
        await message.answer("❌ Enter a valid number")
        return
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    await update_portfolio_profile(
        portfolio_id, monthly_budget=budget)
    await state.set_state(ProfileSetup.risk)
    await message.answer(
        "📊 What's your risk level?\n\n"
        "low / medium / high")



@router.message(ProfileSetup.risk)
async def profile_risk(message: Message, state: FSMContext):
    risk = message.text.lower().strip()
    if risk not in ["low", "medium", "high"]:
        await message.answer("❌ Choose: low / medium / high")
        return
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    await update_portfolio_profile(
        portfolio_id, risk_tolerance=risk)
    await state.clear()
    await message.answer("✅ Profile ready! Building plan...")
    text, keyboard = await build_auto_invest_response(
        message.from_user.id, portfolio_id)
    await message.answer(text, reply_markup=keyboard)