from aiogram.fsm.state import StatesGroup, State


class UpdateOrganizationStates(StatesGroup):
    intro_organization = State()
    update_organization = State()
    confirm_cancel = State()
    organization_updated = State()