# run_local.py
import cv2, json, time, csv, threading, os
import mediapipe as mp
from visolus_adapter import load_pose_wrapper
from exercises.shoulder_flexion import ShoulderFlexionChecker
from utils.landmarks import landmarks_to_dict
import pyttsx3

# simple non-blocking TTS
def say_async(text):
    def _s(tt):
        try:
            engine = pyttsx3.init()
            engine.say(tt)
            engine.runAndWait()
            engine.stop()
        except Exception:
            pass
    th = threading.Thread(target=_s, args=(text,), daemon=True)
    th.start()

# load config
cfg = json.load(open("config.json", "r", encoding="utf-8"))
SH_CFG = cfg.get("shoulder_flexion", {})

# logging
os.makedirs("logs", exist_ok=True)
log_path = "logs/session_log.csv"
first_write = not os.path.exists(log_path) or os.stat(log_path).st_size == 0
logf = open(log_path, "a", newline="", encoding="utf-8")
logwriter = csv.writer(logf)
if first_write:
    logwriter.writerow(["timestamp", "exercise", "metric", "value", "note"])

# pose wrapper attempt
pose_wrapper = load_pose_wrapper()
use_visolus = pose_wrapper is not None
print("Visolus wrapper found:", use_visolus)

# Setup MediaPipe fallback
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# create checker
checker = ShoulderFlexionChecker(SH_CFG, logger=logwriter)

cap = cv2.VideoCapture(0)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

