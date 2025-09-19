# utils/draw.py
import cv2

# simple list of useful connections (subset of MediaPipe pose connections)
DEFAULT_CONNECTIONS = [
    ("NOSE", "LEFT_SHOULDER"),
    ("NOSE", "RIGHT_SHOULDER"),
    ("LEFT_SHOULDER", "LEFT_ELBOW"),
    ("LEFT_ELBOW", "LEFT_WRIST"),
    ("RIGHT_SHOULDER", "RIGHT_ELBOW"),
    ("RIGHT_ELBOW", "RIGHT_WRIST"),
    ("LEFT_SHOULDER", "LEFT_HIP"),
    ("RIGHT_SHOULDER", "RIGHT_HIP"),
    ("LEFT_HIP", "LEFT_KNEE"),
    ("LEFT_KNEE", "LEFT_ANKLE")
]


def draw_skeleton(frame, landmarks, color=(200, 200, 200), thickness=3, connections=None):
    """
    Draw skeleton on `frame` given `landmarks` dict with normalized coords (x,y,z).
    - landmarks: {"LEFT_SHOULDER": (x,y,z), ...}
    - color: BGR tuple
    """
    if connections is None:
        connections = DEFAULT_CONNECTIONS
    h, w = frame.shape[:2]

    # draw bones
    for a, b in connections:
        if a in landmarks and b in landmarks:
            ax, ay, _ = landmarks[a]
            bx, by, _ = landmarks[b]
            pt_a = (int(ax * w), int(ay * h))
            pt_b = (int(bx * w), int(by * h))
            cv2.line(frame, pt_a, pt_b, color, thickness, lineType=cv2.LINE_AA)

    # draw joints
    for name, (x, y, _) in landmarks.items():
        cx, cy = int(x * w), int(y * h)
        cv2.circle(frame, (cx, cy), 5, (255, 255, 0), -1)  # bright marker


def overlay_reference_corner(frame, ref_pose, size_px=220, bg_color=(30, 30, 30),
                             label=None, label_color=(255,255,255)):
    """
    Render a small reference skeleton in a corner (returns frame with overlay applied in-place).
    - ref_pose: dict of normalized landmarks
    - size_px: size of square overlay
    - label: optional string rendered under the overlay
    """
    h, w = frame.shape[:2]
    # prepare blank canvas for small overlay
    canvas = 255 * np.ones((size_px, size_px, 3), dtype='uint8')
    canvas[:] = bg_color

    # scale landmarks to canvas (we'll re-normalize coords to the canvas)
    # draw_skeleton expects normalized coords, so adapt by drawing on temporary canvas
    tmp = canvas.copy()
    draw_skeleton(tmp, ref_pose, color=(220,220,220), thickness=2)

    # add helpful arrows/teaching cues for shoulder flexion / abduction types:
    # try to draw an arrow from shoulder to wrist if landmarks present
    try:
        if "LEFT_SHOULDER" in ref_pose and "LEFT_WRIST" in ref_pose:
            sx, sy, _ = ref_pose["LEFT_SHOULDER"]
            wx, wy, _ = ref_pose["LEFT_WRIST"]
            p1 = (int(sx * size_px), int(sy * size_px))
            p2 = (int(wx * size_px), int(wy * size_px))
            cv2.arrowedLine(tmp, p1, p2, (100, 200, 255), 2, tipLength=0.25)
    except Exception:
        pass

    # place overlay top-left
    frame[10:10+size_px, 10:10+size_px] = tmp

    # label
    if label:
        cv2.putText(frame, label, (12, 10+size_px+18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_color, 2)

# we use numpy here (import inside file to avoid top-level import issues)
import numpy as np
