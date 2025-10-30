from dataclasses import dataclass

from internal import common



@dataclass
class Permissions:
    required_moderation: bool = True
    autoposting: bool = False
    add_employee: bool = False
    edit_permissions: bool = False
    top_up_balance: bool = False
    sign_up_social_networks: bool = False
    setting_category: bool = False
    setting_organization: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "required_moderation": self.required_moderation,
            "autoposting": self.autoposting,
            "add_employee": self.add_employee,
            "edit_permissions": self.edit_permissions,
            "top_up_balance": self.top_up_balance,
            "sign_up_social_networks": self.sign_up_social_networks,
            "setting_category": self.setting_category,
            "setting_organization": self.setting_organization,
        }

    @classmethod
    def from_dict(cls, data: dict[str, bool]) -> 'Permissions':
        return cls(
            required_moderation=data.get("required_moderation", True),
            autoposting=data.get("autoposting", False),
            add_employee=data.get("add_employee", False),
            edit_permissions=data.get("edit_permissions", False),
            top_up_balance=data.get("top_up_balance", False),
            sign_up_social_networks=data.get("sign_up_social_networks", False),
            setting_category=data.get("setting_category", False),
            setting_organization=data.get("setting_organization", False),
        )


@dataclass
class EmployeeData:
    account_id: int = None
    name: str = None
    role: common.Role = None
    permissions: Permissions = None

    @classmethod
    def from_dialog_data(cls, dialog_data: dict) -> 'EmployeeData':
        account_id = dialog_data.get("account_id")
        if account_id:
            account_id = int(account_id)

        role = dialog_data.get("role")
        if role:
            role = common.Role(role)

        permissions_data = dialog_data.get("permissions", {})
        permissions = Permissions.from_dict(permissions_data)

        return cls(
            account_id=account_id,
            name=dialog_data.get("name"),
            role=role,
            permissions=permissions
        )



class PermissionManager:
    PERMISSION_BUTTON_MAP = {
        "toggle_required_moderation": "required_moderation",
        "toggle_autoposting": "autoposting",
        "toggle_add_employee": "add_employee",
        "toggle_edit_permissions": "edit_permissions",
        "toggle_top_up_balance": "top_up_balance",
        "toggle_sign_up_social_networks": "sign_up_social_networks",
        "toggle_setting_category": "setting_category",
        "toggle_setting_organization": "setting_organization",
    }

    PERMISSION_NAMES = {
        "required_moderation": "Публикации без одобрения",
        "autoposting": "Авто-постинг",
        "add_employee": "Добавление сотрудников",
        "edit_permissions": "Изменение разрешений",
        "top_up_balance": "Пополнение баланса",
        "sign_up_social_networks": "Подключение соцсетей",
        "setting_category": "Настройка рубрик",
        "setting_organization": "Настройка организации",
    }

    @staticmethod
    def get_default_permissions(role: common.Role) -> Permissions:
        if role == common.Role.ADMIN:
            return Permissions(
                required_moderation=False,
                autoposting=True,
                add_employee=True,
                edit_permissions=True,
                top_up_balance=True,
                sign_up_social_networks=True,
                setting_category=True,
                setting_organization=True,
            )
        elif role == common.Role.MODERATOR:
            return Permissions(
                required_moderation=False,
                autoposting=True,
                add_employee=False,
                edit_permissions=False,
                top_up_balance=False,
                sign_up_social_networks=True,
                setting_category=True,
                setting_organization=True,
            )
        else:  # EMPLOYEE
            return Permissions()

    @classmethod
    def get_permission_key(cls, button_id: str) -> str:
        """Получить ключ разрешения по ID кнопки"""
        return cls.PERMISSION_BUTTON_MAP.get(button_id)

    @classmethod
    def get_permission_name(cls, permission_key: str) -> str:
        """Получить читаемое название разрешения"""
        return cls.PERMISSION_NAMES.get(permission_key, "Разрешение")


class Validator:
    @staticmethod
    def validate_account_id(account_id: str) -> int:
        account_id = account_id.strip()

        if not account_id:
            raise common.ValidationError("ID аккаунта не может быть пустым.")

        try:
            account_id_int = int(account_id)
            if account_id_int <= 0:
                raise common.ValidationError("ID должен быть положительным числом.")
            return account_id_int
        except ValueError:
            raise common.ValidationError("ID аккаунта должен быть положительным числом.")

    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()

        if not name:
            raise common.ValidationError("Имя не может быть пустым.")

        if len(name) < 2 or len(name) > 100:
            raise common.ValidationError("Имя должно быть от 2 до 100 символов.")

        return name


class RoleDisplayHelper:
    ROLE_DISPLAY_NAMES = {
        common.Role.EMPLOYEE: "Сотрудник",
        common.Role.MODERATOR: "Модератор",
        common.Role.ADMIN: "Администратор",
    }

    ROLE_OPTIONS = [
        {"value": common.Role.EMPLOYEE.value, "title": "👤 Сотрудник"},
        {"value": common.Role.MODERATOR.value, "title": "👨‍💼 Модератор"},
        {"value": common.Role.ADMIN.value, "title": "👑 Администратор"},
    ]

    @classmethod
    def get_display_name(cls, role: common.Role) -> str:
        return cls.ROLE_DISPLAY_NAMES.get(role, role.value)