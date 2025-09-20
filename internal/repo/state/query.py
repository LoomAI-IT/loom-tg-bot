create_state = """
INSERT INTO user_states (tg_chat_id)
VALUES (:tg_chat_id)
RETURNING id;
"""

state_by_id = """
SELECT * FROM user_states
WHERE tg_chat_id = :tg_chat_id;
"""

state_by_account_id = """
SELECT * FROM user_states
WHERE account_id = :account_id;
"""

set_cache_file = """
INSERT INTO cache_files (filename, file_id)
VALUES (:filename, :file_id)
RETURNING id;
"""

get_cache_file = """
SELECT * FROM cache_files
WHERE filename = :filename;
"""

delete_state_by_tg_chat_id = """
DELETE FROM user_states
WHERE tg_chat_id = :tg_chat_id;
"""
