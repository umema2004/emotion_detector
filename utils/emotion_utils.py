from deepface import DeepFace
import cv2
import numpy as np
from collections import deque, Counter

# Rolling window for smoothing
emotion_window = deque(maxlen=10)

def preprocess_frame(frame):
    """Resize and normalize the input frame."""
    frame = cv2.resize(frame, (640, 480))
    frame = cv2.convertScaleAbs(frame)  # Normalize contrast/brightness
    return frame

def classify_emotion(frame):
    """
    Detect emotion with smoothing, improved face detection, and preprocessing.
    """
    try:
        # Preprocess frame for quality
        frame = preprocess_frame(frame)

        # Convert frame to grayscale for face detection
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Load OpenCV's pre-trained face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Feedback for no face or multiple faces detected
        if len(faces) == 0:
            return "No face detected"
        elif len(faces) > 1:
            return "Multiple faces detected"

        # Draw bounding box around detected face
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Analyze with improved backend
        results = DeepFace.analyze(
            frame,
            actions=['emotion'],
            enforce_detection=False,  # Set to True to skip frames with no face
            detector_backend='mediapipe',
            silent=True
        )

        # Get dominant emotion and confidence
        dominant_emotion = results[0]['dominant_emotion']
        emotion_scores = results[0]['emotion']
        confidence = emotion_scores[dominant_emotion]

        # Confidence threshold (optional)
        if confidence < 0.4:
            return "Uncertain"

        # Update window and return smoothed result
        emotion_window.append(dominant_emotion)
        most_common = Counter(emotion_window).most_common(1)
        return most_common[0][0] if most_common else "Unknown"

    except Exception:
        return "Unknown"
