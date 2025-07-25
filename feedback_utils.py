from collections import Counter

def summarize_emotions(history):
    if not history:
        return {}
    counts = Counter(history)
    total = sum(counts.values())
    return {emotion: round((count / total) * 100, 2) for emotion, count in counts.items()}

def get_feedback(emotion, posture):
    feedback = []

    # Emotion feedback
    emotion_feedback = {
        'confident': "Great confidence! Keep engaging with your interviewer.",
        'nervous': "You seem nervous. Take deep breaths and speak slowly.",
        'calm': "You're maintaining a calm demeanor. Keep it up!",
        'frustrated': "You appear frustrated. Try to stay positive and focused.",
        'Unknown': "Please ensure your face is clearly visible.",
        'No Face Detected': "No face detected. Adjust your camera to show your face."
    }
    if emotion in emotion_feedback:
        feedback.append(emotion_feedback[emotion])

    # Posture feedback
    posture_feedback = {
        'Slouching': "Please straighten your shoulders for a more professional posture.",
        'Tilted Head': "Adjust your head to align with your body for better presence.",
        'Leaning Forward': "Sit back in your chair to appear more relaxed.",
        'Leaning Back': "Sit upright with your back supported to project confidence.",
        'No Pose Detected': "Ensure your upper body is visible in the camera."
    }
    if posture in posture_feedback:
        feedback.append(posture_feedback[posture])

    return feedback