from datetime import datetime, time as dt_time, timedelta
import os
from zoneinfo import ZoneInfo
import streamlit as st

from meta_uploader import (
    get_authenticated_meta_session,
    upload_to_facebook,
    upload_to_instagram,
)
from x_uploader import upload_to_x
from youtube_uploader import (
    get_authenticated_youtube_service,
    to_iso_utc,
    upload_to_youtube,
)

st.set_page_config(page_title="Multi-Platform Video Publisher", page_icon="🎬")
st.title("🎬 Multi-Platform Video Auto-Publisher")

uploaded_file = st.file_uploader("Video file chunein (MP4/MOV)", type=["mp4", "mov", "avi"])
title = st.text_input("Video Title (YouTube ke liye)")
caption = st.text_area("Caption / Description (Sabhi platforms ke liye)")

st.subheader("Upload / Publish Option")
publish_mode = st.radio(
    "Aap video ko kaise publish karna chahte hain?",
    options=["Public", "Private", "Schedule"],
    horizontal=True,
)

schedule_iso_utc = None
schedule_unix_ts = None
chosen_local_dt = None
now_local = None

if publish_mode == "Schedule":
    tz_choice = st.selectbox("Timezone", options=["Asia/Kolkata", "UTC"], index=0)
    now_local = datetime.now(ZoneInfo(tz_choice))
    default_date = (now_local + timedelta(days=1)).date()
    default_time = dt_time(18, 0)

    d_col, t_col = st.columns(2)
    with d_col:
        sched_date = st.date_input("Schedule Date", value=default_date, min_value=now_local.date())
    with t_col:
        sched_time = st.time_input("Schedule Time", value=default_time)

    chosen_local_dt = datetime.combine(sched_date, sched_time).replace(tzinfo=ZoneInfo(tz_choice))
    if chosen_local_dt <= now_local:
        st.warning("Schedule time abhi ke samay se aage (future) ka rakhein.")

    schedule_iso_utc = to_iso_utc(sched_date, sched_time, tz_name=tz_choice)
    schedule_unix_ts = int(chosen_local_dt.timestamp())
    st.caption(f"🕒 Scheduled for: {chosen_local_dt.strftime('%Y-%m-%d %H:%M')} ({tz_choice})")

st.subheader("Kahan-kahan upload karna hai?")
col1, col2, col3, col4 = st.columns(4)
with col1:
    use_yt = st.checkbox("YouTube", value=True)
with col2:
    use_fb = st.checkbox("Facebook", value=False)
with col3:
    use_ig = st.checkbox("Instagram", value=False)
with col4:
    use_x = st.checkbox("X (Twitter)", value=False)

yt_service = None
if use_yt:
    yt_service = get_authenticated_youtube_service()
    st.caption("✅ YouTube connected")

selected_page_id = None
selected_page_token = None
selected_ig_user_id = None

if use_fb or use_ig:
    meta_pages = get_authenticated_meta_session()
    page_options = {
        f"{p.get('name')} ({p.get('id')})": p for p in meta_pages
    }
    chosen_label = st.selectbox("Apna Facebook Page chunein", options=list(page_options.keys()))
    chosen_page = page_options[chosen_label]
    selected_page_id = chosen_page.get("id")
    selected_page_token = chosen_page.get("access_token")
    ig_info = chosen_page.get("instagram_business_account") or {}
    selected_ig_user_id = ig_info.get("id")

    if use_fb:
        st.caption(f"✅ Facebook Page connected: {chosen_page.get('name')}")
    if use_ig:
        if selected_ig_user_id:
            st.caption(f"✅ Linked Instagram connected (@{ig_info.get('username', selected_ig_user_id)})")
        else:
            st.warning("Is Facebook Page se koi linked Instagram Business/Creator account nahi mila.")

if st.button("Publish Selected Platforms"):
    if not (use_yt or use_fb or use_ig or use_x):
        st.warning("Kam se kam ek platform ka checkbox tick karein.")
        st.stop()

    if uploaded_file is None:
        st.warning("Pehle ek video file upload karein.")
        st.stop()

    if use_yt and not title.strip():
        st.warning("YouTube ke liye Title zaroori hai.")
        st.stop()

    if publish_mode == "Schedule" and use_yt and chosen_local_dt is not None and now_local is not None:
        if chosen_local_dt <= now_local:
            st.error("YouTube schedule ke liye future date aur time chunein.")
            st.stop()

    temp_path = "temp_upload_video.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        if use_yt:
            with st.spinner("YouTube par process ho raha hai..."):
                try:
                    res = upload_to_youtube(
                        yt_service,
                        temp_path,
                        title.strip(),
                        caption,
                        publish_mode=publish_mode,
                        schedule_iso_utc=schedule_iso_utc,
                    )
                    st.success(f"✅ YouTube ({publish_mode}) done! Video ID: {res.get('id')}")
                except Exception as e:
                    st.error(f"❌ YouTube failed: {e}")

        if use_fb:
            with st.spinner("Facebook par process ho raha hai..."):
                try:
                    res = upload_to_facebook(
                        temp_path,
                        title.strip() or "Video",
                        caption,
                        page_id=selected_page_id,
                        page_token=selected_page_token,
                        publish_mode=publish_mode,
                        schedule_unix_ts=schedule_unix_ts,
                    )
                    st.success(f"✅ Facebook ({publish_mode}) done! ID: {res.get('id')}")
                except Exception as e:
                    st.error(f"❌ Facebook failed: {e}")

        if use_ig:
            with st.spinner("Instagram par process ho raha hai..."):
                try:
                    res = upload_to_instagram(
                        temp_path,
                        caption,
                        ig_user_id=selected_ig_user_id,
                        page_token=selected_page_token,
                        publish_mode=publish_mode,
                        schedule_unix_ts=schedule_unix_ts,
                    )
                    st.success(f"✅ Instagram ({publish_mode}) done! Media ID: {res.get('id')}")
                except Exception as e:
                    st.error(f"❌ Instagram failed: {e}")

        if use_x:
            with st.spinner("X (Twitter) par process ho raha hai..."):
                try:
                    res = upload_to_x(
                        temp_path,
                        caption,
                        publish_mode=publish_mode,
                        schedule_iso_utc=schedule_iso_utc,
                    )
                    st.success(f"✅ X (Twitter) ({publish_mode}) done! {res}")
                except Exception as e:
                    st.error(f"❌ X (Twitter) failed: {e}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)