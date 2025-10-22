from aiogram.fsm.state import StatesGroup, State


class CreateOrganizationStates(StatesGroup):
    create_organization = State()
    organization_created = State()