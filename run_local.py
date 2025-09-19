# # run_local.py
# import cv2,time, csv, threading, os, argparse
# import json5 as json
# import mediapipe as mp
# from visolus_adapter import load_pose_wrapper
# from exercises.shoulder_flexion import ShoulderFlexionChecker
# from exercises.arm_raise_and_carry import ArmRaiseAndCarryChecker
# from utils.landmarks import landmarks_to_dict
# from utils.angles import angle_between_3d as angle_between_points
# import pyttsx3
           
# # simple non-blocking TTS
# def say_async(text):
#     def _s(tt):
#         try:
#             engine = pyttsx3.init()
#             engine.say(tt)
#             engine.runAndWait()
#             engine.stop()
#         except Exception:
#             pass
#     th = threading.Thread(target=_s, args=(text,), daemon=True)
#     th.start()
# EXERCISE_CHECKERS = {
#     "shoulder_flexion": ShoulderFlexionChecker,
#     "farmers_carry": ArmRaiseAndCarryChecker,
# }
   
# # CLI: choose exercise
# parser = argparse.ArgumentParser()
# parser.add_argument("--exercise", type=str, default="farmers_carry",
#                     choices=["shoulder_flexion", "farmers_carry"],
#                     help="Which exercise to run")
# args = parser.parse_args()

# # load config
# cfg = json.load(open("config.json", "r", encoding="utf-8"))
# SH_CFG = cfg.get("shoulder_flexion", {})
# EX_CFG = cfg.get(args.exercise, {})

# # logging
# os.makedirs("logs", exist_ok=True)
# log_path = f"logs/{args.exercise}_session.csv"
# first_write = not os.path.exists(log_path) or os.stat(log_path).st_size == 0
# logf = open(log_path, "a", newline="", encoding="utf-8")
# logwriter = csv.writer(logf)
# if first_write:
#     logwriter.writerow(["timestamp", "exercise", "metric", "value", "note"])
    
# # pose wrapper attempt
# pose_wrapper = load_pose_wrapper()
# use_visolus = pose_wrapper is not None
# print("Visolus wrapper found:", use_visolus)

# # Setup MediaPipe fallback
# mp_pose = mp.solutions.pose
# mp_drawing = mp.solutions.drawing_utils
# pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# # Create checker object
# if args.exercise == "shoulder_flexion":
#     checker = ShoulderFlexionChecker(EX_CFG, logger=logwriter)
# elif args.exercise == "farmers_carry":
#     checker = ArmRaiseAndCarryChecker(EX_CFG, logger=logwriter)
# else:
#     raise ValueError("Unsupported exercise")

# cap = cv2.VideoCapture(0)
# W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
# H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

# last_audio_time = 0
# audio_cooldown = 1.2

# try:
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         img = frame.copy()
#         t0 = time.time()

#         # get landmarks: try visolus wrapper first
#         landmarks = []
#         if use_visolus:
#             try:
#                 out = pose_wrapper.findPose(img, draw=False)
#                 if isinstance(out, tuple) and len(out) >= 2:
#                     _, landmarks = out[0], out[1]
#                 else:
#                     landmarks = out
#             except Exception:
#                 use_visolus = False

#         if not use_visolus:
#             rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#             res = pose.process(rgb)
#             landmarks = res.pose_landmarks.landmark if res.pose_landmarks else []

#         # update checker
#         res = checker.update(landmarks, t=time.time())

#         # convert landmarks to named dict for visualization
#         named = {}
#         try:
#             if landmarks and len(landmarks) > 0:
#                 for i, lm in enumerate(landmarks):
#                     name = mp.solutions.pose.PoseLandmark(i).name
#                     named[name] = (float(lm.x), float(lm.y), float(getattr(lm, "z", 0.0)))
#         except Exception:
#             named = {}
#                 # ---------------------------
#         # Audio feedback
#         now = t0
#         per = res.get("per_side", {})
#         reasons_all = []
#         for sd, p in per.items():
#             reasons_all += p.get("reasons", [])

#         if reasons_all and now - last_audio_time > audio_cooldown:
#             say_async(reasons_all[0])
#             last_audio_time = now

