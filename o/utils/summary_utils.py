from collections import Counter
from datetime import datetime

def generate_session_summary(session, end_time):
    duration = end_time - session['start_time']
    duration_str = str(duration).split('.')[0]

    emotion_counts = Counter(session['emotion_history'])
    total_emotions = len(session['emotion_history'])
    emotion_summary = {
        emotion: round((count / total_emotions) * 100, 1)
        for emotion, count in emotion_counts.items()
    } if total_emotions else {"No data": 100}

    posture_counts = Counter(session['posture_history'])
    total_postures = len(session['posture_history'])
    posture_summary = {
        posture: round((count / total_postures) * 100, 1)
        for posture, count in posture_counts.items()
    } if total_postures else {"No data": 100}

    dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "Unknown"
    dominant_posture = max(posture_counts, key=posture_counts.get) if posture_counts else "Unknown"

    return {
        'session_id': session['session_id'],
        'duration': duration_str,
        'total_frames_analyzed': session['feedback_count'],
        'emotion_summary': emotion_summary,
        'posture_summary': posture_summary,
        'dominant_emotion': dominant_emotion,
        'dominant_posture': dominant_posture,
        'start_time': session['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S")
    }
