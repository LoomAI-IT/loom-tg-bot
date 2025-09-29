import importlib
from pathlib import Path
from typing import Optional

from internal import interface, model
from internal.migration.base import Migration


class MigrationManager:
    def __init__(self, db: interface.IDB):
        self.db = db
        self.migrations = self._load_migrations()

    def _load_migrations(self) -> dict[str, Migration]:
        try:
            migrations = {}
            migration_dir = Path(__file__).parent / 'version'

            for file_path in sorted(migration_dir.glob('v*.py')):
                if file_path.stem == '__init__':
                    continue


                module = importlib.import_module(f"internal.migration.version.{file_path.stem}")

                for attr in dir(module):
                    obj = getattr(module, attr)
                    if (isinstance(obj, type) and
                                issubclass(obj, Migration) and
                                obj != Migration):
                            migration = obj()
                            migrations[migration.info.version] = migration
                            break

            print(migrations, flush=True)
            return migrations
        except Exception as e:
            print(e, flush=True)



    async def _ensure_history_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS migration_history (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self.db.multi_query([query])

    async def _get_applied_versions(self) -> set[str]:
        try:
            rows = await self.db.select(
                "SELECT version FROM migration_history ORDER BY version",
                {}
            )
            return {row[0] for row in rows}
        except:
            return set()  # Таблицы еще нет

    async def _mark_applied(self, migration: Migration):
        await self.db.insert(
            "INSERT INTO migration_history (version, name) VALUES (:version, :name)",
            {'version': migration.info.version, 'name': migration.info.name}
        )

    async def _mark_rolled_back(self, version: str):
        await self.db.delete(
            "DELETE FROM migration_history WHERE version = :version",
            {'version': version}
        )

    def _version_key(self, version: str) -> tuple:
        return tuple(map(int, version.lstrip('v').split('_')))

    async def migrate(self) -> int:
       try:
           await self._ensure_history_table()
           latest_version = max(self.migrations.keys(), key=self._version_key)
           applied = await self._get_applied_versions()

           # Определяем какие миграции нужно применить
           to_apply = []
           target_key = self._version_key(latest_version)

           for version in sorted(self.migrations.keys(), key=self._version_key):
               if (self._version_key(version) <= target_key and
                       version not in applied):
                   to_apply.append(version)

           # Применяем миграции по порядку
           count = 0
           for version in to_apply:
               migration = self.migrations[version]

               # Проверяем зависимости
               if migration.info.depends_on and migration.info.depends_on not in applied:
                   continue  # Пропускаем если зависимость не выполнена

               await migration.up(self.db)
               await self._mark_applied(migration)
               applied.add(version)
               count += 1

           return count
       except Exception as e:
           print(e, flush=True)

    async def rollback_to_version(self, target_version: Optional[str] = None) -> int:
        try:
            await self._ensure_history_table()
            applied = await self._get_applied_versions()

            if not applied:
                return 0

            # Определяем какие миграции откатить
            to_rollback = []

            if target_version is None:
                # Откатываем все
                to_rollback = sorted(applied, key=self._version_key, reverse=True)
            else:
                # Откатываем все версии после target_version
                target_key = self._version_key(target_version)
                for version in sorted(applied, key=self._version_key, reverse=True):
                    if self._version_key(version) > target_key:
                        to_rollback.append(version)

            # Откатываем миграции в обратном порядке
            count = 0
            for version in to_rollback:
                if version in self.migrations:
                    migration = self.migrations[version]
                    await migration.down(self.db)
                    await self._mark_rolled_back(version)
                    count += 1

            return count
        except Exception as e:
            print(e, flush=True)

    async def drop_tables(self):
        try:
            drop_migration_history_table = "DROP TABLE IF EXISTS migration_history;"
            await self.db.multi_query([*model.drop_queries, drop_migration_history_table])
        except Exception as e:
            print(e, flush=True)
