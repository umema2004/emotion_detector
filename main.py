from fastapi import FastAPI
import socketio
import uvicorn
from collections import deque
import cv2

from utils.decode_utils import decode_frame
from utils.emotion_utils import classify_emotion
from utils.pose_utils import get_pose_results, classify_posture
from utils.feedback_utils import summarize_emotions, get_feedback

#setup and configs
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# emotion history
emotion_history = deque(maxlen=30)

@sio.on('frame')
async def process_frame(sid, data):
    frame = decode_frame(data['image'])

    # emotion
    emotion = classify_emotion(frame)
    if emotion != "Unknown":
        emotion_history.append(emotion)

    # posture
    posture = "Unknown"
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pose_results = get_pose_results(frame_rgb)
    if pose_results.pose_landmarks:
        posture = classify_posture(pose_results)

    # feedback
    feedback = get_feedback(emotion, posture)
    emotion_summary = summarize_emotions(emotion_history)

    print(f"Emotion: {emotion} | Posture: {posture} | Feedback: {feedback}")
    print(f"Trend Summary: {emotion_summary}")

    await sio.emit('feedback', {
        'emotion': emotion,
        'posture': posture,
        'feedback': feedback,
        'emotion_trend': emotion_summary
    }, to=sid)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
