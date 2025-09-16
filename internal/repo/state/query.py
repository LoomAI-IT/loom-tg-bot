create_state = """
INSERT INTO dialog_states (tg_chat_id)
VALUES (:tg_chat_id)
RETURNING id;
"""

state_by_id = """
SELECT * FROM dialog_states
WHERE tg_chat_id = :tg_chat_id;
"""

update_state_status = """
UPDATE dialog_states
SET status = :status
WHERE id = :state_id;
"""

delete_state_by_tg_chat_id = """
DELETE FROM dialog_states
WHERE tg_chat_id = :tg_chat_id;
"""
