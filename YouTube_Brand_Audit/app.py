import streamlit as st
import pandas as pd
from dashboard_utils import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    export_to_excel,
    highlight_top_sponsored_topics
)

st.set_page_config(page_title="YouTube Brand Audit", layout="wide")
st.title("📊 YouTube Brand Sponsorship Analyzer")

with st.form(key="input_form"):
    channel_url = st.text_input("Enter YouTube Channel URL")
    max_videos = st.slider("How many recent videos to analyze?", 10, 100, 50, 10)
    openai_key = st.text_input("Your OpenAI API Key", type="password")
    submitted = st.form_submit_button("Run Audit")

if submitted:
    with st.spinner("Fetching channel data and analyzing sponsors..."):
        try:
            st.info("🔍 Extracting Channel ID...")
            channel_id = extract_channel_id_from_url(channel_url)

            st.info("📺 Getting channel metadata...")
            metadata = get_channel_metadata(channel_id)

            st.info("📹 Pulling recent videos and detecting sponsors...")
            video_data = get_recent_videos(channel_id, metadata, max_results=max_videos)

            df = pd.DataFrame(video_data)
            st.success("✅ Audit complete!")

            st.subheader(f"Summary for {metadata['title']}")
            st.markdown(f"**Subscribers:** {metadata['subscriberCount']}  ")
            st.markdown(f"**Videos analyzed:** {len(video_data)}")

            st.download_button("📥 Download Excel Report", data=export_to_excel(video_data, metadata), file_name="channel_report.xlsx")

            st.subheader("📌 Detected Sponsors")
            st.dataframe(df[['title', 'video_url', 'sponsor']], use_container_width=True)

            st.subheader("🔥 Top Performing Sponsored Topics")
            st.markdown(highlight_top_sponsored_topics(video_data))

        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")
