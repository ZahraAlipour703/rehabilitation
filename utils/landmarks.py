import mediapipe as mp

def landmarks_to_dict(landmarks):
    """
    Accepts:
      - MediaPipe: results.pose_landmarks.landmark (list)
      - other list/None
    Returns dict mapping POSE landmark names to (x,y,z) in normalized coords.
    """
    out = {}
    try:
        for i, lm in enumerate(landmarks):
            name = mp.solutions.pose.PoseLandmark(i).name
            out[name] = (float(lm.x), float(lm.y), float(getattr(lm, "z", 0.0)))
    except Exception:
        # fallback: empty dict
        pass
    return out
