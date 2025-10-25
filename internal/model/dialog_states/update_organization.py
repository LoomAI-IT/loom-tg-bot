from aiogram.fsm.state import StatesGroup, State


class UpdateOrganizationStates(StatesGroup):
    update_organization = State()
    confirm_cancel = State()
    organization_updated = State()