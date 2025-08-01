import socketio
import uvicorn
import cv2
from datetime import datetime
import asyncio
import logging
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import shutil
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from utils.decode_utils import decode_frame
from utils.emotion_utils import classify_emotion
from utils.pose_utils import get_pose_results, classify_posture
from utils.feedback_utils import summarize_emotions, get_feedback

from utils.session_utils import get_session_id, get_session_template
from utils.logging_utils import initialize_log_file, log_to_csv, save_session_summary
from utils.summary_utils import generate_session_summary
from utils.cleanup_utils import cleanup_inactive_sessions

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("interview_analyzer")

# --- Setup and Configs ---
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #http://localhost:5500/upload.html
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/templates", StaticFiles(directory="templates"), name="templates")

UPLOAD_DIR = "uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

active_sessions = {}
session_lock = asyncio.Lock()

log_file = "feedback_log.csv"
initialize_log_file(log_file)

# --- Socket Events ---
@sio.on('connect')
async def connect(sid, environ):
    logger.info(f"Client {sid} connected")
    async with session_lock:
        active_sessions[sid] = get_session_template()

@sio.on('disconnect')
async def disconnect(sid):
    logger.info(f"Client {sid} disconnected")
    async with session_lock:
        if sid in active_sessions:
            del active_sessions[sid]

@sio.on('start_session')
async def start_session(sid):
    async with session_lock:
        active_sessions[sid] = get_session_template()
        session = active_sessions[sid]
        session['session_active'] = True
        session['session_id'] = get_session_id()
        session['start_time'] = datetime.now()

    initialize_log_file(log_file)

    logger.info(f"Started session {session['session_id']} for client {sid}")
    timestamp = session['start_time'].strftime("%Y-%m-%d %H:%M:%S")
    await log_to_csv([session['session_id'], timestamp, "SESSION_START", "", "Session started"], log_file)

@sio.on('end_session')
async def end_session(sid):
    async with session_lock:
        if sid not in active_sessions or not active_sessions[sid]['session_active']:
            return

        session = active_sessions[sid]
        session['session_active'] = False
        end_time = datetime.now()

    summary = generate_session_summary(session, end_time)
    save_session_summary(session['session_id'], summary)

    timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
    await log_to_csv([session['session_id'], timestamp, "SESSION_END", "", f"Session ended. Duration: {summary['duration']}"], log_file)

    logger.info(f"Ended session {session['session_id']} for client {sid}")
    await sio.emit('session_summary', summary, to=sid)

@sio.on('frame')
async def process_frame(sid, data):
    async with session_lock:
        if sid not in active_sessions or not active_sessions[sid]['session_active']:
            return
        session = active_sessions[sid]

    try:
        frame = decode_frame(data['image'])
        emotion, lighting_feedback, center_feedback = classify_emotion(frame)
        if emotion != "Unknown":
            session['emotion_history'].append(emotion)

        posture = "Unknown"
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = get_pose_results(frame_rgb)
        if pose_results.pose_landmarks:
            posture = classify_posture(pose_results)
            session['posture_history'].append(posture)

        feedback = get_feedback(emotion, posture)
        if lighting_feedback:
            feedback.append(lighting_feedback)
        if center_feedback:
            feedback.append(center_feedback)

        emotion_summary = summarize_emotions(list(session['emotion_history'])[-30:])
        session['feedback_count'] += 1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await log_to_csv([session['session_id'], timestamp, emotion, posture, "; ".join(feedback)], log_file)

        logger.info(f"Session {session['session_id']} - Emotion: {emotion} | Posture: {posture} | Feedback: {feedback}")
        logger.info(f"Trend Summary: {emotion_summary}")

        if list(session['emotion_history'])[-30:].count("No face detected") == 30:
            logger.info(f"Ending session {session['session_id']} due to prolonged 'No face detected'")
            await end_session(sid)
            return

        await sio.emit('feedback', {
            'emotion': emotion,
            'posture': posture,
            'feedback': feedback,
            'emotion_trend': emotion_summary,
            'session_active': True
        }, to=sid)

    except Exception as e:
        logger.error(f"Error processing frame for session {session.get('session_id', 'unknown')}: {e}")
        await sio.emit('feedback', {
            'emotion': 'Error',
            'posture': 'Error',
            'feedback': ['Error processing frame. Please try again.'],
            'emotion_trend': {},
            'session_active': True
        }, to=sid)

# --- Cleanup Inactive Sessions ---
@app.on_event("startup")
async def start_cleanup():
    asyncio.create_task(cleanup_inactive_sessions(active_sessions, session_lock))

# --- Routes ---
@app.get("/")
async def root():
    return RedirectResponse(url="/templates/start.html")

@app.get("/templates/start.html")
async def serve_start_page():
    return RedirectResponse(url="/templates/start.html")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/sessions")
async def get_active_sessions():
    session_info = {}
    async with session_lock:
        for sid, session in active_sessions.items():
            session_info[sid] = {
                'session_active': session['session_active'],
                'session_id': session['session_id'],
                'start_time': session['start_time'].strftime("%Y-%m-%d %H:%M:%S") if session['start_time'] else None,
                'feedback_count': session['feedback_count'],
                'emotion_count': len(session['emotion_history']),
                'posture_count': len(session['posture_history'])
            }
    return session_info

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")

    session_id = get_session_id()
    video_path = os.path.join(UPLOAD_DIR, f"{session_id}_{file.filename}")

    session = get_session_template()
    session["session_id"] = session_id
    session["session_active"] = True
    session["start_time"] = datetime.now()
    session['emotion_history'] = []
    session['posture_history'] = []

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            raise ValueError("Could not get video FPS.")

        frame_interval = int(fps * 5)
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                try:
                    emotion, lighting_feedback, center_feedback = classify_emotion(frame)
                    if emotion != "Unknown":
                        session['emotion_history'].append(emotion)

                    posture = "Unknown"
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pose_results = get_pose_results(frame_rgb)
                    if pose_results.pose_landmarks:
                        posture = classify_posture(pose_results)
                        session['posture_history'].append(posture)

                    feedback = get_feedback(emotion, posture)
                    if lighting_feedback:
                        feedback.append(lighting_feedback)
                    if center_feedback:
                        feedback.append(center_feedback)

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    await log_to_csv([session_id, timestamp, emotion, posture, "; ".join(feedback)], log_file)

                except Exception as e:
                    logger.error(f"[Frame {frame_count}] Error: {e}")

            frame_count += 1

        cap.release()
        session['session_active'] = False
        end_time = datetime.now()
        summary = generate_session_summary(session, end_time)

        # Normalize summary keys to match frontend
        summary['most_common_emotion'] = summary.pop('dominant_emotion', 'N/A')
        summary['most_common_posture'] = summary.pop('dominant_posture', 'N/A')

        save_session_summary(session_id, summary)

        return JSONResponse(content={
            "message": "Video uploaded and processed successfully!",
            "session_id": session_id,
            "summary": summary
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")



# --- Entry Point ---
if __name__ == "__main__":
    logger.info("\n🚀 Starting Interview Analyzer Backend...")
    logger.info("📊 Features:\n   - Real-time emotion detection\n   - Posture analysis\n   - Session tracking\n   - Logging + Summary")
    logger.info(f"📁 Logs -> {log_file}")
    logger.info("🌐 Running at http://localhost:8000")

    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