#         for sd, p in per.items():
#             if p.get("status") == "done":
#                 if now - last_audio_time > audio_cooldown:
#                     say_async(f"{sd} arm: Good job, rep counted")
#                     last_audio_time = now
#         # draw per-side guides (overhead->front) and progress markers
#         overlay = img.copy()
#         alpha = 0.75
#         # colors
#         ok_c = (0,200,0)
#         warn_c = (0,200,200)
#         bad_c = (0,0,255)
#         gray_c = (180,180,180)
#         sides = ["LEFT","RIGHT"] if SH_CFG.get("side","both") == "both" else ([ "RIGHT"] if SH_CFG.get("side","both")=="right" else ["LEFT"])

#         # For labeling positions for drawing skeleton lines manually
#         def to_px(norm_xy):
#             return (int(norm_xy[0]*W), int(norm_xy[1]*H))

#         for sd in sides:
#             shoulder_key = f"{sd}_SHOULDER"
#             elbow_key = f"{sd}_ELBOW"
#             wrist_key = f"{sd}_WRIST"
#             hip_key = f"{sd}_HIP"
#             if shoulder_key in named and elbow_key in named:
#                 sh = named[shoulder_key]; el = named[elbow_key]; wr = named.get(wrist_key); hip = named.get(hip_key)
#                 prog, overhead, front = checker.progress_along_path((sh[0],sh[1]), (el[0],el[1]), (W,H))
#                 ov = to_px(overhead); fv = to_px(front); ex = to_px((el[0],el[1])); sh_px = to_px((sh[0],sh[1])); wr_px = to_px((wr[0],wr[1])) if wr else None

#                 # draw ghost guide (semi-transparent arc/line)
#                 cv2.line(overlay, ov, fv, gray_c, 6, lineType=cv2.LINE_AA)
#                 # draw endpoints
#                 cv2.circle(overlay, ov, 8, (0,255,255), 2)
#                 cv2.circle(overlay, fv, 8, (0,255,255), 2)
#                 # progress marker
#                 px = int(ov[0] + (fv[0]-ov[0]) * prog)
#                 py = int(ov[1] + (fv[1]-ov[1]) * prog)
#                 cv2.circle(overlay, (px,py), 10, (0,180,0), -1)

#                 # draw arm segment (shoulder->elbow->wrist) colored by status
#                 per = res.get("per_side", {}).get(sd, {})
#                 status = per.get("status","-")
#                 reasons = per.get("reasons", [])
#                 # choose color
#                 if status in ("done","holding","down","moving"):
#                     # but if there are explicit reasons, make it yellow/red
#                     if len(reasons) == 0:
#                         seg_color = ok_c
#                     else:
#                         seg_color = warn_c
#                 else:
#                     seg_color = bad_c

#                 # draw segments thicker
#                 cv2.line(overlay, sh_px, ex, seg_color, 6, lineType=cv2.LINE_AA)
#                 if wr_px:
#                     cv2.line(overlay, ex, wr_px, seg_color, 5, lineType=cv2.LINE_AA)
#                 # small dot at elbow
#                 cv2.circle(overlay, ex, 6, (0,0,0), -1)
#                 # put side label
#                 cv2.putText(overlay, sd, (sh_px[0]-10, sh_px[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

#                 # draw textual reasons near elbow if any
#                 if reasons:
#                     ry = ex[1] + 18
#                     for r in reasons:
#                         cv2.putText(overlay, r, (ex[0]+8, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
#                         ry += 18

#         # blend overlay
#         cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

#         # HUD: angle/status/reps
#         hud_x = 12; hud_y = 28
#         cv2.rectangle(img, (0,0), (420,120), (10,10,10), -1)
#         cv2.putText(img, f"Shoulder Flexion (stick) - Sides: {SH_CFG.get('side','both')}", (hud_x, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
#         hud_y += 28

