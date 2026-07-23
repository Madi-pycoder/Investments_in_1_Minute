from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from ReviewsAndReferrals.review_states import ReviewStates
from ReviewsAndReferrals.review_keyboards import review_finish_keyboard, review_rating_keyboard

router = Router()

@router.callback_query(F.data == "write_review")
async def start_review(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "⭐ Оцените бота\n\n"
        "Нажмите количество звёзд.",
        reply_markup=review_rating_keyboard())
    await state.set_state(ReviewStates.waiting_rating)
    await callback.answer()


@router.callback_query(ReviewStates.waiting_rating, F.data.startswith("review_rating:"))
async def choose_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)
    await callback.message.edit_text(
        f"⭐ Ваша оценка: {rating}/5\n\n"
        "Теперь напишите отзыв.")
    await state.set_state(ReviewStates.waiting_text)
    await callback.answer()


@router.message(ReviewStates.waiting_text)
async def save_review(message: Message, state: FSMContext):
    if len(message.text) < 10:
        await message.answer("Минимум 10 символов.")
        return
    if len(message.text) > 2000:
        await message.answer("Максимум 2000 символов.")
        return
    await message.answer(
        "❤️ Спасибо!\n\n"
        "Ваш отзыв отправлен на модерацию.",
        reply_markup=review_finish_keyboard())
    await state.clear()


@router.callback_query(F.data == "review_again")
async def review_again(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "⭐ Оцените бота",
        reply_markup=review_rating_keyboard())
    await state.set_state(ReviewStates.waiting_rating)
    await callback.answer()