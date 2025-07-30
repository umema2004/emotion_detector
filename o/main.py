from fastapi import FastAPI
import socketio
import uvicorn
from collections import deque
import cv2
import csv
from datetime import datetime

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

# Ensure the CSV file is initialized
log_file = "feedback_log.csv"
with open(log_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Emotion", "Posture", "Feedback"])

@sio.on('frame')
async def process_frame(sid, data):
    frame = decode_frame(data['image'])

    # emotion
    emotion, lighting_feedback, center_feedback = classify_emotion(frame)
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
    if lighting_feedback:
        feedback.append(lighting_feedback)
    if center_feedback:
        feedback.append(center_feedback)

    emotion_summary = summarize_emotions(emotion_history)

    # Log to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, emotion, posture, "; ".join(feedback)])

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
