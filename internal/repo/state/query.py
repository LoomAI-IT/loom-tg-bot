create_state = """
INSERT INTO user_states (tg_chat_id, tg_username)
VALUES (:tg_chat_id, :tg_username)
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

create_vizard_video_cut_alert = """
INSERT INTO vizard_video_cut_alerts (state_id, youtube_video_reference, video_count)
VALUES (:state_id, :youtube_video_reference, :video_count)
RETURNING id;
"""

get_vizard_video_cut_alert_by_state_id = """
SELECT * FROM vizard_video_cut_alerts
WHERE state_id = :state_id;
"""

delete_vizard_video_cut_alert = """
DELETE FROM vizard_video_cut_alerts
WHERE state_id = :state_id;
"""

create_publication_approved_alert = """
INSERT INTO publication_approved_alerts (state_id, publication_id)
VALUES (:state_id, :publication_id)
RETURNING id;
"""

get_publication_approved_alert_by_state_id = """
SELECT * FROM publication_approved_alerts
WHERE state_id = :state_id;
"""

delete_publication_approved_alert = """
DELETE FROM publication_approved_alerts
WHERE state_id = :state_id;
"""

create_publication_rejected_alert = """
INSERT INTO publication_rejected_alerts (state_id, publication_id)
VALUES (:state_id, :publication_id)
RETURNING id;
"""

get_publication_rejected_alert_by_state_id = """
SELECT * FROM publication_rejected_alerts
WHERE state_id = :state_id;
"""

delete_publication_rejected_alert = """
DELETE FROM publication_rejected_alerts
WHERE state_id = :state_id;
"""