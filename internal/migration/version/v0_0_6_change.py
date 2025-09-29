from internal import interface, model
from internal.migration.base import Migration, MigrationInfo


class AddUserPreferencesMigration(Migration):

    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v0_0_6",
            name="add_user_preferences",
            depends_on="v0_0_1"
        )

    async def up(self, db: interface.IDB):
        queries = [
            add_last_active_column_to_user_states,
        ]

        await db.multi_query(queries)

    async def down(self, db: interface.IDB):
        queries = [
            drop_last_active_column_from_user_states,
        ]

        await db.multi_query(queries)

add_last_active_column_to_user_states = """
ALTER TABLE user_states 
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
"""

drop_last_active_column_from_user_states = """
ALTER TABLE user_states 
DROP COLUMN IF EXISTS last_active_at;
"""
