from datetime import datetime, time
from urllib.parse import urlencode
import streamlit as st

st.set_page_config(page_title="Multi-Platform Publisher", layout="centered")

REDIRECT_URI = "https://multi-platform-publisher.streamlit.app"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
META_SCOPES = ["public_profile"]


def _get_persisted_connected() -> set[str]:
    raw = st.query_params.get("connected", "")
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _save_persisted_connected(connected_set: set[str]):
    # 'code', 'state', 'error' hata kar sirf 'connected' rakhein
    st.query_params.clear()
    if connected_set:
        st.query_params["connected"] = ",".join(sorted(connected_set))


# Session state initialize + URL se persisted connections restore
persisted = _get_persisted_connected()

DEFAULTS = {
    "yt_connected": "youtube" in persisted,
    "fb_connected": "facebook" in persisted,
    "ig_connected": "instagram" in persisted,
    "x_connected": "x" in persisted,
    "yt_token": None,
    "fb_token": None,
    "ig_token": None,
    "yt_error": None,
    "fb_error": None,
    "ig_error": None,
    "cb_yt": "youtube" in persisted,
    "cb_fb": "facebook" in persisted,
    "cb_ig": "instagram" in persisted,
    "cb_x": "x" in persisted,
    "processed_codes": set(),
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = set() if isinstance(value, set) else value
    elif key.endswith("_connected") and value is True:
        st.session_state[key] = True
    elif key.startswith("cb_") and value is True:
        st.session_state[key] = True


def get_youtube_auth_url() -> str:
    client_id = st.secrets.get("YOUTUBE_CLIENT_ID", "")
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": YOUTUBE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": "youtube",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def get_meta_auth_url(platform_state: str = "facebook") -> str:
    app_id = st.secrets.get("META_APP_ID", "")
    params = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": ",".join(META_SCOPES),
        "state": platform_state,
    }
    return "https://www.facebook.com/v21.0/dialog/oauth?" + urlencode(params)


def exchange_youtube_code(code: str):
    if not code:
        raise ValueError("Missing YouTube auth code.")
    return {"code": code, "status": "connected"}


def exchange_meta_code(code: str):
    if not code:
        raise ValueError("Missing Meta auth code.")
    return {"code": code, "status": "connected"}


def _current_connected_set() -> set[str]:
    active = set()
    if st.session_state.get("yt_connected"):
        active.add("youtube")
    if st.session_state.get("fb_connected"):
        active.add("facebook")
    if st.session_state.get("ig_connected"):
        active.add("instagram")
    if st.session_state.get("x_connected"):
        active.add("x")
    return active


def handle_oauth_callback():
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if error:
        if state == "youtube":
            st.session_state["yt_error"] = f"YouTube login error: {error}"
            st.session_state["cb_yt"] = True
        elif state == "facebook":
            st.session_state["fb_error"] = f"Facebook login error: {error}"
            st.session_state["cb_fb"] = True
        elif state == "instagram":
            st.session_state["ig_error"] = f"Instagram login error: {error}"
            st.session_state["cb_ig"] = True
        _save_persisted_connected(_current_connected_set())
        return

    if not code:
        return

    if code in st.session_state["processed_codes"]:
        _save_persisted_connected(_current_connected_set())
        return

    st.session_state["processed_codes"].add(code)

    try:
        if state == "youtube":
            st.session_state["yt_token"] = exchange_youtube_code(code)
            st.session_state["yt_connected"] = True
            st.session_state["cb_yt"] = True
            st.session_state["yt_error"] = None

        elif state == "facebook":
            st.session_state["fb_token"] = exchange_meta_code(code)
            st.session_state["fb_connected"] = True
            st.session_state["cb_fb"] = True
            st.session_state["fb_error"] = None

        elif state == "instagram":
            st.session_state["ig_token"] = exchange_meta_code(code)
            st.session_state["ig_connected"] = True
            st.session_state["cb_ig"] = True
            st.session_state["ig_error"] = None

    except Exception as exc:
        if state == "youtube":
            st.session_state["yt_error"] = f"YouTube token error: {exc}"
            st.session_state["cb_yt"] = True
        elif state == "facebook":
            st.session_state["fb_error"] = f"Facebook token error: {exc}"
            st.session_state["cb_fb"] = True
        elif state == "instagram":
            st.session_state["ig_error"] = f"Instagram token error: {exc}"
            st.session_state["cb_ig"] = True
    finally:
        _save_persisted_connected(_current_connected_set())


