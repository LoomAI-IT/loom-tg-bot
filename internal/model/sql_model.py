create_state_table = """
CREATE TABLE IF NOT EXISTS states (
    id SERIAL PRIMARY KEY,
    tg_chat_id BIGINT DEFAULT NULL,
    
    status TEXT DEFAULT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_state_table = """
DROP TABLE IF EXISTS states;
"""


create_queries = [create_state_table]
drop_queries = [drop_state_table]
