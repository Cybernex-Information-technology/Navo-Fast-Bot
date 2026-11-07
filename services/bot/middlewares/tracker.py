"""
Foydalanuvchilarni ma'lumotlar bazasida doimiy hisobga oluvchi middleware.
"""
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from core.database import Database


class UserTrackerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User = data.get("event_from_user")
        if user and not user.is_bot:
            # Foydalanuvchini bazada yangilash / saqlash
            await Database.track_user(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
            )
        return await handler(event, data)
