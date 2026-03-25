from sqlalchemy import select
from models import async_session
from models import Owner, Demo, Portfolio, Position, Transaction



async def set_user(tg_id: int):
    async with async_session() as session:

        user = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id)
        )

        if not user:
            session.add(Owner(tg_id=tg_id))
            await session.commit()




async def create_demo_portfolio(tg_id: int, owner_name: str, demo_name: str):

    async with async_session() as session:

        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id)
        )

        if not owner:
            return None


        portfolio = Portfolio(
            owner_id=owner.id,
            cash=10000.0
        )

        session.add(portfolio)
        await session.flush()

        demo = Demo(
            name=demo_name,
            portfolio_id=portfolio.id
        )

        session.add(demo)

        await session.commit()

        return portfolio.id


async def buy_position(portfolio_id, ticker, qty, price, category_id):
    async with async_session() as session:

        existing = await session.scalar(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.ticker == ticker
            )
        )

        if existing:
            total_qty = existing.quantity + qty
            new_avg = (
                (existing.quantity * existing.average_price + qty * price)
                / total_qty
            )

            existing.quantity = total_qty
            existing.average_price = new_avg
        else:
            new_position = Position(
                portfolio_id=portfolio_id,
                ticker=ticker,
                quantity=qty,
                average_price=price,
                category_id=category_id
            )
            session.add(new_position)

        await session.commit()


async def sell_position(portfolio_id, ticker, qty):
    async with async_session() as session:

        position = await session.scalar(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.ticker == ticker
            )
        )

        if not position:
            return False, "No position"

        if position.quantity < qty:
            return False, "Not enough shares"

        position.quantity -= qty

        if position.quantity == 0:
            await session.delete(position)

        await session.commit()

        return True, "ok"


async def add_transaction(portfolio_id, ticker, qty, price, is_buy):

    async with async_session() as session:

        tr = Transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=qty,
            price=price,
            is_buy=is_buy
        )

        session.add(tr)
        await session.commit()

async def get_portfolio(portfolio_id):

    async with async_session() as session:

        return await session.scalar(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )



async def get_positions(portfolio_id):

    async with async_session() as session:

        result = await session.scalars(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )

        return result.all()



async def get_user_portfolios(tg_id: int):
    async with async_session() as session:

        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id)
        )

        if not owner:
            return []

        result = await session.execute(
            select(Demo, Portfolio)
            .join(Portfolio, Demo.portfolio_id == Portfolio.id)
            .where(Portfolio.owner_id == owner.id)
        )

        return result.all()


async def login_demo_portfolio(tg_id: int, demo_name: str):

    async with async_session() as session:

        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id)
        )

        if not owner:
            return None, "User not found"

        demo = await session.scalar(
            select(Demo).where(Demo.name == demo_name)
        )

        if not demo:
            return None, "Demo not found"

        portfolio = await session.scalar(
            select(Portfolio).where(Portfolio.id == demo.portfolio_id)
        )

        if not portfolio:
            return None, "Portfolio not found"

        return portfolio, "ok"



async def update_cash(portfolio_id: int, new_cash: float):
    async with async_session() as session:
        portfolio = await session.get(Portfolio, portfolio_id)
        portfolio.cash = new_cash
        await session.commit()


async def delete_portfolio(portfolio_id: int):
    async with async_session() as session:

        portfolio = await session.get(Portfolio, portfolio_id)

        if not portfolio:
            return False

        await session.delete(portfolio)
        await session.commit()

        return True