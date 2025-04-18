import streamlit as st
import pandas as pd
from dashboard_utils import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    export_to_excel,
    highlight_top_sponsored_topics
)

st.set_page_config(page_title="YouTube Sponsor Audit Dashboard", layout="wide")
st.title("📊 YouTube Brand Sponsorship Audit")

with st.sidebar:
    st.header("Audit Settings")
    url_input = st.text_input("Paste a YouTube Channel URL:")
    limit = st.slider("Max Videos to Analyze", 10, 100, 50)

if url_input:
    try:
        channel_id = extract_channel_id_from_url(url_input)
        with st.spinner("Fetching channel data..."):
            metadata = get_channel_metadata(channel_id)
            video_data = get_recent_videos(channel_id, metadata, max_results=limit)

        st.success(f"Found {len(video_data)} videos for {metadata['title']}")

        df = pd.DataFrame(video_data)

        st.subheader("📈 Channel Overview")
        st.markdown(f"**Channel Name:** {metadata['title']}")
        st.markdown(f"**Subscribers:** {metadata['subscriberCount']}")
        st.markdown(f"**Videos:** {metadata['videoCount']}")
        st.markdown(f"**Views:** {metadata['viewCount']}")

        st.subheader("🎬 Recent Videos")
        st.dataframe(df[['title', 'views', 'likes', 'comments', 'sponsor', 'video_url']])

        st.download_button("📥 Download Excel Report", data=export_to_excel(video_data, metadata), file_name="audit_report.xlsx")

        st.subheader("🏆 Top Performing Sponsored Topics")
        st.markdown(highlight_top_sponsored_topics(video_data))

    except Exception as e:
        st.error(f"❌ Error: {e}")
