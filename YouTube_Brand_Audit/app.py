import streamlit as st
import pandas as pd

from dashboard_utils import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    export_to_excel,
    highlight_top_sponsored_topics
)

st.set_page_config(page_title="YouTube Brand Audit Tool", layout="wide")
st.title("📊 YouTube Brand Audit Tool")

url = st.text_input("Paste a YouTube channel URL:")

if st.button("Run Audit") and url:
    try:
        channel_id = extract_channel_id_from_url(url)
        st.info(f"🔍 Channel ID: {channel_id}")

        metadata = get_channel_metadata(channel_id)
        if metadata is None:
            st.error("❌ Could not fetch channel metadata. Please check the URL or try again.")
            st.stop()

        st.success(f"✅ Found: {metadata['title']}")

        videos = get_recent_videos(channel_id, metadata)
        df = pd.DataFrame(videos)

        if df.empty:
            st.warning("No videos found on this channel.")
            st.stop()

        # Show raw video descriptions first
        st.subheader("📄 Video Descriptions")
        for video in videos:
            st.markdown(f"**{video['title']}**\n\n{video['description']}")

        # Detect sponsors using OpenAI
        st.subheader("🤖 Detected Sponsors")
        for video in videos:
            desc_head = "\n".join(video['description'].strip().splitlines()[:5])
            sponsor = detect_sponsor(desc_head)
            if sponsor and sponsor.lower() in ["youtube", "instagram"]:
                sponsor = ""
            st.markdown(f"🧠 **Detected Sponsor:** `{sponsor}`\n\n📰 **Video:** {video['title']}")

    except Exception as e:
        st.error(f"❌ {e}")

