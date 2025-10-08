import asyncio
from contextlib import asynccontextmanager
from aiogram import Bot
from aiogram.types import ChatAction


@asynccontextmanager
async def typing_action(bot: Bot, chat_id: int):
    """
    Context manager для показа индикатора 'печатает...' в чате.
    
    Автоматически отправляет ChatAction.TYPING каждые 4 секунды
    пока выполняется код внутри блока with.
    
    Пример использования:
        async with typing_action(bot, message.chat.id):
            # Долгая операция
            result = await some_long_operation()
    """
    stop_event = asyncio.Event()
    
    async def _keep_typing():
        while not stop_event.is_set():
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                await asyncio.sleep(4)
            except Exception:
                break
    
    task = asyncio.create_task(_keep_typing())
    try:
        yield
    finally:
        stop_event.set()
        await task

