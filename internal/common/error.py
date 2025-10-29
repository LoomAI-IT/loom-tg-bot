class ValidationError(Exception):
    """Ошибка валидации пользовательского ввода"""
    pass


class ErrInsufficientBalance(Exception):
    """Ошибка недостаточного баланса организации"""
    pass
