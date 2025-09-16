create_state_table = """
CREATE TABLE IF NOT EXISTS user_states (
    id SERIAL PRIMARY KEY,
    tg_chat_id BIGINT NOT NULL,
    account_id INTEGER DEFAULT 0,
    organization_id INTEGER DEFAULT 0,
    
    access_token TEXT DEFAULT '',
    refresh_token TEXT DEFAULT '',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_state_table = """
DROP TABLE IF EXISTS user_states;
"""


create_queries = [create_state_table]
drop_queries = [drop_state_table]
