from internal import interface, model
from internal.migration.base import Migration, MigrationInfo


class AddLLMChatTablesMigration(Migration):

    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v0_0_26",
            name="add_llm_chat_tables",
            depends_on="v0_0_20"
        )

    async def up(self, db: interface.IDB):
        queries = [
            create_llm_chats_table,
            create_llm_messages_table
        ]

        await db.multi_query(queries)

    async def down(self, db: interface.IDB):
        queries = [
            drop_llm_messages_table,
            drop_llm_chats_table
        ]

        await db.multi_query(queries)


create_llm_chats_table = """
CREATE TABLE IF NOT EXISTS llm_chats (
    id SERIAL PRIMARY KEY,
    state_id INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

create_llm_messages_table = """
CREATE TABLE IF NOT EXISTS llm_messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL,

    role TEXT NOT NULL,
    text TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_llm_chats_table = """
DROP TABLE IF EXISTS llm_chats;
"""

drop_llm_messages_table = """
DROP TABLE IF EXISTS llm_messages;
"""