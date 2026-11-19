from datetime import datetime, time as dt_time, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import requests
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "https://multi-platform-publisher.streamlit.app/"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
OAUTH_QUERY_KEYS = ("code", "state", "error", "scope", "authuser", "prompt")


def _clear_oauth_query_params():
    """Sirf OAuth params hatata hai, baaki query params (jaise 'connected') ko bachaye rakhta hai."""
    for key in OAUTH_QUERY_KEYS:
        if key in st.query_params:
            del st.query_params[key]


def to_iso_utc(schedule_date, schedule_time, tz_name="Asia/Kolkata"):
    if not isinstance(schedule_time, dt_time):
        schedule_time = dt_time(12, 0)
    local_dt = datetime.combine(schedule_date, schedule_time).replace(tzinfo=ZoneInfo(tz_name))
    return local_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_yt_creds():
    client_id = str(st.secrets.get("YOUTUBE_CLIENT_ID", st.secrets.get("CLIENT_ID", ""))).strip()
    client_secret = str(st.secrets.get("YOUTUBE_CLIENT_SECRET", st.secrets.get("CLIENT_SECRET", ""))).strip()
    if not client_id or not client_secret:
        st.error("Secrets mein YOUTUBE_CLIENT_ID ya YOUTUBE_CLIENT_SECRET missing hai.")
        st.stop()
    return client_id, client_secret


def get_auth_url(client_id):
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": "youtube",
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def exchange_code_for_creds(auth_code, client_id, client_secret):
    clean_code = str(auth_code).strip()
    if not clean_code:
        raise RuntimeError("Empty auth code received.")

    resp = requests.post(
        TOKEN_URI,
        data={
            "code": clean_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    data = resp.json()
    if resp.status_code != 200 or "access_token" not in data:
        raise RuntimeError(data.get("error_description") or data.get("error") or str(data))

    return Credentials(
        token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def get_authenticated_youtube_service():
    client_id, client_secret = get_yt_creds()
    creds = st.session_state.get("yt_credentials")

    if creds and creds.valid:
        return build("youtube", "v3", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            st.session_state["yt_credentials"] = creds
            return build("youtube", "v3", credentials=creds)
        except Exception:
            st.session_state.pop("yt_credentials", None)

    auth_url = get_auth_url(client_id)
    oauth_state = st.query_params.get("state")
    oauth_error = st.query_params.get("error")
    auth_code = st.query_params.get("code")
    used_codes = st.session_state.setdefault("yt_used_codes", set())

    # Agar callback kisi aur platform (jaise facebook/instagram) ka hai, toh YouTube code exchange na karein
    if oauth_state and oauth_state != "youtube":
        st.markdown(f"### 👉 [Click here to Connect YouTube]({auth_url})")
        st.stop()

    if oauth_error:
        _clear_oauth_query_params()
        st.error(f"YouTube login error: {oauth_error}")
        st.markdown(f"### 👉 [Click here to Connect YouTube]({auth_url})")
        st.stop()

    if auth_code:
        if auth_code in used_codes:
            _clear_oauth_query_params()
            st.rerun()

        used_codes.add(auth_code)
        try:
            new_creds = exchange_code_for_creds(auth_code, client_id, client_secret)
            st.session_state["yt_credentials"] = new_creds
            _clear_oauth_query_params()
            st.rerun()
        except Exception as e:
            _clear_oauth_query_params()
            st.error(f"YouTube token error: {e}")
            st.markdown(f"### 👉 [Click here to Connect YouTube]({auth_url})")
            st.stop()

    st.markdown(f"### 👉 [Click here to Connect YouTube]({auth_url})")
    st.stop()


def upload_to_youtube(
    youtube,
    video_path,
    title,
    description,
    publish_mode="Public",
    schedule_iso_utc=None,
):
    mode = publish_mode.strip().lower()

    if mode == "schedule":
        if not schedule_iso_utc:
            raise ValueError("Schedule mode ke liye date aur time zaroori hai.")
        status_body = {
            "privacyStatus": "private",
            "publishAt": schedule_iso_utc,
        }
    elif mode == "private":
        status_body = {"privacyStatus": "private"}
    else:
        status_body = {"privacyStatus": "public"}

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
        },
        "status": status_body,
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response
