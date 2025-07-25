import mediapipe as mp
import cv2
import numpy as np
import onnxruntime as ort

# Initialize MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# Load ONNX model
emotion_model = ort.InferenceSession('emotion_model.onnx')
emotion_labels = ['happy', 'sad', 'angry', 'neutral', 'fear', 'disgust', 'surprise']

def preprocess_frame(frame):
    """Preprocess frame for emotion detection."""
    frame = cv2.resize(frame, (224, 224))
    frame = frame / 255.0
    frame = np.expand_dims(frame, axis=0).astype(np.float32)
    return frame

def check_lighting_and_angle(frame, face_results):
    """Check lighting and camera angle, return feedback."""
    feedback = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    if mean_brightness < 50:
        feedback.append("Lighting is too dim. Please increase brightness or move to a well-lit area.")
    elif mean_brightness > 200:
        feedback.append("Lighting is too bright. Reduce glare or adjust lighting.")
    
    if face_results.detections:
        detection = face_results.detections[0]
        bbox = detection.location_data.relative_bounding_box
        h, w = frame.shape[:2]
        x_center = (bbox.xmin + bbox.width / 2) * w
        if x_center < w * 0.3 or x_center > w * 0.7:
            feedback.append("Please center your face in the camera frame.")
        if bbox.ymin * h < h * 0.2:
            feedback.append("Your face is too close to the top. Adjust the camera to center your face.")
    
    return feedback

def classify_emotion(frame):
    """Classify emotion with ONNX model and MediaPipe face detection."""
    try:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_results = face_detection.process(frame_rgb)
        lighting_angle_feedback = check_lighting_and_angle(frame, face_results)
        
        if not face_results.detections:
            return "No Face Detected", lighting_angle_feedback
        
        detection = face_results.detections[0]
        bbox = detection.location_data.relative_bounding_box
        h, w = frame.shape[:2]
        x, y = int(bbox.xmin * w), int(bbox.ymin * h)
        width, height = int(bbox.width * w), int(bbox.height * h)
        face_crop = frame[y:y+height, x:x+width]
        
        face_crop = preprocess_frame(face_crop)
        inputs = {emotion_model.get_inputs()[0].name: face_crop}
        predictions = emotion_model.run(None, inputs)[0]
        emotion_idx = np.argmax(predictions[0])
        emotion = emotion_labels[emotion_idx]
        
        # Map to interview context
        if emotion == 'happy':
            emotion = 'confident'
        elif emotion in ['fear', 'sad']:
            emotion = 'nervous'
        elif emotion == 'neutral':
            emotion = 'calm'
        elif emotion == 'angry':
            emotion = 'frustrated'
        
        return emotion, lighting_angle_feedback
    except Exception as e:
        print(f"Emotion detection error: {e}")
        return "Unknown", lighting_angle_feedback