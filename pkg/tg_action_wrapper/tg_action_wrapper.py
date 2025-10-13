import asyncio
from contextlib import asynccontextmanager
from aiogram import Bot


@asynccontextmanager
async def tg_action(bot: Bot, chat_id: int, action: str = "typing"):
    stop_event = asyncio.Event()

    async def _keep_typing():
        while not stop_event.is_set():
            try:
                await bot.send_chat_action(chat_id=chat_id, action=action)
                await asyncio.sleep(4)
            except Exception:
                break

    task = asyncio.create_task(_keep_typing())
    try:
        yield
    finally:
        stop_event.set()
        await task

