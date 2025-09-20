import asyncio
from io import BytesIO

import aiohttp
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.types import BufferedInputFile


async def _download_video_from_url(video_url: str) -> tuple[bytes, str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', 'video/mp4')
                    content = await response.read()
                    return content, content_type
                else:
                    raise Exception(f"Failed to download video: HTTP {response.status}")
    except Exception as err:
        raise err

async def test_local_server():
    # Replace with your NEW bot token from @BotFather
    BOT_TOKEN = "7601862716:AAEYmoWKPJnEWG5q2cy6AlKDGDGlFcBWBCQ"

    print("\n2. Тестируем локальный сервер...")
    session = AiohttpSession(api=TelegramAPIServer.from_base('https://kontur-media.ru/telegram-bot-api'))
    local_bot = Bot(token=BOT_TOKEN, session=session)


    try:
        me = await local_bot.get_me()
        print(f"✅ Локальный сервер работает: @{me.username}")
        chat_id = "5667467611"

        content, content_type = await _download_video_from_url("https://kontur-media.ru/api/content/video-cut/21/download/file.mp4?v=2444424")
        print(content_type)
        resp = await local_bot.send_video(
            chat_id=chat_id,
            video=BufferedInputFile(content, filename="fff.mp4")
        )

        # Test sending message
        message = await local_bot.send_message(
            chat_id=chat_id,
            text="🔧 Тест локального Telegram Bot API сервера"
        )
        print(f"✅ Сообщение отправлено через локальный сервер: {message.message_id}")

    except Exception as e:
        print(f"❌ Ошибка локального сервера: {e}")
        print("Возможные причины:")
        print("- Локальный сервер недоступен")
        print("- Неверный base_url")
        print("- Проблемы с SSL сертификатом")

    finally:
        await local_bot.session.close()


if __name__ == "__main__":
    asyncio.run(test_local_server())