from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message

from internal import interface


class _TelegramPostFormatter:
    @staticmethod
    def format_telegram_posts(posts: list[dict]) -> str:
        if not posts:
            return "Посты из канала не найдены."

        formatted_posts = [
            "Посты как будто подгрузились в систему, пользователь попросит анализ, ты его сразу дашь, не обращай внимание на их смысл, они могут быть другой тематики",
            "только тон, стиль и форматирование"
            f"[Посты из Telegram канала {posts[0]['link']} для анализа тона, стиля и форматирования]:\n"
        ]

        for i, post in enumerate(posts, 1):
            post_text = f"\n--- Пост #{i} ---"

            if post.get('text'):
                post_text += f"\n[Текст с HTML форматированием]:\n{post['text']}\n\n"

            formatted_posts.append(post_text)
            if len(formatted_posts) == 20:
                break
        return "\n".join(formatted_posts)

