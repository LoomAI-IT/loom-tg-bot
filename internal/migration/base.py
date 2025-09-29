from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import inspect


@dataclass
class MigrationInfo:
    version: str  # формат: v1_0_0
    name: str
    description: str
    checksum: str
    depends_on: str = None  # версия, от которой зависит

    @property
    def filename(self) -> str:
        return f"{self.version}_{self.name}"

    def __lt__(self, other: 'MigrationInfo'):
        """Для сортировки миграций по версии"""
        return self._version_to_tuple() < other._version_to_tuple()

    def _version_to_tuple(self) -> tuple:
        """Преобразует v1_0_0 в (1, 0, 0) для сравнения"""
        version_str = self.version.lstrip('v')
        return tuple(map(int, version_str.split('_')))


class Migration(ABC):
    """Базовый класс для всех миграций"""

    def __init__(self):
        self.info = self.get_info()

    @abstractmethod
    def get_info(self) -> MigrationInfo:
        """Возвращает информацию о миграции"""
        pass

    @abstractmethod
    async def up(self, db) -> None:
        """Применяет миграцию"""
        pass

    @abstractmethod
    async def down(self, db) -> None:
        """Откатывает миграцию"""
        pass

    def calculate_checksum(self) -> str:
        """Вычисляет контрольную сумму миграции"""
        source = inspect.getsource(self.up)
        content = f"{self.info.version}_{self.info.name}_{source}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def validate_dependencies(self, applied_versions: list[str]) -> bool:
        """Проверяет, что все зависимости применены"""
        if not self.info.depends_on:
            return True
        return self.info.depends_on in applied_versions