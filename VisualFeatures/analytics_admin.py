from aiogram.types import Message
from aiogram import Router
from aiogram.filters import Command
from ProjectDataBase.analytics import AnalyticsService
from ReviewsAndReferrals.referral_service import ReferralService
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("analytics"))
async def analytics_cmd(message: Message):
    logger.info("MY_ID = ", message.from_user.id)
    logger.info("ADMIN_ID = ", ADMIN_ID)
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ You are not admin")
        return
    await message.answer("START")
    data = await AnalyticsService.get_dashboard()
    ref_stats = await ReferralService.admin_statistics()
    text = f"""
📊 Analytics

👥 Users: {data["users"]}
📁 Portfolios: {data["portfolios"]}
🧮 Rebalances: {data["quantity"]}
🎯 Goals: {data["goals"]}

🆕 New today: {data["new_1d"]}
🆕 New 7d: {data["new_7d"]}
🆕 New 30d: {data["new_30d"]}
🆕 New 90d: {data["new_90d"]}

📈 DAU: {data["dau"]}
📈 WAU: {data["wau"]}
📈 MAU: {data["mau"]}

📈 WoW: {data["wow"]}
📈 MoM: {data["mom"]}

⚡ Activation:
{data["activation"]:.1%}

🔁 Retention D1:
{data["retention1"]:.1%}
🔁 Retention 1W:
{data["retention7"]:.1%}
🔁 Retention 1M:
{data["retention30"]:.1%}
🔁 Retention 3M:
{data["retention90"]:.1%}

📉 Churn:
{data["churn"]:.1%}

💰 Avg portfolio:
${data["avg_portfolio"]}

🎯 Avg goals:
{data["avg_goals"]}

💳 Avg deals:
{data["avg_deals"]}

📡 Events:
{data["events"]}




🎁 Referrals

Codes:

{ref_stats["codes"]}

Clicks:

{ref_stats["clicks"]}

Registrations:

{ref_stats["uses"]}

Conversion:

{ref_stats["conversion"]:.1f}%

Unique inviters:

{ref_stats["inviters"]}
"""
    await message.answer(text)



@router.message(Command("events"))
async def events_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    events = await AnalyticsService.latest_events()
    text = "📡 Last events\n\n"
    for e in events:
        text += (
            f"{e.created_at:%H:%M:%S} "
            f"{e.user_id} "
            f"{e.event_name} "
            f"{'✅' if e.success else '❌'}\n")
    await message.answer(text)



@router.message(Command("funnel"))
async def funnel_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    f = await AnalyticsService.get_funnel()
    total = max(f["total"], 1)
    text = f"""
🚀 Funnel

Users:

{f["total"]}

↓

Welcome:

{f["welcome"]}

({f["welcome"]/total:.1%})

↓

Portfolio:

{f["portfolio"]}

({f["portfolio"]/total:.1%})

↓

Analysis:

{f["analysis"]}

({f["analysis"]/total:.1%})

↓

Auto Invest:

{f["invest"]}

({f["invest"]/total:.1%})
"""
    await message.answer(text)