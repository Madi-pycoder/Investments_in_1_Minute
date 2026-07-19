from aiogram import Router, F
from aiogram.types import CallbackQuery
from GrowthSystem.service import GrowthService

router = Router()


@router.callback_query(F.data.startswith("growth_"))
async def handle_growth_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Ошибка")
        return
    promo_type = parts[1]
    action = parts[2]
    user_id = callback.from_user.id
    
    await GrowthService.record_user_action(user_id, promo_type, action)
    if action == "subscribed":
        await callback.message.edit_text(
            "✅ Спасибо за подписку!\n\n"
            "Если в канале будут выходить новые материалы и обновления бота,"
            "они появятся именно там.")
        await callback.answer("Отлично!")
    elif action == "later":
        await callback.message.edit_text(
            "Хорошо, напомню позже 🙂")
        await callback.answer("Напомню позже")
    elif action == "dismissed":
        await callback.message.edit_text(
            "Хорошо.\n"
            "Больше не буду предлагать подписку на канал.")
        await callback.answer("Понял")
    else:
        await callback.answer("OK")