handle_oauth_callback()

st.title("Multi-Platform Video Publisher")
st.subheader("Kahan-kahan upload karna hai?")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.checkbox("YouTube", key="cb_yt")
with c2:
    st.checkbox("Facebook", key="cb_fb")
with c3:
    st.checkbox("Instagram", key="cb_ig")
with c4:
    st.checkbox("X (Twitter)", key="cb_x")

st.divider()

if st.session_state["cb_yt"]:
    if st.session_state["yt_error"]:
        st.error(st.session_state["yt_error"])
    if st.session_state["yt_connected"]:
        st.success("YouTube Connected")
    elif not st.secrets.get("YOUTUBE_CLIENT_ID"):
        st.warning("Streamlit Secrets mein `YOUTUBE_CLIENT_ID` set karein.")
    else:
        st.markdown(f"👉 **[Click here to Connect YouTube]({get_youtube_auth_url()})**")

if st.session_state["cb_fb"]:
    if st.session_state["fb_error"]:
        st.error(st.session_state["fb_error"])
    if st.session_state["fb_connected"]:
        st.success("Facebook Connected")
    elif not st.secrets.get("META_APP_ID"):
        st.warning("Streamlit Secrets mein `META_APP_ID` set karein.")
    else:
        st.markdown(f"👉 **[Click here to Connect Facebook]({get_meta_auth_url('facebook')})**")

if st.session_state["cb_ig"]:
    if st.session_state["ig_error"]:
        st.error(st.session_state["ig_error"])
    if st.session_state["ig_connected"]:
        st.success("Instagram Connected")
    elif not st.secrets.get("META_APP_ID"):
        st.warning("Streamlit Secrets mein `META_APP_ID` set karein.")
    else:
        st.markdown(f"👉 **[Click here to Connect Instagram]({get_meta_auth_url('instagram')})**")

if st.session_state["cb_x"]:
    st.info("X (Twitter) uploader integration yahan add kiya ja sakta hai.")

st.divider()
st.subheader("Video Details & Publish Settings")

uploaded_video = st.file_uploader("Video file select karein", type=["mp4", "mov", "avi", "mkv"])
title = st.text_input("Title")
caption = st.text_area("Caption / Description")

publish_mode = st.radio(
    "Publishing Mode",
    options=["Public", "Private", "Schedule"],
    horizontal=True,
)

scheduled_datetime = None
if publish_mode == "Schedule":
    d_col, t_col = st.columns(2)
    with d_col:
        sched_date = st.date_input("Schedule Date")
    with t_col:
        sched_time = st.time_input("Schedule Time", value=time(12, 0))
    scheduled_datetime = datetime.combine(sched_date, sched_time)

if st.button("Publish Selected Platforms", type="primary"):
    selected = []
    if st.session_state["cb_yt"]:
        selected.append("YouTube")
    if st.session_state["cb_fb"]:
        selected.append("Facebook")
    if st.session_state["cb_ig"]:
        selected.append("Instagram")
    if st.session_state["cb_x"]:
        selected.append("X (Twitter)")

    if not selected:
        st.warning("Kam se kam ek platform select karein.")
    elif not uploaded_video:
        st.warning("Pehle ek video file upload karein.")
    else:
        st.success(
            f"Selected: {', '.join(selected)} | Mode: {publish_mode}"
            + (f" | Time: {scheduled_datetime}" if scheduled_datetime else "")
        )
