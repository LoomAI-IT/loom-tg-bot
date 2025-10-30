from aiogram.filters import Command
from aiogram_dialog import setup_dialogs, BgManagerFactory
from aiogram import Dispatcher, Router

from internal import interface


def NewTg(
        dp: Dispatcher,
        command_controller: interface.ICommandController,
        tg_middleware: interface.ITelegramMiddleware,
        auth_dialog: interface.IIntroDialog,
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
        draft_publication_dialog: interface.IDraftPublicationDialog,
        add_social_network_dialog: interface.IAddSocialNetworkDialog,
        alerts_dialog: interface.IAlertsDialog,
        create_category_dialog: interface.ICreateCategoryDialog,
        create_organization_dialog: interface.ICreateOrganizationDialog,
        update_category_dialog: interface.IUpdateCategoryDialog,
        update_organization_dialog: interface.IUpdateOrganizationDialog,
) -> BgManagerFactory:
    include_command_handlers(
        dp,
        command_controller
    )
    include_tg_middleware(
        dp,
        tg_middleware,
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
        draft_publication_dialog,
        add_social_network_dialog,
        alerts_dialog,
        create_category_dialog,
        create_organization_dialog,
        update_category_dialog,
        update_organization_dialog,
    )

    return dialog_bg_factory


def include_tg_middleware(
        dp: Dispatcher,
        tg_middleware: interface.ITelegramMiddleware,
):
    dp.update.middleware(tg_middleware.logger_middleware01)


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
        auth_dialog: interface.IIntroDialog,
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
        draft_publication_dialog: interface.IDraftPublicationDialog,
        add_social_network_dialog: interface.IAddSocialNetworkDialog,
        alerts_dialog: interface.IAlertsDialog,
        create_category_dialog: interface.ICreateCategoryDialog,
        create_organization_dialog: interface.ICreateOrganizationDialog,
        update_category_dialog: interface.IUpdateCategoryDialog,
        update_organization_dialog: interface.IUpdateOrganizationDialog,
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
        draft_publication_dialog.get_dialog(),
        add_social_network_dialog.get_dialog(),
        alerts_dialog.get_dialog(),
        create_category_dialog.get_dialog(),
        create_organization_dialog.get_dialog(),
        update_category_dialog.get_dialog(),
        update_organization_dialog.get_dialog(),
    )

    dp.include_routers(dialog_router)

    dialog_bg_factory = setup_dialogs(dp)

    return dialog_bg_factory