#         # show per-side summary
#         per = res.get("per_side", {})
#         colx = 14
#         for sd in (["LEFT","RIGHT"] if SH_CFG.get("side","both")=="both" else (["RIGHT"] if SH_CFG.get("side","both")=="right" else ["LEFT"])):
#             p = per.get(sd, {})
#             st = p.get("status", "-")
#             ang = p.get("angle", None)
#             ang_text = f"{int(ang)}°" if ang is not None else "-"
#             reps = p.get("reps", 0)
#             txt = f"{sd}: {st}  angle={ang_text}  reps={reps}"
#             color = (0,200,0) if st in ("done","holding","down","moving") and len(p.get("reasons",[]))==0 else (0,165,255) if len(p.get("reasons",[]))>0 else (0,0,255)
#             cv2.putText(img, txt, (colx, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
#             hud_y += 24

#         # torso tilt display
#         tt = res.get("torso_tilt_deg", None)
#         if tt is not None:
#             cv2.putText(img, f"Torso tilt: {tt:.1f}° (max {SH_CFG.get('max_torso_tilt_deg'):.0f}°)", (14, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
#             hud_y += 24

#         # audio feedback rules (limited)
#         # if any side has an error reason, speak once per cooldown
#         now = time.time()
#         reasons_all = []
#         for sd, p in per.items():
#             reasons_all += p.get("reasons", [])
#         if reasons_all and now - last_audio_time > audio_cooldown:
#             # short voice prompt describing first reason
#             say_async(reasons_all[0])
#             last_audio_time = now
#         # encouragement when a rep is done
#         for sd, p in per.items():
#             if p.get("status") == "done":
#                 if now - last_audio_time > audio_cooldown:
#                     say_async(f"{sd} arm: Good job, rep counted")
#                     last_audio_time = now

#         # Draw mediapipe skeleton (light) for extra clarity
#         try:
#             res_draw = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#             if res_draw.pose_landmarks:
#                 mp_drawing.draw_landmarks(img, res_draw.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
#         except Exception:
#             pass

#         cv2.imshow(f"Rehab - {args.exercise}", img)
#         k = cv2.waitKey(1) & 0xFF
#         if k == ord('q'):
#             break

# finally:
#     cap.release()
#     logf.close()
#     cv2.destroyAllWindows()


# # rehab-monitor/
# # │
# # ├── external/
# # │   └── Visolus/                # git submodule or copy of Visolus repo
# # │
# # ├── app.py                      # Streamlit / frontend
# # ├── run_local.py                # quick-run script (cv2 window)
# # ├── visolus_adapter.py          # adapter to import Visolus pose / dtw safely
# # │
# # ├── exercises/
# # │   ├── __init__.py
# # │   ├── base.py                 # BaseExerciseChecker class (common logic)
# # │   ├── shoulder_flexion.py     # COMPLETE exercise implementation (provided)
# # │   └── <others>_checker.py     # one file per exercise (templates provided)
# # │
# # ├── config.json                 # doctor-editable thresholds + references
# # ├── utils/
# # │   ├── angles.py               # stable angle functions
# # │   ├── smoothing.py            # smoothing helpers
# # │   └── landmarks.py            # convert different landmark formats to common dict
# # │
# # ├── logs/
# # │   └── session_log.csv
# # ├── recordings/                 # optional saved reference sequences (npy/json)
# # └── requirements.txt
# # run_local.py (updated, friendlier audio/feedback logic)
# # run_local.py (Stage 1: Shoulder Flexion only)
# run_local.py (updated to support shoulder_abduction + friendlier behavior)
# import cv2, time, csv, threading, os, argparse
# import json5 as json
# import mediapipe as mp
# from visolus_adapter import load_pose_wrapper
# from exercises.shoulder_flexion import ShoulderFlexionChecker
# from exercises.arm_raise_and_carry import ArmRaiseAndCarryChecker
# from exercises.shoulder_Abduction import ShoulderAbductionChecker
# from utils.landmarks import landmarks_to_dict
# from utils.angles import angle_between_3d as angle_between_points
# import pyttsx3

# # simple non-blocking TTS
# def say_async(text):
#     def _s(tt):
#         try:
#             engine = pyttsx3.init()
#             engine.say(tt)
#             engine.runAndWait()
#             engine.stop()
#         except Exception:
#             pass
#     th = threading.Thread(target=_s, args=(text,), daemon=True)
#     th.start()

