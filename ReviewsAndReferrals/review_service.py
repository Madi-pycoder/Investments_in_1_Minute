from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update, delete
from ProjectDataBase.models import async_session, UserReview

class ReviewService:
    @staticmethod
    async def create_review(user_id, rating, text):
        async with async_session() as session:
            review = UserReview(user_id=user_id, rating=rating, text=text.strip(),
                published=False, admin_note=None, created_at=datetime.now(timezone.utc))
            session.add(review)
            await session.commit()
            await session.refresh(review)
            return review

    @staticmethod
    async def get_review(review_id) -> Optional[UserReview]:
        async with async_session() as session:
            return await session.scalar(select(UserReview)
                .where(UserReview.id==review_id))

    @staticmethod
    async def get_user_reviews(user_id):
        async with async_session() as session:
            result = await session.scalars(select(UserReview)
                .where(UserReview.user_id == user_id)
                .order_by(UserReview.created_at.desc()))
            return list(result)

    @staticmethod
    async def get_last_reviews(limit=20):
        async with async_session() as session:
            result = await session.scalars(select(UserReview)
                .order_by(UserReview.created_at.desc())
                .limit(limit))
            return list(result)

    @staticmethod
    async def get_published_reviews(limit=20):
        async with async_session() as session:
            result = await session.scalars(select(UserReview)
                .where(UserReview.published == True)
                .order_by(UserReview.created_at.desc())
                .limit(limit))
            return list(result)

    @staticmethod
    async def get_unpublished_reviews(limit=20):
        async with async_session() as session:
            result = await session.scalars(select(UserReview)
                .where(UserReview.published == False)
                .order_by(UserReview.created_at.asc())
                .limit(limit))
            return list(result)

    @staticmethod
    async def publish_review(review_id):
        async with async_session() as session:
            await session.execute(update(UserReview)
                .where(UserReview.id==review_id)
                .values(published=True))
            await session.commit()

    @staticmethod
    async def unpublish_review(review_id):
        async with async_session() as session:
            await session.execute(update(UserReview)
                .where(UserReview.id == review_id)
                .values(published=False))
            await session.commit()

    @staticmethod
    async def set_admin_note(review_id, note):
        async with async_session() as session:
            await session.execute(update(UserReview)
                .where(UserReview.id == review_id)
                .values(admin_note=note))
            await session.commit()

    @staticmethod
    async def update_text(review_id, text):
        async with async_session() as session:
            await session.execute(update(UserReview)
                .where(UserReview.id==review_id)
                .values(text=text))
            await session.commit()

    @staticmethod
    async def update_rating(review_id, rating):
        async with async_session() as session:
            await session.execute(update(UserReview)
                .where(UserReview.id==review_id)
                .values(rating=rating))
            await session.commit()

    @staticmethod
    async def delete_review(review_id):
        async with async_session() as session:
            await session.execute(delete(UserReview)
                .where(UserReview.id==review_id))
            await session.commit()

    @staticmethod
    async def count_reviews():
        async with async_session() as session:
            result = await session.scalars(select(UserReview))
            return len(list(result))

    @staticmethod
    async def count_published():
        async with async_session() as session:
            result = await session.scalars(select(UserReview)
                .where(UserReview.published==True))
            return len(list(result))

    @staticmethod
    async def average_rating():
        reviews = await ReviewService.get_published_reviews(limit=100000)
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews), 2)