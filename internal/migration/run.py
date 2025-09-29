import asyncio
import sys
import traceback
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent.parent))

from infrastructure.pg.pg import PG
from infrastructure.telemetry.telemetry import Telemetry
from internal.config.config import Config
from internal.migration.manager import MigrationManager


async def run_migrations(target_version: str):
    cfg = Config()

    tel = Telemetry(
        cfg.log_level,
        cfg.root_path,
        cfg.environment,
        cfg.service_name + "-migration",
        cfg.service_version,
        cfg.otlp_host,
        cfg.otlp_port,
        None
    )
    logger = tel.logger()

    # Инициализируем БД
    db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)

    # Создаем менеджер миграций
    manager = MigrationManager(tel, db)

    try:

        logger.info(f"🎯 Целевая версия миграции: {target_version}")

        # Показываем текущее состояние
        applied = await manager.get_applied_migrations()
        if applied:
            logger.info(f"📋 Применены миграции: {', '.join(applied)}")
        else:
            logger.info("📋 Нет примененных миграций")

        # Запускаем миграции
        count = await manager.migrate(target_version)

        if count > 0:
            logger.info(f"✅ Миграции успешно выполнены: {count} шт")
            return 0
        else:
            logger.info("✅ Все миграции уже применены")
            return 0

    except Exception as e:
        logger.error(f"❌ Ошибка выполнения миграций", {"traceback": traceback.format_exc()})
        return 1
    finally:
        tel.shutdown()


async def rollback_migration(target_version: str):
    cfg = Config()

    tel = Telemetry(
        cfg.log_level,
        cfg.root_path,
        cfg.environment,
        cfg.service_name + "-migration",
        cfg.service_version,
        cfg.otlp_host,
        cfg.otlp_port,
        None
    )

    db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)
    manager = MigrationManager(tel, db)

    try:
        await manager.rollback_migration(target_version)
        tel.logger().info(f"✅ Миграция {target_version} успешно откачена")
        return 0
    except Exception as e:
        tel.logger().error(f"❌ Ошибка отката миграции: {e}")
        return 1
    finally:
        tel.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Управление миграциями БД')
    parser.add_argument('command', choices=['up', 'down'], help='Команда: up или down')
    parser.add_argument('--version', help='Версия миграции (например, v1.0.1)')

    args = parser.parse_args()

    if args.command == 'up':
        exit_code = asyncio.run(run_migrations(args.version))
    else:  # down
        if not args.version:
            print("Для отката нужно указать версию: --version v1.0.1")
            sys.exit(1)
        exit_code = asyncio.run(rollback_migration(args.version))

    sys.exit(exit_code)