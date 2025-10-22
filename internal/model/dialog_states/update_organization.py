from aiogram.fsm.state import StatesGroup, State


class UpdateOrganizationStates(StatesGroup):
    update_organization = State()
    organization_updated = State()