from aiogram.fsm.state import StatesGroup, State


class ChangeEmployeeStates(StatesGroup):
    employee_list = State()
    employee_detail = State()
    change_permissions = State()

    confirm_delete = State()
    change_role = State()