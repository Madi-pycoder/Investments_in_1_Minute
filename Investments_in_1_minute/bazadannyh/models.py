from datetime import datetime
from sqlalchemy import BigInteger, String, Float, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker

engine = create_async_engine(
    "sqlite+aiosqlite:///db1.sqlite3",
    echo=True
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False
)

class Base(AsyncAttrs, DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )


class Demo(Base):
    __tablename__ = "demos"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("owners.id")
    )

    cash: Mapped[float] = mapped_column(Float)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


class Position(Base):
    __tablename__  = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)

    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id")
    )

    ticker: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float)
    average_price: Mapped[float] = mapped_column(Float)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id")
    )


class Transaction(Base):
    __tablename__  = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id")
    )

    ticker: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)

    is_buy: Mapped[bool] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)