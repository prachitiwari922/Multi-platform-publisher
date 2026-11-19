import streamlit as st

st.set_page_config(page_title="Multi-Platform Publisher", layout="centered")

# 1. Session state initialize karein (taaki rerun ya dusre platform par jaane par state na ude)
defaults = {
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

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = set() if isinstance(v, set) else v


def handle_oauth_callback():
    """
    URL se aaye OAuth code ko sirf ek baar process karke session_state mein save karta hai,
    aur phir query_params clear kar deta hai taaki agle rerun par 'Malformed auth code' na aaye.
    """
    params = st.query_params
    code = params.get("code")
    state = params.get("state")

    if not code:
        return

    # Agar yeh code pehle hi process ho chuka hai toh dobara exchange na karein
    if code in st.session_state["processed_codes"]:
        st.query_params.clear()
        return

    st.session_state["processed_codes"].add(code)

    try:
        if state == "youtube":
            # Yahan apne youtube_uploader.py ka token exchange function call karein:
            # token = exchange_youtube_code(code)
            token = {"auth_code_used": code}
            st.session_state["yt_token"] = token
            st.session_state["yt_connected"] = True
            st.session_state["cb_yt"] = True
            st.session_state["yt_error"] = None

        elif state == "facebook":
            # Yahan apne meta_uploader.py ka token exchange function call karein:
            # token = exchange_meta_code(code)
            token = {"auth_code_used": code}
            st.session_state["fb_token"] = token
            st.session_state["fb_connected"] = True
            st.session_state["cb_fb"] = True
            st.session_state["fb_error"] = None

    except Exception as e:
        if state == "youtube":
            st.session_state["yt_error"] = f"YouTube token error: {e}"
        elif state == "facebook":
            st.session_state["fb_error"] = f"Facebook token error: {e}"
    finally:
        # Sabse zaroori: code use hone ke baad URL params saaf karein
        st.query_params.clear()


handle_oauth_callback()

st.subheader("Kahan-kahan upload karna hai?")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.checkbox("YouTube", key="cb_yt")
with col2:
    st.checkbox("Facebook", key="cb_fb")
with col3:
    st.checkbox("Instagram", key="cb_ig")
with col4:
    st.checkbox("X (Twitter)", key="cb_x")

# YouTube section
if st.session_state["cb_yt"]:
    if st.session_state["yt_error"]:
        st.error(st.session_state["yt_error"])

    if st.session_state["yt_connected"]:
        st.success("YouTube Connected ✅ (Tick aur session safe hai)")
    else:
        # Yahan apni youtube_uploader.py se auth_url banayein jisme state="youtube" ho
        yt_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?state=youtube"
        st.markdown(f"👉 **[Click here to Connect YouTube]({yt_auth_url})**")

# Facebook section
if st.session_state["cb_fb"]:
    if st.session_state["fb_error"]:
        st.error(st.session_state["fb_error"])

    if st.session_state["fb_connected"]:
        st.success("Facebook Connected ✅")
    else:
        # Yahan apni meta_uploader.py se auth_url banayein jisme state="facebook" ho
        fb_auth_url = "https://www.facebook.com/v21.0/dialog/oauth?state=facebook"
        st.markdown(f"👉 **[Click here to Connect Facebook]({fb_auth_url})**")
