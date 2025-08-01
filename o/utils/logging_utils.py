import csv
import os
import json
from datetime import datetime
import asyncio

csv_lock = asyncio.Lock()

def initialize_log_file(path="feedback_log.csv"):
    # The file is overwritten every time a new session starts
    with open(path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Session_ID", "Timestamp", "Emotion", "Posture", "Feedback"])

async def log_to_csv(row, path="feedback_log.csv"):
    async with csv_lock:
        with open(path, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(row)

def save_session_summary(session_id, summary):
    os.makedirs("summaries", exist_ok=True)
    with open(f"summaries/{session_id}_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)