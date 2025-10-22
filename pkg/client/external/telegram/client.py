import base64
import asyncio

from aiogram import Bot
from aiogram.types import BufferedInputFile
from sulguk import SULGUK_PARSE_MODE, AiogramSulgukMiddleware

import segno
from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from telethon.tl.functions.auth import ExportLoginTokenRequest
from telethon.tl.types.auth import LoginTokenSuccess
from telethon.extensions.html import unparse
from telethon.errors import (
    AuthTokenExpiredError,
    AuthTokenAlreadyAcceptedError,
    AuthTokenInvalidError,
)

from internal import interface


class LTelegramClient(interface.ITelegramClient):
    def __init__(
            self,
            bot_token: str,
            session_string: str,
            api_id: int,
            api_hash: str,
    ):
        self.bot = Bot(token=bot_token)
        self.bot.session.middleware(AiogramSulgukMiddleware())

        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.telegram_client: TelethonClient | None = None

    async def send_text_message(
            self,
            channel_id: str | int,
            text: str,
            parse_mode: str = None,
    ) -> str:
        try:
            message = await self.bot.send_message(
                chat_id="@"+channel_id,
                text=text,
                parse_mode=SULGUK_PARSE_MODE,
            )
            post_link = self._create_post_link(str(channel_id), message.message_id)
            return post_link

        except Exception as e:
            raise

    async def send_photo(
            self,
            channel_id: str | int,
            photo: bytes,
            caption: str = None,
            parse_mode: str = None,
    ) -> str:
        try:
            photo_input = BufferedInputFile(photo, "file")

            message = await self.bot.send_photo(
                chat_id="@"+channel_id,
                photo=photo_input,
                caption=caption,
                parse_mode=SULGUK_PARSE_MODE,
            )
            post_link = self._create_post_link(str(channel_id), message.message_id)
            return post_link

        except Exception as e:
            raise

    async def check_permission(
            self,
            channel_id: str | int,
    ) -> bool:
        try:
            chat = await self.bot.get_chat(chat_id="@" + channel_id)
            bot_member = await self.bot.get_chat_member(
                chat_id="@" + channel_id,
                user_id=self.bot.id
            )

            allowed_statuses = ["administrator", "creator"]

            if bot_member.status in allowed_statuses:
                return True
            elif bot_member.status == "member":
                if chat.type in ["channel", "supergroup"]:
                    return False
                else:
                    return True
            else:
                return False

        except Exception as e:
            return False

    def _create_post_link(self, channel_username: str, message_id: int) -> str:
        clean_username = channel_username.lstrip('@')
        return f"https://t.me/{clean_username}/{message_id}"

    async def authorize_telegram(self) -> str:
        """Авторизация через QR код и получение string_session"""
        try:
            # Закрываем

            session = StringSession()
            client = TelethonClient(
                session,
                self.api_id,
                self.api_hash,
                device_model='Server',
                system_version='Linux',
                app_version='1.0',
                lang_code='ru'
            )
            await client.connect()

            # Генерируем QR код
            auth_result = await client(ExportLoginTokenRequest(
                api_id=self.api_id,
                api_hash=self.api_hash,
                except_ids=[]
            ))

            token_b64url = base64.urlsafe_b64encode(auth_result.token).decode().rstrip('=')
            qr_url = f"tg://login?token={token_b64url}"

            qr = segno.make(qr_url)
            qr.save("qr.png", kind='png', scale=8)

            print("QR код сгенерирован и сохранен в qr.png. Отсканируйте его в Telegram...", flush=True)

            # Бесконечный цикл проверки статуса
            while True:
                await asyncio.sleep(2)

                try:
                    auth_result = await client(ExportLoginTokenRequest(
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        except_ids=[],
                    ))

                    if isinstance(auth_result, LoginTokenSuccess):
                        print("QR код успешно подтвержден!")

                        # Сохраняем сессию
                        string_session = session.save()

                        # Небольшая задержка для полной инициализации
                        await asyncio.sleep(2)

                        # Проверяем авторизацию
                        await client.get_me()
                        print("Авторизация успешна!")

                        return string_session

                except AuthTokenExpiredError:
                    print("QR код истек, генерируем новый...")
                    # Генерируем новый QR код
                    auth_result = await client(ExportLoginTokenRequest(
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        except_ids=[]
                    ))

                    token_b64url = base64.urlsafe_b64encode(auth_result.token).decode().rstrip('=')
                    qr_url = f"tg://login?token={token_b64url}"

                    qr = segno.make(qr_url)
                    qr.save("qr.png", kind='png', scale=8)

                    print("Новый QR код сгенерирован и сохранен. Отсканируйте его...", flush=True)

                except (AuthTokenAlreadyAcceptedError, AuthTokenInvalidError) as e:
                    print(f"Ошибка токена: {e}")
                    raise

        except Exception as e:
            raise

    async def get_channel_posts(
            self,
            channel_id: str,
            limit: int = None
    ) -> list[dict]:
        try:
            if not self.telegram_client:
                client = TelethonClient(
                    StringSession(self.session_string),
                    self.api_id,
                    self.api_hash,
                    device_model='Server',
                    system_version='Linux',
                    app_version='1.0',
                    lang_code='ru'
                )
                await client.connect()
                self.telegram_client = client

            # Проверяем авторизацию
            if not await self.telegram_client.is_user_authorized():
                raise Exception("Session string недействительна")

            # Нормализуем ID канала
            if not channel_id.startswith('@'):
                channel_id = f"@{channel_id}"

            # Получаем информацию о канале
            entity = await self.telegram_client.get_entity(channel_id)

            posts = []
            async for message in self.telegram_client.iter_messages(entity, limit=limit):
                # Определяем тип медиа
                media_type = None
                if message.media:
                    if hasattr(message.media, 'photo'):
                        media_type = 'photo'
                    elif hasattr(message.media, 'document'):
                        if message.video:
                            media_type = 'video'
                        else:
                            media_type = 'document'

                # Формируем ссылку на пост
                channel_username = entity.username if hasattr(entity, 'username') and entity.username else str(entity.id)
                post_link = self._create_post_link(channel_username, message.id)

                post_data = {
                    'id': message.id,
                    'date': message.date,
                    'text': message.text or '',
                    'html_text': unparse(message.text, message.entities) if message.text else '',
                    'views': message.views or 0,
                    'media_type': media_type,
                    'link': post_link,
                }

                posts.append(post_data)

            return posts

        except Exception as e:
            raise