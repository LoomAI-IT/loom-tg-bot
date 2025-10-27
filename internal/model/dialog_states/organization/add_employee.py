from aiogram.fsm.state import StatesGroup, State


class AddEmployeeStates(StatesGroup):
    """Состояния диалога добавления сотрудника"""
    enter_account_id = State()
    enter_name = State()
    enter_role = State()
    set_permissions = State()
    confirm_employee = State()