# EXERCISE_CHECKERS = {
#     "shoulder_flexion": ShoulderFlexionChecker,
#     "farmers_carry": ArmRaiseAndCarryChecker,      # CLI name kept for backward compatibility
#     "shoulder_abduction": ShoulderAbductionChecker,
# }

# # CLI: choose exercise
# parser = argparse.ArgumentParser()
# parser.add_argument("--exercise", type=str, default="farmers_carry",
#                     choices=list(EXERCISE_CHECKERS.keys()),
#                     help="Which exercise to run")
# args = parser.parse_args()

# # --- config key mapping (CLI name -> config.json key) ---
# # use this if your config.json uses a different root key name for some exercises
# CONFIG_KEY_MAP = {
#     "farmers_carry": "arm_raise_and_carry",   # your config used arm_raise_and_carry earlier
#     "shoulder_flexion": "shoulder_flexion",
#     "shoulder_abduction": "shoulder_abduction",
# }

# # load config
# cfg = json.load(open("config.json", "r", encoding="utf-8"))
# SH_CFG = cfg.get("shoulder_flexion", {})  # keep as fallback/legacy
# cfg_key = CONFIG_KEY_MAP.get(args.exercise, args.exercise)
# EX_CFG = cfg.get(cfg_key, {})

# # logging
# os.makedirs("logs", exist_ok=True)
# log_path = f"logs/{args.exercise}_session.csv"
# first_write = not os.path.exists(log_path) or os.stat(log_path).st_size == 0
# logf = open(log_path, "a", newline="", encoding="utf-8")
# logwriter = csv.writer(logf)
# if first_write:
#     logwriter.writerow(["timestamp", "exercise", "metric", "value", "note"])

# # pose wrapper attempt
# pose_wrapper = load_pose_wrapper()
# use_visolus = pose_wrapper is not None
# print("Visolus wrapper found:", use_visolus)

# # Setup MediaPipe fallback
# mp_pose = mp.solutions.pose
# mp_drawing = mp.solutions.drawing_utils
# pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# # Create checker object dynamically
# checker_cls = EXERCISE_CHECKERS.get(args.exercise)
# if checker_cls is None:
#     raise ValueError("Unsupported exercise")
# checker = checker_cls(EX_CFG, logger=logwriter)

# cap = cv2.VideoCapture(0)
# W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
# H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

# # audio / feedback control state
# last_audio_time = 0.0
# audio_cooldown = 1.5  # seconds between voice prompts
# last_spoken_reasons = set()
# last_reps = {"LEFT": 0, "RIGHT": 0}

# # friendly human titles for HUD
# EX_TITLES = {
#     "shoulder_flexion": "Shoulder Flexion (stick)",
#     "farmers_carry": "Arm Raise + Carry",
#     "shoulder_abduction": "Shoulder Abduction (lateral)",
# }

# try:
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         img = frame.copy()
#         t0 = time.time()

#         # get landmarks: try visolus wrapper first
#         landmarks = []
#         if use_visolus:
#             try:
#                 out = pose_wrapper.findPose(img, draw=False)
#                 if isinstance(out, tuple) and len(out) >= 2:
#                     _, landmarks = out[0], out[1]
#                 else:
#                     landmarks = out
#             except Exception:
#                 use_visolus = False

#         if not use_visolus:
#             rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#             res = pose.process(rgb)
#             landmarks = res.pose_landmarks.landmark if res.pose_landmarks else []

#         # update checker
#         res = checker.update(landmarks, t=time.time())

#         # convert landmarks to named dict for visualization
#         named = {}
#         try:
#             if landmarks and len(landmarks) > 0:
#                 for i, lm in enumerate(landmarks):
#                     name = mp.solutions.pose.PoseLandmark(i).name
#                     named[name] = (float(lm.x), float(lm.y), float(getattr(lm, "z", 0.0)))
#         except Exception:
#             named = {}

#         # ---------------------------
#         # Audio feedback (friendlier): only speak new reasons and on rep increments
#         now = t0
#         per = res.get("per_side", {})

#         # gather unique reasons currently present
#         current_reasons = set()
#         for sd, p in per.items():
#             for r in p.get("reasons", []):
#                 current_reasons.add(r.strip())

