#rule based feedback, trend summaries

from collections import Counter

def summarize_emotions(history):          #freq distribution of recent emotions
    counts = Counter(history)
    total = sum(counts.values())
    return {emotion: round((count / total) * 100, 2) for emotion, count in counts.items()}

def get_feedback(emotion, posture):
    feedback = []

    #emotion feedback
    if emotion == "happy":
        feedback.append("Great job! Keep smiling!")
    elif emotion == "sad":
        feedback.append("It's okay to feel sad. Take a moment for yourself.")
    elif emotion == "angry":
        feedback.append("Try to take deep breaths and relax.")
    elif emotion == "neutral":
        feedback.append("Maintain a positive mindset.")

    #posture feedback
    if posture == "Slouching":
        feedback.append("Please straighten your shoulders.")
    elif posture == "Tilted Head":
        feedback.append("Adjust your head position for better alignment.")
    elif posture == "Leaning Forward":
        feedback.append("Try to sit back in your chair.")
    elif posture == "Leaning Back":
        feedback.append("Ensure your back is straight and supported.")

    return feedback
