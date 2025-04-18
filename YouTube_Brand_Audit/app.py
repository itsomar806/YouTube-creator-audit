import streamlit as st
from dashboard import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    export_to_excel,
    highlight_top_sponsored_topics
)
import pandas as pd

st.set_page_config(page_title="YouTube Brand Audit Tool", layout="wide")
st.title("📊 YouTube Brand Audit Tool")

url = st.text_input("Paste a YouTube channel URL:")

if st.button("Run Audit") and url:
    try:
        channel_id = extract_channel_id_from_url(url)
        metadata = get_channel_metadata(channel_id)

        if metadata is None:
            st.error("❌ Could not fetch channel metadata. Please check the URL or try again.")
            st.stop()

        st.success(f"✅ Found: {metadata['title']}")

        videos = get_recent_videos(channel_id, metadata)
        df = pd.DataFrame(videos)

        if df.empty:
            st.warning("No videos found on this channel.")
        else:
            # Save to Excel
            xlsx_path = export_to_excel(videos, metadata)
            st.download_button(
                label="📥 Download Excel Report",
                data=open(xlsx_path, "rb"),
                file_name=xlsx_path,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.subheader("📈 Top Performing Sponsors")
            sponsor_df = df[df["sponsor"] != ""]
            if not sponsor_df.empty:
                st.dataframe(
                    sponsor_df.groupby("sponsor")[["views", "likes", "comments"]]
                    .mean().sort_values(by="views", ascending=False)
                    .style.format("{:,.0f}"),
                    use_container_width=True
                )
            else:
                st.info("No sponsors detected.")

            # Top Sponsored Topics
            topic_df = highlight_top_sponsored_topics(videos)
            if not topic_df.empty:
                st.subheader("🔥 Top Performing Sponsored Topics")
                st.dataframe(
                    topic_df.style.format("{:,.0f}"),
                    use_container_width=True
                )
            else:
                st.info("No sponsored topics found.")

    except Exception as e:
        st.error(f"❌ {e}")