#         # speak only about newly appeared reasons (respect cooldown)
#         new_reasons = [r for r in current_reasons if r not in last_spoken_reasons]
#         if new_reasons and now - last_audio_time > audio_cooldown:
#             say_async(new_reasons[0])
#             last_audio_time = now
#             last_spoken_reasons.update(new_reasons)

#         # encouragement when a rep is done: speak once per rep increment
#         for sd, p in per.items():
#             reps = p.get("reps", 0)
#             if reps and reps > last_reps.get(sd, 0) and now - last_audio_time > audio_cooldown:
#                 say_async(f"{sd} arm: Good job, rep counted")
#                 last_audio_time = now
#                 last_reps[sd] = reps

#         # decay spoken reasons after some time so we can re-suggest later
#         if now - last_audio_time > 6.0:
#             last_spoken_reasons.clear()

#         # draw per-side guides (overhead->front/side) and progress markers
#         overlay = img.copy()
#         alpha = 0.75
#         # colors
#         ok_c = (0,200,0)
#         warn_c = (0,200,200)
#         bad_c = (0,0,255)
#         gray_c = (180,180,180)

#         # sides from exercise config (fallback to shoulder config)
#         sides_cfg = EX_CFG.get("side") if EX_CFG.get("side") is not None else SH_CFG.get("side", "both")
#         sides = ["LEFT","RIGHT"] if sides_cfg == "both" else (["RIGHT"] if sides_cfg == "right" else ["LEFT"])

#         def to_px(norm_xy):
#             return (int(norm_xy[0]*W), int(norm_xy[1]*H))

#         for sd in sides:
#             shoulder_key = f"{sd}_SHOULDER"
#             elbow_key = f"{sd}_ELBOW"
#             wrist_key = f"{sd}_WRIST"
#             hip_key = f"{sd}_HIP"
#             if shoulder_key in named and elbow_key in named:
#                 sh = named[shoulder_key]; el = named[elbow_key]; wr = named.get(wrist_key); hip = named.get(hip_key)

#                 # support progress_along_path functions with different signatures/returns
#                 try:
#                     # try with side parameter (some checkers accept it)
#                     path_res = checker.progress_along_path((sh[0],sh[1]), (el[0],el[1]), (W,H), side=sd)
#                 except TypeError:
#                     try:
#                         path_res = checker.progress_along_path((sh[0],sh[1]), (el[0],el[1]), (W,H))
#                     except Exception:
#                         path_res = (0.0, (sh[0],sh[1]), (el[0],el[1]))
#                 except Exception:
#                     path_res = (0.0, (sh[0],sh[1]), (el[0],el[1]))

#                 # unpack robustly
#                 if isinstance(path_res, (tuple, list)) and len(path_res) >= 3:
#                     prog = float(path_res[0])
#                     overhead = path_res[1]
#                     front = path_res[2]
#                 else:
#                     prog = 0.0
#                     overhead = (sh[0], sh[1])
#                     front = (el[0], el[1])

#                 ov = to_px(overhead); fv = to_px(front); ex = to_px((el[0],el[1])); sh_px = to_px((sh[0],sh[1])); wr_px = to_px((wr[0],wr[1])) if wr else None

#                 # ghost guide
#                 cv2.line(overlay, ov, fv, gray_c, 6, lineType=cv2.LINE_AA)
#                 cv2.circle(overlay, ov, 8, (0,255,255), 2)
#                 cv2.circle(overlay, fv, 8, (0,255,255), 2)
#                 px = int(ov[0] + (fv[0]-ov[0]) * prog)
#                 py = int(ov[1] + (fv[1]-ov[1]) * prog)
#                 cv2.circle(overlay, (px,py), 10, (0,180,0), -1)

#                 # draw arm segment colored by status
#                 per_side = res.get("per_side", {}).get(sd, {})
#                 status = per_side.get("status","-")
#                 reasons = per_side.get("reasons", [])
#                 if status in ("done","holding","down","moving"):
#                     seg_color = ok_c if len(reasons) == 0 else warn_c
#                 else:
#                     seg_color = bad_c

