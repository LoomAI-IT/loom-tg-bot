from internal import interface, model
from internal.migration.base import Migration, MigrationInfo


class AddUserPreferencesMigration(Migration):

    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v0_0_6",
            name="add_user_preferences",
        )

    async def up(self, db: interface.IDB):
        queries = [
            create_user_preferences_table,
            create_notification_settings_table,
            add_last_active_column_to_user_states,
            create_index_on_tg_chat_id
        ]

        await db.multi_query(queries)

    async def down(self, db: interface.IDB):
        queries = [
            drop_index_on_tg_chat_id,
            drop_last_active_column_from_user_states,
            drop_notification_settings_table,
            drop_user_preferences_table
        ]

        await db.multi_query(queries)


# UP queries
create_user_preferences_table = """
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    state_id INTEGER NOT NULL REFERENCES user_states(id) ON DELETE CASCADE,
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    theme VARCHAR(20) DEFAULT 'light',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(state_id)
);
"""

create_notification_settings_table = """
CREATE TABLE IF NOT EXISTS notification_settings (
    id SERIAL PRIMARY KEY,
    state_id INTEGER NOT NULL REFERENCES user_states(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT FALSE,
    push_notifications BOOLEAN DEFAULT TRUE,
    notification_frequency VARCHAR(20) DEFAULT 'instant',
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(state_id)
);
"""

add_last_active_column_to_user_states = """
ALTER TABLE user_states 
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
"""

create_index_on_tg_chat_id = """
CREATE INDEX IF NOT EXISTS idx_user_states_tg_chat_id 
ON user_states(tg_chat_id);
"""


# DOWN queries
drop_user_preferences_table = """
DROP TABLE IF EXISTS user_preferences;
"""

drop_notification_settings_table = """
DROP TABLE IF EXISTS notification_settings;
"""

drop_last_active_column_from_user_states = """
ALTER TABLE user_states 
DROP COLUMN IF EXISTS last_active_at;
"""

drop_index_on_tg_chat_id = """
DROP INDEX IF EXISTS idx_user_states_tg_chat_id;
"""