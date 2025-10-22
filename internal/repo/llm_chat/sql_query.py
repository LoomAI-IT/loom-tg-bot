# Queries for llm_chat table
create_llm_chat = """
INSERT INTO llm_chats (state_id)
VALUES (:state_id)
RETURNING id;
"""

delete_llm_chat = """
DELETE FROM llm_chats
WHERE id = :chat_id;
"""

get_llm_chat_by_id = """
SELECT * FROM llm_chats
WHERE id = :chat_id;
"""

get_llm_chat_by_state_id = """
SELECT * FROM llm_chats
WHERE state_id = :state_id;
"""

# Queries for llm_message table
create_llm_message = """
INSERT INTO llm_messages (chat_id, role, text)
VALUES (:chat_id, :role, :text)
RETURNING id;
"""

get_all_messages_by_chat_id = """
SELECT * FROM llm_messages
WHERE chat_id = :chat_id
ORDER BY created_at ASC;
"""

delete_all_messages_by_chat_id = """
DELETE FROM llm_messages
WHERE chat_id = :chat_id;
"""

delete_message_by_id = """
DELETE FROM llm_messages
WHERE id = :message_id;
"""

get_message_by_id = """
SELECT * FROM llm_messages
WHERE id = :message_id;
"""