#                 cv2.line(overlay, sh_px, ex, seg_color, 6, lineType=cv2.LINE_AA)
#                 if wr_px:
#                     cv2.line(overlay, ex, wr_px, seg_color, 5, lineType=cv2.LINE_AA)
#                 cv2.circle(overlay, ex, 6, (0,0,0), -1)
#                 cv2.putText(overlay, sd, (sh_px[0]-10, sh_px[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

#                 if reasons:
#                     ry = ex[1] + 18
#                     for r in reasons:
#                         cv2.putText(overlay, r, (ex[0]+8, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
#                         ry += 18

#         cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

#         # HUD
#         hud_x = 12; hud_y = 28
#         cv2.rectangle(img, (0,0), (520,140), (10,10,10), -1)
#         title = EX_TITLES.get(args.exercise, args.exercise)
#         cv2.putText(img, f"{title}  (sides: {EX_CFG.get('side', SH_CFG.get('side','both'))})", (hud_x, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
#         hud_y += 28

#         per = res.get("per_side", {})
#         colx = 14
#         sides_to_show = ["LEFT","RIGHT"] if EX_CFG.get("side", SH_CFG.get("side","both")) == "both" else (["RIGHT"] if EX_CFG.get("side", SH_CFG.get("side","both")) == "right" else ["LEFT"])
#         for sd in sides_to_show:
#             p = per.get(sd, {})
#             st = p.get("status", "-")
#             ang = p.get("angle", None)
#             ang_text = f"{int(ang)}°" if ang is not None else "-"
#             reps = p.get("reps", 0)
#             txt = f"{sd}: {st}  angle={ang_text}  reps={reps}"
#             color = (0,200,0) if st in ("done","holding","down","moving") and len(p.get("reasons",[]))==0 else (0,165,255) if len(p.get("reasons",[]))>0 else (0,0,255)
#             cv2.putText(img, txt, (colx, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
#             hud_y += 24

#         tt = res.get("torso_tilt_deg", None)
#         if tt is not None:
#             max_tilt = EX_CFG.get('max_torso_tilt_deg', SH_CFG.get('max_torso_tilt_deg', 12))
#             cv2.putText(img, f"Torso tilt: {tt:.1f}° (max {max_tilt:.0f}°)", (14, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
#             hud_y += 24

#         # Draw mediapipe skeleton lightly
#         try:
#             res_draw = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#             if res_draw.pose_landmarks:
#                 mp_drawing.draw_landmarks(img, res_draw.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
#         except Exception:
#             pass

#         cv2.imshow(f"Rehab - {args.exercise}", img)
#         k = cv2.waitKey(1) & 0xFF
#         if k == ord('q'):
#             break

# finally:
#     cap.release()
#     logf.close()
#     cv2.destroyAllWindows()
#----------------------------------------------------------------------------------------------------------------------------------------------------
# run_local.py
import cv2, time, csv, threading, os, argparse
import json5 as json
import mediapipe as mp
from visolus_adapter import load_pose_wrapper

from exercises.shoulder_flexion import ShoulderFlexionChecker
from exercises.arm_raise_and_carry import ArmRaiseAndCarryChecker
# make sure you have an exercise file for shoulder_abduction with class ShoulderAbductionChecker
try:
    from exercises.shoulder_Abduction import ShoulderAbductionChecker
except Exception:
    # if not present, ignore — only available when file exists
    ShoulderAbductionChecker = None

from utils.landmarks import landmarks_to_dict
from utils.angles import angle_between_3d as angle_between_points
from utils.reference_motion import REFERENCE_FUNCTIONS
from utils.draw import draw_skeleton, overlay_reference_corner

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

EXERCISE_CHECKERS = {
    "shoulder_flexion": ShoulderFlexionChecker,
    "farmers_carry": ArmRaiseAndCarryChecker,      # CLI legacy name
    "shoulder_abduction": ShoulderAbductionChecker,
}

# CLI: choose exercise
parser = argparse.ArgumentParser()
parser.add_argument("--exercise", type=str, default="farmers_carry",
                    choices=[k for k,v in EXERCISE_CHECKERS.items() if v is not None],
                    help="Which exercise to run")
args = parser.parse_args()

