create_state_table = """
CREATE TABLE IF NOT EXISTS user_states (
    id SERIAL PRIMARY KEY,
    tg_chat_id BIGINT NOT NULL,
    account_id INTEGER DEFAULT 0,
    organization_id INTEGER DEFAULT 0,
    
    access_token TEXT DEFAULT '',
    refresh_token TEXT DEFAULT '',
    tg_username TEXT DEFAULT '',
    can_show_alerts BOOLEAN DEFAULT TRUE,
    show_error_recovery BOOLEAN DEFAULT FALSE,
    
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

create_vizard_video_cut_alerts_table = """
CREATE TABLE IF NOT EXISTS vizard_video_cut_alerts (
    id SERIAL PRIMARY KEY,
    state_id INTEGER NOT NULL,
    youtube_video_reference TEXT NOT NULL,
    video_count INTEGER NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_state_table = """
DROP TABLE IF EXISTS user_states;
"""

drop_cache_files_table = """
DROP TABLE IF EXISTS cache_files;
"""

drop_vizard_video_cut_alerts_table = """
DROP TABLE IF EXISTS vizard_video_cut_alerts;
"""


create_queries = [create_state_table, create_cache_files_table, create_vizard_video_cut_alerts_table]
drop_queries = [drop_state_table, drop_cache_files_table, drop_vizard_video_cut_alerts_table]
