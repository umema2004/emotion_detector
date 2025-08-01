import asyncio
from datetime import datetime
import logging

logger = logging.getLogger("interview_analyzer")

async def cleanup_inactive_sessions(active_sessions, session_lock, timeout_seconds=300):
    while True:
        now = datetime.now()
        async with session_lock:
            for sid, session in list(active_sessions.items()):
                if session['start_time'] and not session['session_active']:
                    elapsed = (now - session['start_time']).total_seconds()
                    if elapsed > timeout_seconds:
                        del active_sessions[sid]
                        logger.info(f"Cleaned up inactive session {sid}")
        await asyncio.sleep(60)
