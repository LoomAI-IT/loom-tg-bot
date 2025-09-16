create_state = """
INSERT INTO user_states (tg_chat_id)
VALUES (:tg_chat_id)
RETURNING id;
"""

state_by_id = """
SELECT * FROM user_states
WHERE tg_chat_id = :tg_chat_id;
"""

delete_state_by_tg_chat_id = """
DELETE FROM user_states
WHERE tg_chat_id = :tg_chat_id;
"""
