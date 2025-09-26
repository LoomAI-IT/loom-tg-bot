from aiogram.filters import Command
from aiogram_dialog import setup_dialogs, BgManagerFactory
from aiogram import Dispatcher, Router

from internal import interface


def NewTg(
        dp: Dispatcher,
        command_controller: interface.ICommandController,
        auth_dialog: interface.IAuthDialog,
        main_menu_dialog: interface.IMainMenuDialog,
        personal_profile_dialog: interface.IPersonalProfileDialog,
        organization_menu_dialog: interface.IOrganizationMenuDialog,
        change_employee_dialog: interface.IChangeEmployeeDialog,
        add_employee_dialog: interface.IAddEmployeeDialog,
        content_menu_dialog: interface.IContentMenuDialog,
        generate_publication_dialog: interface.IGeneratePublicationDialog,
        generate_video_cut_dialog: interface.IGenerateVideoCutDialog,
        moderation_publication_dialog: interface.IModerationPublicationDialog,
        moderation_video_cut_dialog: interface.IVideoCutModerationDialog,
        video_cuts_draft_dialog: interface.IVideoCutsDraftDialog,
        publication_draft_dialog: interface.IPublicationDraftDialog,
        add_social_network_dialog: interface.IAddSocialNetworkDialog,
) -> BgManagerFactory:
    include_command_handlers(
        dp,
        command_controller
    )
    dialog_bg_factory = include_dialogs(
        dp,
        auth_dialog,
        main_menu_dialog,
        personal_profile_dialog,
        organization_menu_dialog,
        change_employee_dialog,
        add_employee_dialog,
        content_menu_dialog,
        generate_publication_dialog,
        generate_video_cut_dialog,
        moderation_publication_dialog,
        moderation_video_cut_dialog,
        video_cuts_draft_dialog,
        publication_draft_dialog,
        add_social_network_dialog
    )

    return dialog_bg_factory


def include_tg_middleware(
        dp: Dispatcher,
        tg_middleware: interface.ITelegramMiddleware,
):
    dp.update.middleware(tg_middleware.trace_middleware01)
    dp.update.middleware(tg_middleware.metric_middleware02)
    dp.update.middleware(tg_middleware.logger_middleware03)


def include_command_handlers(
        dp: Dispatcher,
        command_controller: interface.ICommandController,
):
    dp.message.register(
        command_controller.start_handler,
        Command("start")
    )


def include_dialogs(
        dp: Dispatcher,
        auth_dialog: interface.IAuthDialog,
        main_menu_dialog: interface.IMainMenuDialog,
        personal_profile_dialog: interface.IPersonalProfileDialog,
        organization_menu_dialog: interface.IOrganizationMenuDialog,
        change_employee_dialog: interface.IChangeEmployeeDialog,
        add_employee_dialog: interface.IAddEmployeeDialog,
        content_menu_dialog: interface.IContentMenuDialog,
        generate_publication_dialog: interface.IGeneratePublicationDialog,
        generate_video_cut_dialog: interface.IGenerateVideoCutDialog,
        moderation_publication_dialog: interface.IModerationPublicationDialog,
        moderation_video_cut_dialog: interface.IVideoCutModerationDialog,
        video_cuts_draft_dialog: interface.IVideoCutsDraftDialog,
        publication_draft_dialog: interface.IPublicationDraftDialog,
        add_social_network_dialog: interface.IAddSocialNetworkDialog,
) -> BgManagerFactory:
    dialog_router = Router()
    dialog_router.include_routers(
        auth_dialog.get_dialog(),
        main_menu_dialog.get_dialog(),
        personal_profile_dialog.get_dialog(),
        organization_menu_dialog.get_dialog(),
        change_employee_dialog.get_dialog(),
        add_employee_dialog.get_dialog(),
        content_menu_dialog.get_dialog(),
        generate_publication_dialog.get_dialog(),
        moderation_publication_dialog.get_dialog(),
        generate_video_cut_dialog.get_dialog(),
        moderation_video_cut_dialog.get_dialog(),
        video_cuts_draft_dialog.get_dialog(),
        publication_draft_dialog.get_dialog(),
        add_social_network_dialog.get_dialog()
    )

    dp.include_routers(dialog_router)

    dialog_bg_factory = setup_dialogs(dp)

    return dialog_bg_factory
