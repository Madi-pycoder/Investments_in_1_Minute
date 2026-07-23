import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.cache import (AUTO_INVEST_METRICS_CACHE, AUTO_INVEST_INFLIGHT,
    AUTO_INVEST_LOCKS, CACHE_TTL)
from ProjectDataBase.market_data_service import ensure_utc
from ProfileData.user_profile import (get_portfolio_profile, update_portfolio_profile, get_user_profile,
    create_user_profile, create_portfolio_profile)
from MainEngines.robo_engine import RoboAdvisor
from ProjectDataBase import backend as rq

logger = logging.getLogger(__name__)

async def safe_async(coro, default=None):
    try:
        return await coro
    except Exception as e:
        logger.info("Error:", e)
        return default

def build_metrics_cache_key(portfolio_id, data):
    positions = data.get("positions") or []
    goals = data.get("goals") or []
    pos_key = tuple(sorted(
        (p.ticker, round(float(p.quantity or 0), 4),
        round(float(p.average_price or 0), 2)) for p in positions))
    goals_key = tuple(sorted(
        (g["name"], round(float(g["amount"]), 2), int(g["years"])) for g in goals))
    return portfolio_id, pos_key, goals_key

def get_auto_invest_lock(portfolio_id):
    if portfolio_id not in AUTO_INVEST_LOCKS:
        AUTO_INVEST_LOCKS[portfolio_id] = asyncio.Lock()
    return AUTO_INVEST_LOCKS[portfolio_id]

async def get_cached_metrics(portfolio_id, data):
    cache_key = build_metrics_cache_key(portfolio_id, data)
    now = time.time()
    cached = AUTO_INVEST_METRICS_CACHE.get(cache_key)
    if cached:
        ts, value = cached
        if now - ts < CACHE_TTL:
            return value
    existing_task = AUTO_INVEST_INFLIGHT.get(cache_key)
    if existing_task:
        return await existing_task
    async def compute():
        try:
            metrics = await compute_portfolio_metrics(data)
            AUTO_INVEST_METRICS_CACHE[cache_key] = (time.time(), metrics)
            return metrics
        finally:
            AUTO_INVEST_INFLIGHT.pop(cache_key, None)
    task = asyncio.create_task(compute())
    AUTO_INVEST_INFLIGHT[cache_key] = task
    return await task


def cleanup_metrics_cache():
    now = time.time()
    expired = [
        key for key, (ts, _) in AUTO_INVEST_METRICS_CACHE.items()
        if now - ts > CACHE_TTL]
    for key in expired:
        AUTO_INVEST_METRICS_CACHE.pop(key, None)


def can_run_auto_invest(profile):
    if not profile.last_auto_invest:
        return True
    last = ensure_utc(profile.last_auto_invest)
    return datetime.now(timezone.utc) - last >= timedelta(days=30)


async def run_auto_invest_for_user(user_id, portfolio_id):
    user_profile = await get_user_profile(user_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if not portfolio_profile:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    cleanup_metrics_cache()
    lock = get_auto_invest_lock(portfolio_id)
    async with lock:
        if not portfolio_id:
            return {"ok": False,
            "status": "Ошибка с поиском портфеля"}
        profile = await get_portfolio_profile(portfolio_id)
        if not profile or not profile.auto_invest_enabled:
            return {"ok": False,
            "status": "Авто-инвестирование выключено"}
        data = await load_portfolio_data(portfolio_id)
        if not data:
            return {"ok": False, "status": "no_data"}
        metrics = await get_cached_metrics(portfolio_id, data)
        if not metrics:
            return {"ok": False,
                "status": "Расчёт метрик не удалось"}
        robo = RoboAdvisor(
            user_profile=user_profile,
            portfolio_profile=portfolio_profile,
            metrics=metrics,
            data=data)
        result = robo.build_auto_invest_plan()
        if not result["ok"]:
            return {"ok": False,
                "status": result["status"]}
        plan = result["plan"]
        if not plan:
            return {"ok": False,
                "status": "Не удалось составить план"}
        trades = []
        for item in plan:
            amount = float(item.get("amount", 0))
            ticker = item.get("ticker")
            if not ticker:
                continue
            if amount <= 0:
                continue
            trades.append({
                "ticker": ticker,
                "amount": round(amount, 2),
                "action": "BUY"})
        if not trades:
            return {
                "ok": False,
                "status": "Нету сделок"}
        total_invest = sum(t["amount"] for t in trades)
        if total_invest <= 0:
            return {
                "ok": False,
                "status": "Не было инвестиций"}
        if not can_run_auto_invest(profile):
            return {
                "ok": False,
                "status": "Срок авто-инвестирования не прошёл"}
        fresh_profile = await get_portfolio_profile(portfolio_id)
        if (fresh_profile.next_auto_invest_at
            and fresh_profile.next_auto_invest_at > datetime.now(timezone.utc)):
            return {
                "ok": False,
                "status": "Срок авто-инвестирования не прошёл"}
        success, result, executed_trades = await rq.execute_rebalance(
            portfolio_id, trades)
        if not success:
            return {
                "ok": False,
                "status": result}
        if not executed_trades:
            return {
                "ok": False,
                "status": "Недостаточно средств"}
        now = datetime.now(timezone.utc)
        monthly_budget = profile.monthly_budget
        await rq.deposit_monthly_budget(portfolio_id, monthly_budget)
        await update_portfolio_profile(
            portfolio_id,
            last_auto_invest=now,
            next_auto_invest_at=now + timedelta(days=30))
        return {
            "ok": True,
            "status": "Исполнено",
            "trades": trades,
            "invested": total_invest}