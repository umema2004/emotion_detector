#emotion detection, smoothing

from deepface import DeepFace

def classify_emotion(frame):
    try:
        results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        return results[0]['dominant_emotion']
    except Exception:
        return "Unknown"
