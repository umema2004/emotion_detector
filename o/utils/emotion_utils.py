from deepface import DeepFace
import cv2
import numpy as np
from collections import deque, Counter
import logging

# --- Setup ---
logging.basicConfig(level=logging.INFO)
emotion_window = deque(maxlen=10)

# --- Preprocessing ---
def preprocess_frame(frame):
    """Resize, normalize, and enhance the input frame."""
    frame = cv2.resize(frame, (640, 480))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.equalizeHist(frame)
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    frame = cv2.convertScaleAbs(frame)
    return frame

# --- Emotion Classification ---
def classify_emotion(frame, threshold=0.5):
    """
    Detect emotion with smoothing, lighting feedback, and face centering check.
    Returns:
        - Emotion label (string)
        - Feedback string for lighting/centering (or None)
    """
    try:
        frame = preprocess_frame(frame)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Lighting check
        avg_brightness = np.mean(gray_frame)
        lighting_feedback = "Lighting is too dark" if avg_brightness < 50 else None

        # Face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return "No face detected", lighting_feedback, None
        elif len(faces) > 1:
            return "Multiple faces detected", lighting_feedback, None

        # Use first face
        x, y, w, h = faces[0]
        face_roi = frame[y:y+h, x:x+w]

        # Centering feedback
        frame_center_x, frame_center_y = frame.shape[1] // 2, frame.shape[0] // 2
        face_center_x, face_center_y = x + w // 2, y + h // 2
        center_feedback = "Face is not centered" if abs(face_center_x - frame_center_x) > frame.shape[1] * 0.2 else None

        #rectangle (for UI display)
        # cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Resize face ROI for DeepFace
        face_roi_resized = cv2.resize(face_roi, (224, 224))

        # Emotion analysis
        results = DeepFace.analyze(
            face_roi_resized,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='mediapipe',
            silent=True
        )

        dominant_emotion = results[0]['dominant_emotion']
        confidence = results[0]['emotion'][dominant_emotion]

        # --- Emotion conversion logic ---
        if dominant_emotion == 'fear':
            dominant_emotion = 'neutral'
        elif dominant_emotion == 'neutral':
            dominant_emotion = 'calm'
        # --- End of conversion logic ---

        logging.info(f"Detected emotion: {dominant_emotion} (confidence: {confidence:.2f})")

        if confidence < threshold:
            return "Uncertain", lighting_feedback, center_feedback

        # Smooth using rolling window
        emotion_window.append(dominant_emotion)
        most_common = Counter(emotion_window).most_common(1)

        return most_common[0][0] if most_common else "Unknown", lighting_feedback, center_feedback

    except Exception as e:
        logging.error(f"Emotion classification failed: {str(e)}")
        return "Unknown", None, None