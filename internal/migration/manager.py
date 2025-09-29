import time
import importlib
from pathlib import Path
from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface
from internal.migration.base import Migration


class MigrationManager:

    def __init__(
            self,
            tel: interface.ITelemetry,
            db: interface.IDB,
            auto_discover: bool = True
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.db = db
        self.migrations: dict[str, Migration] = {}

        if auto_discover:
            self._discover_migrations()

    def _discover_migrations(self):
        migration_dir = Path(__file__).parent / 'version'

        for file_path in sorted(migration_dir.glob('v*.py')):
            if file_path.stem == '__init__':
                continue

            try:
                module_name = f"internal.migration.version.{file_path.stem}"
                module = importlib.import_module(module_name)

                # Ищем класс, наследующий Migration
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                            issubclass(attr, Migration) and
                            attr != Migration):
                        migration = attr()
                        self.migrations[migration.info.version] = migration
                        self.logger.info(
                            f"Обнаружена миграция: {migration.info.version} - {migration.info.name}"
                        )

            except Exception as e:
                self.logger.error(f"Ошибка загрузки миграции {file_path}: {e}")

    async def get_applied_migrations(self) -> list[str]:
        with self.tracer.start_as_current_span(
                "MigrationManager.get_applied_migrations",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                query = """
SELECT version FROM migration_history
WHERE status = 'success'
ORDER BY version 
"""
                rows = await self.db.select(query, {})
                versions = [row[0] for row in rows]

                span.set_status(Status(StatusCode.OK))
                return versions

            except Exception as e:
                # Если таблицы еще нет, возвращаем пустой список
                if "migration_history" in str(e):
                    self.logger.info("Таблица migration_history еще не создана")
                    return []

                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_pending_migrations(self, target_version: str) -> list[Migration]:
        applied = await self.get_applied_migrations()
        pending = []

        # Получаем все версии до TARGET_VERSION включительно
        target_tuple = self._version_to_tuple(target_version)

        for version, migration in sorted(self.migrations.items()):
            version_tuple = self._version_to_tuple(version)

            # Проверяем, что версия <= целевой и еще не применена
            if version_tuple <= target_tuple and version not in applied:
                # Проверяем зависимости
                if await migration.validate_dependencies(applied):
                    pending.append(migration)
                else:
                    self.logger.warning(
                        f"Миграция {version} пропущена - не выполнены зависимости"
                    )

        return pending

    def _version_to_tuple(self, version: str) -> tuple:
        """Преобразует v1_0_0 в (1, 0, 0)"""
        version_str = version.lstrip('v')
        return tuple(map(int, version_str.split('_')))

    async def apply_migration(self, migration: Migration) -> bool:
        with self.tracer.start_as_current_span(
                f"MigrationManager.apply_migration.{migration.info.version}",
                kind=SpanKind.INTERNAL,
                attributes={
                    "migration.version": migration.info.version,
                    "migration.name": migration.info.name
                }
        ) as span:

            start_time = time.time()

            try:
                self.logger.info(f"Применяем миграцию {migration.info.version}: {migration.info.description}")

                # Применяем миграцию
                await migration.up(self.db)

                execution_time_ms = int((time.time() - start_time) * 1000)

                # Записываем в историю
                query = """
INSERT INTO migration_historyv(version, name, execution_time_ms, checksum, status)
VALUES (:version, :name, :execution_time_ms, :checksum, :status)
RETURNING id
"""

                await self.db.insert(query, {
                    'version': migration.info.version,
                    'name': migration.info.name,
                    'execution_time_ms': execution_time_ms,
                    'checksum': migration.calculate_checksum(),
                    'status': 'success'
                })

                self.logger.info(f"✅ Миграция {migration.info.version} применена за {execution_time_ms}мс")

                span.set_status(Status(StatusCode.OK))
                return True

            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)

                self.logger.error(f"❌ Ошибка применения миграции {migration.info.version}", {
                    "traceback": e
                })

                try:
                    query = """
INSERT INTO migration_history (version, name, execution_time_ms, status, error_message)
VALUES (:version, :name, :execution_time_ms, :status, :error_message)
"""

                    await self.db.insert(query, {
                        'version': migration.info.version,
                        'name': migration.info.name,
                        'execution_time_ms': execution_time_ms,
                        'status': 'failed',
                        'error_message': str(e)
                    })
                except:
                    pass

                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def rollback_migration(self, version: str) -> bool:
        """Откатывает миграцию"""
        with self.tracer.start_as_current_span(
                f"MigrationManager.rollback_migration.{version}",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                migration = self.migrations.get(version)
                if not migration:
                    raise ValueError(f"Миграция {version} не найдена")

                self.logger.info(f"Откатываем миграцию {version}")

                await migration.down(self.db)

                # Обновляем историю
                query = """
                        UPDATE migration_history
                        SET status      = 'rolled_back',
                            rollback_at = CURRENT_TIMESTAMP
                        WHERE version = :version \
                        """

                await self.db.update(query, {'version': version})

                self.logger.info(f"✅ Миграция {version} откачена")

                span.set_status(Status(StatusCode.OK))
                return True

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def migrate(self, target_version: str) -> int:
        with self.tracer.start_as_current_span(
                "MigrationManager.migrate",
                kind=SpanKind.INTERNAL
        ) as span:
            try:

                self.logger.info(f"🚀 Начинаем миграцию до версии {target_version}")

                # Сначала создаем таблицу истории, если её нет
                await self._ensure_migration_table()

                # Получаем список pending миграций
                pending = await self.get_pending_migrations(target_version)

                if not pending:
                    self.logger.info("✅ Нет новых миграций для применения")
                    span.set_status(Status(StatusCode.OK))
                    return 0

                self.logger.info(f"📋 Найдено {len(pending)} миграций для применения")

                applied_count = 0
                for migration in pending:
                    await self.apply_migration(migration)
                    applied_count += 1

                self.logger.info(f"✅ Успешно применено {applied_count} миграций")

                span.set_status(Status(StatusCode.OK))
                return applied_count

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def _ensure_migration_table(self):
        create_migration_history_table = """
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    checksum VARCHAR(64),
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    rollback_at TIMESTAMP
);

CREATE INDEX idx_migration_version ON migration_history(version);
CREATE INDEX idx_migration_status ON migration_history(status);
"""

        try:
            # Проверяем, существует ли таблица
            check_query = """
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'migration_history') 
"""
            result = await self.db.select(check_query, {})

            if not result[0][0]:
                self.logger.info("Создаем таблицу migration_history")
                await self.db.multi_query([create_migration_history_table])

        except Exception as e:
            self.logger.error(f"Ошибка создания таблицы миграций: {e}")
            raise