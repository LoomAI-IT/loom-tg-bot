import traceback

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method


class CreateOrganizationService(interface.ICreateOrganizationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            create_organization_prompt_generator: interface.ICreateOrganizationPromptGenerator,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.create_organization_prompt_generator = create_organization_prompt_generator
        self.loom_organization_client = loom_organization_client
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._get_state(dialog_manager)
        try:
            dialog_manager.show_mode = ShowMode.SEND

            chat_id = dialog_manager.dialog_data.get("chat_id")
            user_text = await self._extract_text_from_message(message)

            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="user",
                text=user_text
            )

            system_prompt = await self.create_organization_prompt_generator.get_create_organization_system_prompt()
            messages = await self.llm_chat_repo.get_all_messages(chat_id)
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.text
                })

            async with tg_action(self.bot, message.chat.id):
                llm_response_json, _ = await self.anthropic_client.generate_json(
                    history=history,
                    system_prompt=system_prompt,
                    max_tokens=15000,
                    thinking_tokens=10000,
                )

            if llm_response_json.get("organization_data"):
                organization_data = llm_response_json["organization_data"]
                dialog_manager.dialog_data["organization_data"] = organization_data

                organization_id = await self.loom_organization_client.create_organization(
                    organization_data["name"]
                )
                await self.loom_organization_client.update_organization(
                    organization_id,
                    organization_data["name"],
                    organization_data["description"],
                    organization_data["tone_of_voice"],
                    organization_data["compliance_rules"],
                    organization_data["products"],
                    organization_data["locale"],
                    organization_data["additional_info"],
                )
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    organization_id=organization_id,
                )

                await self.loom_employee_client.create_employee(
                    organization_id=organization_id,
                    invited_from_account_id=0,
                    account_id=state.account_id,
                    name="admin",
                    role="admin"
                )

                await dialog_manager.switch_to(model.CreateOrganizationStates.organization_created)
                return

            message_to_user = llm_response_json["message_to_user"]
            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="assistant",
                text=message_to_user
            )
            dialog_manager.dialog_data["message_to_user"] = message_to_user
        except Exception as e:
            await self.bot.send_message(
                state.tg_chat_id,
                "Произошла непредвиденная ошибка, попробуйте продолжить диалог"
            )
            self.logger.error("Ошибка!!!", {"traceback": traceback.format_exc()})

    @auto_log()
    @traced_method()
    async def go_to_create_category(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await callback.answer()

        state = await self._get_state(dialog_manager)

        chat = await self.llm_chat_repo.get_chat_by_state_id(state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat[0].id)

        await dialog_manager.start(
            model.CreateCategoryStates.create_category,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.start(model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)

    async def _speech_to_text(self, message: Message, organization_id: int) -> str:
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id

        file = await self.bot.get_file(file_id)
        file_data = await self.bot.download_file(file.file_path)

        text = await self.loom_content_client.transcribe_audio(
            organization_id,
            audio_content=file_data.read(),
            audio_filename="audio.mp3",
        )
        return text

    async def _extract_text_from_message(self, message: Message) -> str:
        text_parts = []

        if message.content_type in [ContentType.AUDIO, ContentType.VOICE]:
            audio_text = await self._speech_to_text(message, -1)
            text_parts.append(audio_text)

        if message.text:
            text_parts.append(message.text)

        if message.caption:
            text_parts.append(message.caption)

        if message.forward_origin:
            if hasattr(message, 'forward_from_message') and message.forward_from_message:
                forwarded_text = await self._extract_text_from_message(message.forward_from_message)
                if forwarded_text:
                    text_parts.append(f"[Пересланное сообщение]: {forwarded_text}")

        if message.reply_to_message:
            reply_text = await self._extract_text_from_message(message.reply_to_message)
            if reply_text:
                text_parts.append(f"[Ответ на]: {reply_text}")

        result = "\n\n".join(text_parts)

        if not result:
            return f"[Сообщение типа {message.content_type} без текста]"

        return result

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]
