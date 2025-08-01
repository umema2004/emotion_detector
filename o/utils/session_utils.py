from datetime import datetime
from collections import deque

def get_session_template():
    return {
        'session_active': False,
        'session_id': None,
        'emotion_history': deque(maxlen=100),
        'posture_history': deque(maxlen=100),
        'start_time': None,
        'feedback_count': 0
    }

def get_session_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")