# map CLI name -> config key if needed
CONFIG_KEY_MAP = {
    "farmers_carry": "arm_raise_and_carry",
    "shoulder_flexion": "shoulder_flexion",
    "shoulder_abduction": "shoulder_abduction",
}
cfg = json.load(open("config.json", "r", encoding="utf-8"))
SH_CFG = cfg.get("shoulder_flexion", {})
cfg_key = CONFIG_KEY_MAP.get(args.exercise, args.exercise)
EX_CFG = cfg.get(cfg_key, {})

# logging
os.makedirs("logs", exist_ok=True)
log_path = f"logs/{args.exercise}_session.csv"
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

# Create checker object dynamically
checker_cls = EXERCISE_CHECKERS.get(args.exercise)
if checker_cls is None:
    raise ValueError("Unsupported exercise")
checker = checker_cls(EX_CFG, logger=logwriter)

cap = cv2.VideoCapture(0)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

# prepare reference poses (choose a matching reference function)
# NOTE: reference mapping keys may differ from your EX_CFG keys, adjust if needed
ref_key = args.exercise
# try few fallbacks:
if ref_key not in REFERENCE_FUNCTIONS:
    if args.exercise == "farmers_carry":
        ref_key = "farmers_carry"
    elif args.exercise == "shoulder_abduction":
        ref_key = "arm_raise_and_carry"
ref_gen = REFERENCE_FUNCTIONS.get(ref_key)
if ref_gen:
    ref_poses = ref_gen(num_frames=140)
else:
    ref_poses = []
ref_index = 0

# audio / feedback control
last_audio_time = 0.0
audio_cooldown = 1.5
last_spoken_reasons = set()
last_reps = {"LEFT": 0, "RIGHT": 0}

