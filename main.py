from fastapi import FastAPI
import socketio
import uvicorn
from collections import deque, Counter
import cv2
import csv
from datetime import datetime
import os

from utils.decode_utils import decode_frame
from utils.emotion_utils import classify_emotion
from utils.pose_utils import get_pose_results, classify_posture
from utils.feedback_utils import summarize_emotions, get_feedback

# Setup and configs
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Session management
active_sessions = {}  # Store session data for each client

# Ensure the CSV file is initialized
log_file = "feedback_log.csv"
if not os.path.exists(log_file):
    with open(log_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Session_ID", "Timestamp", "Emotion", "Posture", "Feedback"])

def get_session_id():
    """Generate a unique session ID"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

@sio.on('connect')
async def connect(sid, environ):
    print(f"Client {sid} connected")
    # Initialize session data for this client
    active_sessions[sid] = {
        'session_active': False,
        'session_id': None,
        'emotion_history': deque(maxlen=100),  # Store more for better summaries
        'posture_history': deque(maxlen=100),
        'start_time': None,
        'feedback_count': 0
    }

@sio.on('disconnect')
async def disconnect(sid):
    print(f"Client {sid} disconnected")
    # Clean up session data
    if sid in active_sessions:
        del active_sessions[sid]

@sio.on('start_session')
async def start_session(sid):
    """Start a new analysis session"""
    if sid not in active_sessions:
        active_sessions[sid] = {
            'session_active': False,
            'session_id': None,
            'emotion_history': deque(maxlen=100),
            'posture_history': deque(maxlen=100),
            'start_time': None,
            'feedback_count': 0
        }
    
    session = active_sessions[sid]
    session['session_active'] = True
    session['session_id'] = get_session_id()
    session['start_time'] = datetime.now()
    session['emotion_history'].clear()
    session['posture_history'].clear()
    session['feedback_count'] = 0
    
    print(f"Started session {session['session_id']} for client {sid}")
    
    # Log session start
    timestamp = session['start_time'].strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([session['session_id'], timestamp, "SESSION_START", "", "Session started"])

@sio.on('end_session')
async def end_session(sid):
    """End the current analysis session and generate summary"""
    if sid not in active_sessions or not active_sessions[sid]['session_active']:
        return
    
    session = active_sessions[sid]
    session['session_active'] = False
    end_time = datetime.now()
    
    print(f"Ended session {session['session_id']} for client {sid}")
    
    # Generate session summary
    summary = generate_session_summary(session, end_time)
    
    # Log session end
    timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([session['session_id'], timestamp, "SESSION_END", "", f"Session ended. Duration: {summary['duration']}"])
    
    # Send summary to client
    await sio.emit('session_summary', summary, to=sid)

def generate_session_summary(session, end_time):
    """Generate a comprehensive session summary"""
    duration = end_time - session['start_time']
    duration_str = str(duration).split('.')[0]  # Remove microseconds
    
    # Calculate emotion percentages
    emotion_counts = Counter(session['emotion_history'])
    total_emotions = len(session['emotion_history'])
    emotion_summary = {}
    
    if total_emotions > 0:
        for emotion, count in emotion_counts.items():
            percentage = round((count / total_emotions) * 100, 1)
            emotion_summary[emotion] = percentage
    else:
        emotion_summary = {"No data": 100}
    
    # Calculate posture percentages
    posture_counts = Counter(session['posture_history'])
    total_postures = len(session['posture_history'])
    posture_summary = {}
    
    if total_postures > 0:
        for posture, count in posture_counts.items():
            percentage = round((count / total_postures) * 100, 1)
            posture_summary[posture] = percentage
    else:
        posture_summary = {"No data": 100}
    
    # Determine dominant emotion and posture
    dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "Unknown"
    dominant_posture = max(posture_counts, key=posture_counts.get) if posture_counts else "Unknown"
    
    return {
        'session_id': session['session_id'],
        'duration': duration_str,
        'total_frames_analyzed': session['feedback_count'],
        'emotion_summary': emotion_summary,
        'posture_summary': posture_summary,
        'dominant_emotion': dominant_emotion,
        'dominant_posture': dominant_posture,
        'start_time': session['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S")
    }

@sio.on('frame')
async def process_frame(sid, data):
    """Process video frame for emotion and posture analysis"""
    # Check if session is active for this client
    if sid not in active_sessions or not active_sessions[sid]['session_active']:
        return
    
    session = active_sessions[sid]
    
    try:
        frame = decode_frame(data['image'])
        
        # Emotion analysis
        emotion, lighting_feedback, center_feedback = classify_emotion(frame)
        if emotion != "Unknown":
            session['emotion_history'].append(emotion)
        
        # Posture analysis
        posture = "Unknown"
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = get_pose_results(frame_rgb)
        if pose_results.pose_landmarks:
            posture = classify_posture(pose_results)
            session['posture_history'].append(posture)
        
        # Generate feedback
        feedback = get_feedback(emotion, posture)
        if lighting_feedback:
            feedback.append(lighting_feedback)
        if center_feedback:
            feedback.append(center_feedback)
        
        # Get emotion trend summary
        emotion_summary = summarize_emotions(list(session['emotion_history'])[-30:])  # Last 30 for trend
        
        # Increment feedback counter
        session['feedback_count'] += 1
        
        # Log to CSV with session ID
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([session['session_id'], timestamp, emotion, posture, "; ".join(feedback)])
        
        print(f"Session {session['session_id']} - Emotion: {emotion} | Posture: {posture} | Feedback: {feedback}")
        print(f"Trend Summary: {emotion_summary}")
        
        # Send feedback to client
        await sio.emit('feedback', {
            'emotion': emotion,
            'posture': posture,
            'feedback': feedback,
            'emotion_trend': emotion_summary,
            'session_active': True
        }, to=sid)
        
    except Exception as e:
        print(f"Error processing frame for session {session.get('session_id', 'unknown')}: {e}")
        await sio.emit('feedback', {
            'emotion': 'Error',
            'posture': 'Error',
            'feedback': ['Error processing frame. Please try again.'],
            'emotion_trend': {},
            'session_active': True
        }, to=sid)

@app.get("/")
async def root():
    return {"message": "Interview Analyzer Backend is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/sessions")
async def get_active_sessions():
    """Get information about currently active sessions"""
    session_info = {}
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

if __name__ == "__main__":
    print("🚀 Starting Interview Analyzer Backend...")
    print("📊 Features enabled:")
    print("   - Real-time emotion detection")
    print("   - Posture analysis")
    print("   - Session management")
    print("   - CSV logging with session tracking")
    print("   - Session summaries")
    print(f"📁 Logs will be saved to: {log_file}")
    print("🌐 Server starting on http://localhost:8000")
    
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
