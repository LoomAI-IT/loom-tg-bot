create_state = """
INSERT INTO states (tg_chat_id)
VALUES (:tg_chat_id)
RETURNING id;
"""

state_by_id = """
SELECT * FROM states
WHERE tg_chat_id = :tg_chat_id;
"""

update_state_status = """
UPDATE states
SET status = :status
WHERE id = :state_id;
"""

delete_state_by_tg_chat_id = """
DELETE FROM states
WHERE tg_chat_id = :tg_chat_id;
"""
