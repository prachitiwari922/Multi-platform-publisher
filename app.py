from datetime import datetime, time
from urllib.parse import urlencode
import streamlit as st

# ---------------------------------------------------------
# 1. App Configuration & Constants
# ---------------------------------------------------------
st.set_page_config(page_title="Multi-Platform Publisher", layout="centered")

REDIRECT_URI = "https://multi-platform-publisher.streamlit.app"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
META_SCOPES = ["public_profile"]  # Abhi available scope; Page/IG permissions milne par add karein


# ---------------------------------------------------------
# 2. Session State Initialization
# ---------------------------------------------------------
DEFAULTS = {
    "yt_connected": False,
    "fb_connected": False,
    "ig_connected": False,
    "x_connected": False,
    "yt_token": None,
    "fb_token": None,
    "yt_error": None,
    "fb_error": None,
    "cb_yt": False,
    "cb_fb": False,
    "cb_ig": False,
    "cb_x": False,
    "processed_codes": set(),
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = set() if isinstance(value, set) else value


# ---------------------------------------------------------
# 3. OAuth URL Helpers
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 4. Token Exchange Placeholders (Connect your uploader modules)
# ---------------------------------------------------------
def exchange_youtube_code(code: str):
    """
    TODO: Apne youtube_uploader.py ke token exchange function ko yahan call karein.
    Example:
        from youtube_uploader import exchange_code_for_token
        return exchange_code_for_token(code, REDIRECT_URI)
    """
    if not code:
        raise ValueError("Missing YouTube auth code.")
    return {"code": code, "status": "connected"}


def exchange_meta_code(code: str):
    """
    TODO: Apne meta_uploader.py ke token exchange function ko yahan call karein.
    Example:
        from meta_uploader import exchange_code_for_token
        return exchange_code_for_token(code, REDIRECT_URI)
    """
    if not code:
        raise ValueError("Missing Meta auth code.")
    return {"code": code, "status": "connected"}


# ---------------------------------------------------------
# 5. One-Time OAuth Callback Handler
# ---------------------------------------------------------
def handle_oauth_callback():
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if error:
        if state == "youtube":
            st.session_state["yt_error"] = f"YouTube login error: {error}"
            st.session_state["cb_yt"] = True
        elif state in ("facebook", "instagram"):
            st.session_state["fb_error"] = f"Meta login error: {error}"
            st.session_state["cb_fb"] = True
        st.query_params.clear()
        return

    if not code:
        return

    # Ek hi code dobara exchange na ho isliye guard
    if code in st.session_state["processed_codes"]:
        st.query_params.clear()
        return

    st.session_state["processed_codes"].add(code)

    try:
        if state == "youtube":
            token = exchange_youtube_code(code)
            st.session_state["yt_token"] = token
            st.session_state["yt_connected"] = True
            st.session_state["cb_yt"] = True
            st.session_state["yt_error"] = None

        elif state == "facebook":
            token = exchange_meta_code(code)
            st.session_state["fb_token"] = token
            st.session_state["fb_connected"] = True
            st.session_state["cb_fb"] = True
            st.session_state["fb_error"] = None

        elif state == "instagram":
            token = exchange_meta_code(code)
            st.session_state["fb_token"] = token
            st.session_state["ig_connected"] = True
            st.session_state["cb_ig"] = True
            st.session_state["fb_error"] = None

    except Exception as exc:
        if state == "youtube":
            st.session_state["yt_error"] = f"YouTube token error: {exc}"
            st.session_state["cb_yt"] = True
        elif state in ("facebook", "instagram"):
            st.session_state["fb_error"] = f"Meta token error: {exc}"
            st.session_state["cb_fb"] = True
    finally:
        # Query params turant clear karein taaki rerun par dobara code process na ho
        st.query_params.clear()


handle_oauth_callback()


# ---------------------------------------------------------
# 6. UI: Platform Selection & Connections
# ---------------------------------------------------------
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

# YouTube Connection Box
if st.session_state["cb_yt"]:
    if st.session_state["yt_error"]:
        st.error(st.session_state["yt_error"])

    if st.session_state["yt_connected"]:
        st.success("YouTube Connected")
    else:
        if not st.secrets.get("YOUTUBE_CLIENT_ID"):
            st.warning("Streamlit Secrets mein `YOUTUBE_CLIENT_ID` set karein.")
        else:
            st.markdown(f"👉 **[Click here to Connect YouTube]({get_youtube_auth_url()})**")

# Facebook Connection Box
if st.session_state["cb_fb"]:
    if st.session_state["fb_error"]:
        st.error(st.session_state["fb_error"])

    if st.session_state["fb_connected"]:
        st.success("Facebook Connected")
    else:
        if not st.secrets.get("META_APP_ID"):
            st.warning("Streamlit Secrets mein `META_APP_ID` set karein.")
        else:
            st.markdown(f"👉 **[Click here to Connect Facebook]({get_meta_auth_url('facebook')})**")

# Instagram Connection Box
if st.session_state["cb_ig"]:
    if st.session_state["ig_connected"]:
        st.success("Instagram Connected")
    else:
        if not st.secrets.get("META_APP_ID"):
            st.warning("Streamlit Secrets mein `META_APP_ID` set karein.")
        else:
            st.markdown(f"👉 **[Click here to Connect Instagram]({get_meta_auth_url('instagram')})**")

# X (Twitter) Placeholder Box
if st.session_state["cb_x"]:
    st.info("X (Twitter) uploader integration yahan add kiya ja sakta hai.")


# ---------------------------------------------------------
# 7. UI: Video Details & Publishing Controls
# ---------------------------------------------------------
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
        # TODO: Yahan selected platforms ke hisaab se youtube_uploader / meta_uploader / x_uploader call karein
