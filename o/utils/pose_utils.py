#pose detection, classification

import mediapipe as mp

mp_pose = mp.solutions.pose
pose= mp_pose.Pose()

def get_pose_results(frame):
    # Process the frame with MediaPipe Pose
    results = pose.process(frame)
    return results

def classify_posture(results):
    # Classify the posture based on landmarks
    if not results.pose_landmarks:
        return "No Pose Detected"

    landmarks = results.pose_landmarks.landmark
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    nose = landmarks[mp_pose.PoseLandmark.NOSE]
    left_ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR]
    right_ear = landmarks[mp_pose.PoseLandmark.RIGHT_EAR]

    posture = "Upright"

    # Slouching: shoulders not aligned vertically
    shoulder_slope = abs(left_shoulder.y - right_shoulder.y)
    if shoulder_slope > 0.1:
        posture = "Slouching"

    # Head tilt detection: horizontal misalignment
    if abs(left_ear.x - right_ear.x) > 0.2:
        posture = "Tilted Head"

    # Leaning forward/backward with z-coordinates
    avg_shoulder_z = (left_shoulder.z + right_shoulder.z) / 2
    head_forward = nose.z < avg_shoulder_z - 0.1
    head_backward = nose.z > avg_shoulder_z + 0.1

    if head_forward:
        posture = "Leaning Forward"
    elif head_backward:
        posture = "Leaning Back"

    return posture