EX_TITLES = {
    "shoulder_flexion": "Shoulder Flexion (stick)",
    "farmers_carry": "Arm Raise + Carry",
    "shoulder_abduction": "Shoulder Abduction (lateral)",
}

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        img = frame.copy()
        t0 = time.time()

        # get landmarks
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

        # --- Audio feedback (friendlier)
        now = t0
        per = res.get("per_side", {})
        current_reasons = set()
        for sd, p in per.items():
            for r in p.get("reasons", []):
                current_reasons.add(r.strip())
        new_reasons = [r for r in current_reasons if r not in last_spoken_reasons]
        if new_reasons and now - last_audio_time > audio_cooldown:
            say_async(new_reasons[0])
            last_audio_time = now
            last_spoken_reasons.update(new_reasons)
        # rep encouragement
        for sd, p in per.items():
            reps = p.get("reps", 0)
            if reps and reps > last_reps.get(sd, 0) and now - last_audio_time > audio_cooldown:
                say_async(f"{sd} arm: Good job, rep counted")
                last_audio_time = now
                last_reps[sd] = reps
        if now - last_audio_time > 6.0:
            last_spoken_reasons.clear()

        # draw per-side guides & progress
        overlay = img.copy()
        alpha = 0.75
        ok_c = (0,200,0); warn_c = (0,200,200); bad_c = (0,0,255); gray_c = (180,180,180)

        sides_cfg = EX_CFG.get("side") if EX_CFG.get("side") is not None else SH_CFG.get("side", "both")
        sides = ["LEFT","RIGHT"] if sides_cfg == "both" else (["RIGHT"] if sides_cfg == "right" else ["LEFT"])

        def to_px(norm_xy):
            return (int(norm_xy[0]*W), int(norm_xy[1]*H))

        for sd in sides:
            shoulder_key = f"{sd}_SHOULDER"
            elbow_key = f"{sd}_ELBOW"
            wrist_key = f"{sd}_WRIST"
            hip_key = f"{sd}_HIP"
            if shoulder_key in named and elbow_key in named:
                sh = named[shoulder_key]; el = named[elbow_key]; wr = named.get(wrist_key); hip = named.get(hip_key)
                # robustly call progress_along_path
                try:
                    path_res = checker.progress_along_path((sh[0],sh[1]), (el[0],el[1]), (W,H), side=sd)
                except TypeError:
                    try:
                        path_res = checker.progress_along_path((sh[0],sh[1]), (el[0],el[1]), (W,H))
                    except Exception:
                        path_res = (0.0, (sh[0],sh[1]), (el[0],el[1]))
                except Exception:
                    path_res = (0.0, (sh[0],sh[1]), (el[0],el[1]))

                if isinstance(path_res, (tuple, list)) and len(path_res) >= 3:
                    prog = float(path_res[0]); overhead = path_res[1]; front = path_res[2]
                else:
                    prog = 0.0; overhead = (sh[0], sh[1]); front = (el[0], el[1])

                ov = to_px(overhead); fv = to_px(front); ex = to_px((el[0],el[1])); sh_px = to_px((sh[0],sh[1])); wr_px = to_px((wr[0],wr[1])) if wr else None

                # ghost guide
                cv2.line(overlay, ov, fv, gray_c, 6, lineType=cv2.LINE_AA)
                cv2.circle(overlay, ov, 8, (0,255,255), 2); cv2.circle(overlay, fv, 8, (0,255,255), 2)
                px = int(ov[0] + (fv[0]-ov[0]) * prog); py = int(ov[1] + (fv[1]-ov[1]) * prog)
                cv2.circle(overlay, (px,py), 10, (0,180,0), -1)

                per_side = res.get("per_side", {}).get(sd, {})
                status = per_side.get("status","-")
                reasons = per_side.get("reasons", [])
                seg_color = ok_c if status in ("done","holding","down","moving") and len(reasons)==0 else (warn_c if len(reasons)>0 else bad_c)

                cv2.line(overlay, sh_px, ex, seg_color, 6, lineType=cv2.LINE_AA)
                if wr_px:
                    cv2.line(overlay, ex, wr_px, seg_color, 5, lineType=cv2.LINE_AA)
                cv2.circle(overlay, ex, 6, (0,0,0), -1)
                cv2.putText(overlay, sd, (sh_px[0]-10, sh_px[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

                if reasons:
                    ry = ex[1] + 18
                    for r in reasons:
                        cv2.putText(overlay, r, (ex[0]+8, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                        ry += 18

        cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

        # HUD
        hud_x = 12; hud_y = 28
        cv2.rectangle(img, (0,0), (520,160), (10,10,10), -1)
        title = EX_TITLES.get(args.exercise, args.exercise)
        cv2.putText(img, f"{title}  (sides: {EX_CFG.get('side', SH_CFG.get('side','both'))})", (hud_x, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        hud_y += 32

        per = res.get("per_side", {})
        colx = 14
        sides_to_show = ["LEFT","RIGHT"] if EX_CFG.get("side", SH_CFG.get("side","both")) == "both" else (["RIGHT"] if EX_CFG.get("side", SH_CFG.get("side","both")) == "right" else ["LEFT"])
        for sd in sides_to_show:
            p = per.get(sd, {})
            st = p.get("status", "-")
            ang = p.get("angle", None)
            ang_text = f"{int(ang)}°" if ang is not None else "-"
            reps = p.get("reps", 0)
            txt = f"{sd}: {st}  angle={ang_text}  reps={reps}"
            color = (0,200,0) if st in ("done","holding","down","moving") and len(p.get("reasons",[]))==0 else (0,165,255) if len(p.get("reasons",[]))>0 else (0,0,255)
            cv2.putText(img, txt, (colx, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            hud_y += 24

        tt = res.get("torso_tilt_deg", None)
        if tt is not None:
            max_tilt = EX_CFG.get('max_torso_tilt_deg', SH_CFG.get('max_torso_tilt_deg', 12))
            cv2.putText(img, f"Torso tilt: {tt:.1f}° (max {max_tilt:.0f}°)", (14, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            hud_y += 24

        # Draw Mediapipe skeleton lightly (patient)
        try:
            res_draw = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if res_draw.pose_landmarks:
                mp_drawing.draw_landmarks(img, res_draw.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        except Exception:
            pass

        # --- Reference coach overlay (top-left) ---
        if ref_poses:
            ref_pose = ref_poses[ref_index % len(ref_poses)]
            ref_index += 1
            # draw small overlay and label with quick cue text
            overlay_reference_corner(img, ref_pose, size_px=220, label="Follow guide", label_color=(220,220,220))

        cv2.imshow(f"Rehab - {args.exercise}", img)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break

finally:
    cap.release()
    logf.close()
    cv2.destroyAllWindows()
