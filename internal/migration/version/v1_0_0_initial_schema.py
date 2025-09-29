from internal import interface, model
from internal.migration.base import Migration, MigrationInfo


class InitialSchemaMigration(Migration):

    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v1_0_0",
            name="initial_schema",
            description="Создание начальной схемы БД",
            checksum=self.calculate_checksum(),
        )

    async def up(self, db: interface.IDB):
        queries = [
            model.create_state_table,
            model.create_cache_files_table,
            model.create_vizard_video_cut_alerts_table
        ]

        await db.multi_query(queries)

    async def down(self, db: interface.IDB):
        queries = [
            model.drop_state_table,
            model.drop_cache_files_table,
            model.drop_vizard_video_cut_alerts_table
        ]

        await db.multi_query(queries)

