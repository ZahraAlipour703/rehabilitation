# app.py
import streamlit as st
import json, os, pandas as pd

st.set_page_config(page_title="Rehab Monitor - Doctor UI", layout="wide")

CFG_PATH = "config.json"
LOG_PATH = "logs/session_log.csv"

# Load config
with open(CFG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

st.title("Rehab Monitor — Doctor Panel")
st.header("Shoulder Flexion (stick) settings")

sf = cfg.get("shoulder_flexion", {})

col1, col2, col3 = st.columns(3)
with col1:
    side = st.selectbox("Side", ["both","right","left"], index=0 if sf.get("side","both")=="both" else (1 if sf.get("side")=="right" else 2))
    target_up = st.slider("Target angle (UP)", 120, 180, int(sf.get("target_angle_up",160)))
with col2:
    target_down = st.slider("Target angle (DOWN)", 0, 90, int(sf.get("target_angle_down",40)))
    tol = st.slider("Tolerance (deg)", 5, 30, int(sf.get("tolerance_deg",12)))
with col3:
    hold_time = st.slider("Hold time (sec)", 0.5, 5.0, float(sf.get("hold_time_sec",1.5)))
    smooth_w = st.slider("Smoothing window", 1, 20, int(sf.get("smoothing_window",5)))

# more settings
st.subheader("Form checks")
col4, col5 = st.columns(2)
with col4:
    max_elbow = st.slider("Max elbow flexion allowed (deg)", 0, 60, int(sf.get("max_elbow_flexion_deg",20)))
with col5:
    max_tilt = st.slider("Max torso tilt allowed (deg)", 0, 30, int(sf.get("max_torso_tilt_deg",12)))

if st.button("Save settings"):
    cfg["shoulder_flexion"]["side"] = side
    cfg["shoulder_flexion"]["target_angle_up"] = int(target_up)
    cfg["shoulder_flexion"]["target_angle_down"] = int(target_down)
    cfg["shoulder_flexion"]["tolerance_deg"] = int(tol)
    cfg["shoulder_flexion"]["hold_time_sec"] = float(hold_time)
    cfg["shoulder_flexion"]["smoothing_window"] = int(smooth_w)
    cfg["shoulder_flexion"]["max_elbow_flexion_deg"] = int(max_elbow)
    cfg["shoulder_flexion"]["max_torso_tilt_deg"] = int(max_tilt)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    st.success("Saved!")

st.header("Session logs")
if os.path.exists(LOG_PATH):
    try:
        df = pd.read_csv(LOG_PATH)
        st.dataframe(df.tail(200))
        st.download_button("Download CSV", data=df.to_csv(index=False), file_name="session_log.csv")
    except Exception as e:
        st.error("cannot read logs: " + str(e))
else:
    st.info("No logs yet. Run run_local.py to generate logs.")
