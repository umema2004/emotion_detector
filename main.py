from fastapi import FastAPI
import socketio
import uvicorn
from collections import deque, Counter
import cv2
from utils.decode_utils import decode_frame
from utils.emotion_utils import classify_emotion
from utils.pose_utils import get_pose_results, classify_posture
from utils.feedback_utils import summarize_emotions, get_feedback

# Setup and configs
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Emotion history
emotion_history = deque(maxlen=30)

@sio.on('frame')
async def process_frame(sid, data):
    if 'image' not in data or not isinstance(data['image'], str):
        await sio.emit('error', {'message': 'Invalid or missing image data'}, to=sid)
        return
    
    frame = decode_frame(data['image'])
    if frame is None:
        await sio.emit('error', {'message': 'Failed to decode frame'}, to=sid)
        return

    # Emotion analysis
    emotion, lighting_angle_feedback = classify_emotion(frame)
    if emotion not in ["Unknown", "No Face Detected"]:
        emotion_history.append(emotion)
    
    # Temporal smoothing
    if len(emotion_history) >= 5:
        emotion_counts = Counter(emotion_history)
        smoothed_emotion = emotion_counts.most_common(1)[0][0]
    else:
        smoothed_emotion = emotion

    # Posture analysis
    posture = "Unknown"
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pose_results = get_pose_results(frame_rgb)
    if pose_results and pose_results.pose_landmarks:
        posture = classify_posture(pose_results)

    # Feedback
    feedback = get_feedback(smoothed_emotion, posture)
    feedback.extend(lighting_angle_feedback)  # Add lighting/angle feedback
    emotion_summary = summarize_emotions(emotion_history)

    print(f"Emotion: {smoothed_emotion} | Posture: {posture} | Feedback: {feedback}")
    print(f"Trend Summary: {emotion_summary}")

    await sio.emit('feedback', {
        'emotion': smoothed_emotion,
        'posture': posture,
        'feedback': feedback,
        'emotion_trend': emotion_summary
    }, to=sid)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)