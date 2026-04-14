from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import requets as rq
from requets import get_goals


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



router = Router()

@router.callback_query(F.data == "create demo")
async def cmd_create_demo(callback: CallbackQuery):
    await callback.message.answer("Let's create demo portfolio!", show_alert=True),
    await callback.message.answer("Tap on /registrate to start creating own demo-portfolio!")

@router.message(Command('registrate'))
async def cmd_ownername(message: Message, state: FSMContext):
    await rq.set_user(message.from_user.id)
    await state.set_state(Reg.name)
    await message.answer("Enter owner's full name")

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
        demo_name=data['name_demo']
    )

    await message.answer(
        f"✅ Demo-portfolio created!\n\n"
        f"Owner: {data['name']}\n"
        f"Portfolio: {data['name_demo']}\n"
        f"Start balance: $10 000\n"
        f"ID: {portfolio_id}"
    )

    await state.clear()



@router.callback_query(F.data == "login demo")
async def cmd_login(callback: CallbackQuery):

    demos = await rq.get_user_portfolios(callback.from_user.id)

    if not demos:
        await callback.message.answer("❌ You have no portfolios yet.")
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = []

    for demo, portfolio in demos:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{demo.name} — ${round(portfolio.cash,2)}",
                callback_data=f"select_portfolio_{portfolio.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="➕ Create New Portfolio",
            callback_data="create_new_portfolio"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="🗑 Delete Portfolio",
            callback_data="delete_portfolio_menu"
        )
    ])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.answer(
        "📂 Choose portfolio:",
        reply_markup=markup
    )



@router.callback_query(F.data.startswith("select_portfolio_"))
async def select_portfolio(callback: CallbackQuery, state: FSMContext):

    portfolio_id = int(callback.data.split("_")[-1])

    portfolio = await rq.get_portfolio(portfolio_id)

    if not portfolio:
        await callback.message.answer("❌ Portfolio not found.")
        return

    await state.update_data(portfolio_id=portfolio.id)

    await callback.message.answer(
        f"✅ Logged in!\n\n"
        f"Portfolio ID: {portfolio.id}\n"
        f"Balance: ${portfolio.cash}",
    )



@router.callback_query(F.data == "delete_portfolio_menu")
async def delete_menu(callback: CallbackQuery):

    demos = await rq.get_user_portfolios(callback.from_user.id)

    if not demos:
        await callback.message.answer("No portfolios to delete.")
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = []

    for demo, portfolio in demos:
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {demo.name}",
                callback_data=f"delete_{portfolio.id}"
            )
        ])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.answer(
        "Select portfolio to delete:",
        reply_markup=markup
    )


@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete(callback: CallbackQuery):

    portfolio_id = int(callback.data.split("_")[-1])

    success = await rq.delete_portfolio(portfolio_id)

    if success:
        await callback.message.answer("🗑 Portfolio deleted.")
    else:
        await callback.message.answer("❌ Error deleting portfolio.")




@router.callback_query(F.data == "goal_settings")
async def goal_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🎯 Enter goal name:")
    await state.set_state(GoalSetup.name)


@router.message(GoalSetup.name)
async def goal_name_input(message: Message, state: FSMContext):
    await state.update_data(goal_name=message.text)
    await message.answer("💰 Enter amount ($):")
    await state.set_state(GoalSetup.amount)



@router.message(GoalSetup.amount)
async def goal_amount_input(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except:
        await message.answer("❌ Enter a valid number.")
        return

    await state.update_data(goal_amount=amount)
    await message.answer("⏳ Enter years to achieve goal:")
    await state.set_state(GoalSetup.years)



@router.message(GoalSetup.years)
async def goal_years_input(message: Message, state: FSMContext):
    try:
        years = int(message.text)
    except:
        await message.answer("❌ Enter a valid number.")
        return

    await state.update_data(goal_years=years)

    await message.answer("⭐ Enter priority (1 = highest):")
    await state.set_state(GoalSetup.priority)


@router.message(GoalSetup.priority)
async def goal_priority_input(message: Message, state: FSMContext):
    try:
        priority = int(message.text)
    except:
        await message.answer("❌ Enter valid number.")
        return

    await state.update_data(goal_priority=priority)

    await message.answer(
        "🕌 Choose compliance:\n\n1. Shariah\n2. Conventional"
    )
    await state.set_state(GoalSetup.compliance)

@router.message(GoalSetup.compliance)
async def goal_compliance_input(message: Message, state: FSMContext):
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")

    text = message.text.lower()

    if text in ["1", "shariah"]:
        compliance = "shariah"
    elif text in ["2", "conventional"]:
        compliance = "conventional"
    else:
        await message.answer("❌ Enter 1 or 2")
        return

    data = await state.get_data()

    goal = {
        "name": data["goal_name"],
        "amount": data["goal_amount"],
        "years": data["goal_years"],
        "priority": data["goal_priority"],
        "compliance": compliance
    }

    goals = await get_goals(portfolio_id)
    await rq.add_goal({
        "portfolio_id": portfolio_id,
        **goal
    })
    await state.update_data(goals=goals)

    await message.answer(f"✅ Goal added ({compliance})!")
    await state.clear()