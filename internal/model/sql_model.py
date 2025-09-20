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
create_cache_files_table = """
CREATE TABLE IF NOT EXISTS cache_files (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    file_id TEXT NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_state_table = """
DROP TABLE IF EXISTS user_states;
"""

drop_cache_files_table = """
DROP TABLE IF EXISTS cache_files;
"""


create_queries = [create_state_table, create_cache_files_table]
drop_queries = [drop_state_table, drop_cache_files_table]
