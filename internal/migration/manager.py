import importlib
from pathlib import Path
from typing import Optional

from internal import interface, model
from internal.migration.base import Migration


class MigrationManager:
    def __init__(self, db: interface.IDB):
        print("MigrationManager: Initializing...", flush=True)
        self.db = db
        self.migrations = self._load_migrations()
        print(f"MigrationManager: Loaded {len(self.migrations)} migrations", flush=True)

    def _load_migrations(self) -> dict[str, Migration]:
        print("MigrationManager: Loading migrations...", flush=True)
        try:
            migrations = {}
            migration_dir = Path(__file__).parent / 'version'
            print(f"MigrationManager: Migration directory: {migration_dir}", flush=True)

            for file_path in sorted(migration_dir.glob('v*.py')):
                if file_path.stem == '__init__':
                    continue

                print(f"MigrationManager: Processing file {file_path.stem}", flush=True)
                module = importlib.import_module(f"internal.migration.version.{file_path.stem}")

                for attr in dir(module):
                    obj = getattr(module, attr)
                    if (isinstance(obj, type) and
                            issubclass(obj, Migration) and
                            obj != Migration):
                        migration = obj()
                        migrations[migration.info.version] = migration
                        print(f"MigrationManager: Added migration {migration.info.version} - {migration.info.name}",
                              flush=True)
                        break

            print(f"MigrationManager: All migrations: {migrations}", flush=True)
            return migrations
        except Exception as e:
            print(f"MigrationManager: ERROR loading migrations: {e}", flush=True)
            return {}

    async def _ensure_history_table(self):
        print("MigrationManager: Ensuring migration_history table exists...", flush=True)
        query = """
                CREATE TABLE IF NOT EXISTS migration_history \
                ( \
                    version \
                    TEXT \
                    PRIMARY \
                    KEY, \
                    name \
                    TEXT \
                    NOT \
                    NULL, \
                    applied_at \
                    TIMESTAMP \
                    DEFAULT \
                    CURRENT_TIMESTAMP
                ) \
                """
        await self.db.multi_query([query])
        print("MigrationManager: migration_history table ready", flush=True)

    async def _get_applied_versions(self) -> set[str]:
        print("MigrationManager: Getting applied versions...", flush=True)
        try:
            rows = await self.db.select(
                "SELECT version FROM migration_history ORDER BY version",
                {}
            )
            applied = {row[0] for row in rows}
            print(f"MigrationManager: Applied versions: {applied}", flush=True)
            return applied
        except Exception as e:
            print(f"MigrationManager: No applied versions yet (table doesn't exist?): {e}", flush=True)
            return set()

    async def _mark_applied(self, migration: Migration):
        print(f"MigrationManager: Marking migration {migration.info.version} as applied...", flush=True)
        await self.db.insert(
            "INSERT INTO migration_history (version, name) VALUES (:version, :name)",
            {'version': migration.info.version, 'name': migration.info.name}
        )
        print(f"MigrationManager: Migration {migration.info.version} marked as applied", flush=True)

    async def _mark_rolled_back(self, version: str):
        print(f"MigrationManager: Marking migration {version} as rolled back...", flush=True)
        await self.db.delete(
            "DELETE FROM migration_history WHERE version = :version",
            {'version': version}
        )
        print(f"MigrationManager: Migration {version} rolled back", flush=True)

    def _version_key(self, version: str) -> tuple:
        key = tuple(map(int, version.lstrip('v').split('_')))
        print(f"MigrationManager: Version key for {version}: {key}", flush=True)
        return key

    async def migrate(self) -> int:
        print("MigrationManager: Starting migration process...", flush=True)
        try:
            await self._ensure_history_table()
            latest_version = max(self.migrations.keys(), key=self._version_key)
            print(f"MigrationManager: Latest version: {latest_version}", flush=True)

            applied = await self._get_applied_versions()

            # Определяем какие миграции нужно применить
            to_apply = []
            target_key = self._version_key(latest_version)
            print(f"MigrationManager: Target version key: {target_key}", flush=True)

            for version in sorted(self.migrations.keys(), key=self._version_key, reverse=True):
                if (self._version_key(version) <= target_key and
                        version not in applied):
                    to_apply.append(version)
                    print(f"MigrationManager: Will apply migration {version}", flush=True)

            print(f"MigrationManager: Total migrations to apply: {len(to_apply)}", flush=True)

            # Применяем миграции по порядку
            count = 0
            for version in to_apply:
                migration = self.migrations[version]
                print(f"MigrationManager: Applying migration {version}...", flush=True)

                # Проверяем зависимости
                if migration.info.depends_on and migration.info.depends_on not in applied:
                    print(f"MigrationManager: Skipping {version} - dependency {migration.info.depends_on} not met",
                          flush=True)
                    continue

                await migration.up(self.db)
                await self._mark_applied(migration)
                applied.add(version)
                count += 1
                print(f"MigrationManager: Successfully applied migration {version} ({count}/{len(to_apply)})",
                      flush=True)

            print(f"MigrationManager: Migration complete. Applied {count} migrations", flush=True)
            return count
        except Exception as e:
            print(f"MigrationManager: ERROR during migration: {e}", flush=True)
            return 0

    async def rollback_to_version(self, target_version: Optional[str] = None) -> int:
        print(f"MigrationManager: Starting rollback to version {target_version}...", flush=True)
        try:
            await self._ensure_history_table()
            applied = await self._get_applied_versions()

            if not applied:
                print("MigrationManager: No migrations to rollback", flush=True)
                return 0

            # Определяем какие миграции откатить
            to_rollback = []

            if target_version is None:
                print("MigrationManager: Rolling back ALL migrations", flush=True)
                to_rollback = sorted(applied, key=self._version_key, reverse=True)
            else:
                print(f"MigrationManager: Rolling back to version {target_version}", flush=True)
                target_key = self._version_key(target_version)
                for version in sorted(applied, key=self._version_key, reverse=True):
                    if self._version_key(version) > target_key:
                        to_rollback.append(version)
                        print(f"MigrationManager: Will rollback migration {version}", flush=True)

            print(f"MigrationManager: Total migrations to rollback: {len(to_rollback)}", flush=True)

            # Откатываем миграции в обратном порядке
            count = 0
            for version in to_rollback:
                if version in self.migrations:
                    print(f"MigrationManager: Rolling back migration {version}...", flush=True)
                    migration = self.migrations[version]
                    await migration.down(self.db)
                    await self._mark_rolled_back(version)
                    count += 1
                    print(
                        f"MigrationManager: Successfully rolled back migration {version} ({count}/{len(to_rollback)})",
                        flush=True)
                else:
                    print(f"MigrationManager: WARNING - Migration {version} not found in loaded migrations", flush=True)

            print(f"MigrationManager: Rollback complete. Rolled back {count} migrations", flush=True)
            return count
        except Exception as e:
            print(f"MigrationManager: ERROR during rollback: {e}", flush=True)
            return 0

    async def drop_tables(self):
        print("MigrationManager: Dropping all tables...", flush=True)
        try:
            drop_migration_history_table = "DROP TABLE IF EXISTS migration_history;"
            await self.db.multi_query([*model.drop_queries, drop_migration_history_table])
            print("MigrationManager: All tables dropped successfully", flush=True)
        except Exception as e:
            print(f"MigrationManager: ERROR dropping tables: {e}", flush=True)