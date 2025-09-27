from dataclasses import dataclass


@dataclass
class Employee:
    id: int
    organization_id: int
    account_id: int
    invited_from_account_id: int

    required_moderation: bool
    autoposting_permission: bool
    add_employee_permission: bool
    edit_employee_perm_permission: bool
    top_up_balance_permission: bool
    sign_up_social_net_permission: bool

    name: str
    role: str

    created_at: str