last_audio_time = 0
audio_cooldown = 1.2

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        img = frame.copy()
        t0 = time.time()

        # get landmarks: try visolus wrapper first
        landmarks = []
        if use_visolus:
            try:
                out = pose_wrapper.findPose(img, draw=False)
                if isinstance(out, tuple) and len(out) >= 2:
                    _, landmarks = out[0], out[1]
                else:
                    landmarks = out
            except Exception:
                use_visolus = False

        if not use_visolus:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)
            landmarks = res.pose_landmarks.landmark if res.pose_landmarks else []

        # update checker
        res = checker.update(landmarks, t=time.time())

        # convert landmarks to named dict for visualization
        named = {}
        try:
            if landmarks and len(landmarks) > 0:
                for i, lm in enumerate(landmarks):
                    name = mp.solutions.pose.PoseLandmark(i).name
                    named[name] = (float(lm.x), float(lm.y), float(getattr(lm, "z", 0.0)))
        except Exception:
            named = {}

        # draw per-side guides (overhead->front) and progress markers
        overlay = img.copy()
        alpha = 0.75
        # colors
        ok_c = (0,200,0)
        warn_c = (0,200,200)
        bad_c = (0,0,255)
        gray_c = (180,180,180)
        sides = ["LEFT","RIGHT"] if SH_CFG.get("side","both") == "both" else ([ "RIGHT"] if SH_CFG.get("side","both")=="right" else ["LEFT"])

        # For labeling positions for drawing skeleton lines manually
        def to_px(norm_xy):
            return (int(norm_xy[0]*W), int(norm_xy[1]*H))

        for sd in sides:
            shoulder_key = f"{sd}_SHOULDER"
            elbow_key = f"{sd}_ELBOW"
            wrist_key = f"{sd}_WRIST"
            hip_key = f"{sd}_HIP"
            if shoulder_key in named and elbow_key in named:
                sh = named[shoulder_key]; el = named[elbow_key]; wr = named.get(wrist_key); hip = named.get(hip_key)
                prog, overhead, front = checker.progress_along_path((sh[0],sh[1]), (el[0],el[1]), (W,H))
                ov = to_px(overhead); fv = to_px(front); ex = to_px((el[0],el[1])); sh_px = to_px((sh[0],sh[1])); wr_px = to_px((wr[0],wr[1])) if wr else None

                # draw ghost guide (semi-transparent arc/line)
                cv2.line(overlay, ov, fv, gray_c, 6, lineType=cv2.LINE_AA)
                # draw endpoints
                cv2.circle(overlay, ov, 8, (0,255,255), 2)
                cv2.circle(overlay, fv, 8, (0,255,255), 2)
                # progress marker
                px = int(ov[0] + (fv[0]-ov[0]) * prog)
                py = int(ov[1] + (fv[1]-ov[1]) * prog)
                cv2.circle(overlay, (px,py), 10, (0,180,0), -1)

                # draw arm segment (shoulder->elbow->wrist) colored by status
                per = res.get("per_side", {}).get(sd, {})
                status = per.get("status","-")
                reasons = per.get("reasons", [])
                # choose color
                if status in ("done","holding","down","moving"):
                    # but if there are explicit reasons, make it yellow/red
                    if len(reasons) == 0:
                        seg_color = ok_c
                    else:
                        seg_color = warn_c
                else:
                    seg_color = bad_c

                # draw segments thicker
                cv2.line(overlay, sh_px, ex, seg_color, 6, lineType=cv2.LINE_AA)
                if wr_px:
                    cv2.line(overlay, ex, wr_px, seg_color, 5, lineType=cv2.LINE_AA)
                # small dot at elbow
                cv2.circle(overlay, ex, 6, (0,0,0), -1)
                # put side label
                cv2.putText(overlay, sd, (sh_px[0]-10, sh_px[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

                # draw textual reasons near elbow if any
                if reasons:
                    ry = ex[1] + 18
                    for r in reasons:
                        cv2.putText(overlay, r, (ex[0]+8, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                        ry += 18

        # blend overlay
        cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

        # HUD: angle/status/reps
        hud_x = 12; hud_y = 28
        cv2.rectangle(img, (0,0), (420,120), (10,10,10), -1)
        cv2.putText(img, f"Shoulder Flexion (stick) - Sides: {SH_CFG.get('side','both')}", (hud_x, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        hud_y += 28

        # show per-side summary
        per = res.get("per_side", {})
        colx = 14
        for sd in (["LEFT","RIGHT"] if SH_CFG.get("side","both")=="both" else (["RIGHT"] if SH_CFG.get("side","both")=="right" else ["LEFT"])):
            p = per.get(sd, {})
            st = p.get("status", "-")
            ang = p.get("angle", None)
            ang_text = f"{int(ang)}°" if ang is not None else "-"
            reps = p.get("reps", 0)
            txt = f"{sd}: {st}  angle={ang_text}  reps={reps}"
            color = (0,200,0) if st in ("done","holding","down","moving") and len(p.get("reasons",[]))==0 else (0,165,255) if len(p.get("reasons",[]))>0 else (0,0,255)
            cv2.putText(img, txt, (colx, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            hud_y += 24

        # torso tilt display
        tt = res.get("torso_tilt_deg", None)
        if tt is not None:
            cv2.putText(img, f"Torso tilt: {tt:.1f}° (max {SH_CFG.get('max_torso_tilt_deg'):.0f}°)", (14, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            hud_y += 24

        # audio feedback rules (limited)
        # if any side has an error reason, speak once per cooldown
        now = time.time()
        reasons_all = []
        for sd, p in per.items():
            reasons_all += p.get("reasons", [])
        if reasons_all and now - last_audio_time > audio_cooldown:
            # short voice prompt describing first reason
            say_async(reasons_all[0])
            last_audio_time = now
        # encouragement when a rep is done
        for sd, p in per.items():
            if p.get("status") == "done":
                if now - last_audio_time > audio_cooldown:
                    say_async(f"{sd} arm: Good job, rep counted")
                    last_audio_time = now

        # Draw mediapipe skeleton (light) for extra clarity
        try:
            res_draw = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if res_draw.pose_landmarks:
                mp_drawing.draw_landmarks(img, res_draw.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        except Exception:
            pass

        cv2.imshow("Rehab - Shoulder Flexion with Stick (q to quit)", img)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break

finally:
    cap.release()
    logf.close()
    cv2.destroyAllWindows()


# rehab-monitor/
# │
# ├── external/
# │   └── Visolus/                # git submodule or copy of Visolus repo
# │
# ├── app.py                      # Streamlit / frontend
# ├── run_local.py                # quick-run script (cv2 window)
# ├── visolus_adapter.py          # adapter to import Visolus pose / dtw safely
# │
# ├── exercises/
# │   ├── __init__.py
# │   ├── base.py                 # BaseExerciseChecker class (common logic)
# │   ├── shoulder_flexion.py     # COMPLETE exercise implementation (provided)
# │   └── <others>_checker.py     # one file per exercise (templates provided)
# │
# ├── config.json                 # doctor-editable thresholds + references
# ├── utils/
# │   ├── angles.py               # stable angle functions
# │   ├── smoothing.py            # smoothing helpers
# │   └── landmarks.py            # convert different landmark formats to common dict
# │
# ├── logs/
# │   └── session_log.csv
# ├── recordings/                 # optional saved reference sequences (npy/json)
# └── requirements.txt
