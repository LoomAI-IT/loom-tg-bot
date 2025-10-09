from internal import interface, model
from internal.migration.base import Migration, MigrationInfo


class AddPublicationApprovedAlertMigration(Migration):

    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v0_0_19",
            name="add_publication_approved_alert",
            depends_on="v0_0_1"
        )

    async def up(self, db: interface.IDB):
        queries = [
            create_publication_approved_alerts_table
        ]

        await db.multi_query(queries)

    async def down(self, db: interface.IDB):
        queries = [
            drop_publication_approved_alerts_table
        ]

        await db.multi_query(queries)


create_publication_approved_alerts_table = """
CREATE TABLE IF NOT EXISTS publication_approved_alerts (
    id SERIAL PRIMARY KEY,
    state_id INTEGER NOT NULL,
    publication_id INTEGER NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_publication_approved_alerts_table = """
DROP TABLE IF EXISTS publication_approved_alerts;
"""