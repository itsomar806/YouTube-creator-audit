import os
import re
import requests
import openai
import pandas as pd

sponsor_cache = {}

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

def call_youtube_api(endpoint: str, params: dict):
    params['key'] = YOUTUBE_API_KEY
    response = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params)
    response.raise_for_status()
    return response.json()

def extract_channel_id_from_url(url: str) -> str:
    if "@" in url:
        handle = url.strip().split("@")[-1].split("/")[0]
        data = call_youtube_api("search", {
            "q": handle,
            "type": "channel",
            "part": "snippet",
            "maxResults": 1
        })
        if not data['items']:
            raise ValueError("❌ Could not extract channel ID from YouTube page")
        return data['items'][0]['snippet']['channelId']
    elif "channel/" in url:
        return url.split("channel/")[-1].split("/")[0]
    raise ValueError("❌ Invalid YouTube channel URL format")

def get_channel_metadata(channel_id: str):
    try:
        data = call_youtube_api("channels", {
            "id": channel_id,
            "part": "snippet,statistics,brandingSettings"
        })
    except Exception:
        return None

    if not data.get('items'):
        return None

    item = data['items'][0]
    snippet = item['snippet']
    stats = item['statistics']
    return {
        'title': snippet['title'],
        'description': snippet['description'],
        'country': snippet.get('country', 'N/A'),
        'publishedAt': snippet['publishedAt'],
        'subscriberCount': stats.get('subscriberCount'),
        'videoCount': stats.get('videoCount'),
        'viewCount': stats.get('viewCount')
    }

def get_recent_videos(channel_id: str, channel_metadata: dict, max_results: int = 50):
    uploads_response = call_youtube_api("channels", {
        "id": channel_id,
        "part": "contentDetails"
    })
    uploads_playlist_id = uploads_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    playlist_items = call_youtube_api("playlistItems", {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": max_results
    })
    video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_items['items']]
    videos_response = call_youtube_api("videos", {
        "part": "snippet,statistics",
        "id": ','.join(video_ids)
    })
    result = []
    for item in videos_response['items']:
        vid = item['id']
        snippet = item['snippet']
        stats = item['statistics']
        video_info = {
            'videoId': vid,
            'title': snippet['title'],
            'description': snippet['description'],
            'publishedAt': snippet['publishedAt'],
            'views': int(stats.get('viewCount', 0)),
            'likes': int(stats.get('likeCount', 0)),
            'comments': int(stats.get('commentCount', 0)),
            'video_url': f"https://www.youtube.com/watch?v={vid}"
        }
        result.append(video_info)
    return result

def detect_sponsor(description: str) -> str:
    if description in sponsor_cache:
        return sponsor_cache[description]

    # fallback regex
    regex = r"https?://(?:www\.)?([\w\-]+)\.com"
    match = re.search(regex, description, re.IGNORECASE)
    if match:
        sponsor = match.group(1)
        if sponsor.lower() not in ["youtube", "instagram"]:
            sponsor_cache[description] = sponsor
            return sponsor

    # fallback to GPT
    try:
        lines = description.strip().splitlines()
        context = "\n".join(lines[:5])
        prompt = (
            "You are a sponsorship detection expert. Your job is to extract the name of an external "
            "third-party sponsor (brand/company) from the YouTube description text provided.\n"
            "Ignore all URLs or mentions of the creator's own programs, mentorships, or newsletters.\n"
            "Do not include vague phrases like 'None', 'No sponsor', or promotional taglines.\n"
            "Respond ONLY with the sponsor name (e.g., 'HubSpot', 'NordVPN', 'Squarespace').\n"
            "If there is no clear external sponsor, return: None\n\n"
            f"Description:\n{context}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You extract third-party sponsors from YouTube video descriptions."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=30,
            temperature=0
        )
        answer = response.choices[0].message.content.strip()
        if answer.lower() in ['none', 'no sponsor', 'n/a', '', 'youtube', 'instagram']:
            sponsor_cache[description] = ''
        else:
            sponsor_cache[description] = answer
        return sponsor_cache[description]

    except Exception:
        sponsor_cache[description] = ''
        return ''

def export_to_excel(video_data: list, metadata: dict):
    # Export to Excel + CSV
    df = pd.DataFrame(video_data)
    excel_file = f"{metadata['title'].replace(' ', '_')}_channel_analysis.xlsx"
    csv_file = f"{metadata['title'].replace(' ', '_')}_channel_analysis.csv"
    df.to_excel(excel_file, index=False)
    df.to_csv(csv_file, index=False)
    return excel_file

def highlight_top_sponsored_topics(video_data: list):
    df = pd.DataFrame(video_data)
    df = df[df['sponsor'] != '']
    if df.empty:
        return pd.DataFrame()
    df['topic'] = df['title'].apply(lambda x: x.split('|')[0].strip() if '|' in x else x.split(':')[0].strip())
    summary = df.groupby('topic')[['views', 'likes', 'comments']].mean().sort_values(by='views', ascending=False)
    return summary

__all__ = [
    "call_youtube_api",
    "extract_channel_id_from_url",
    "get_channel_metadata",
    "get_recent_videos",
    "detect_sponsor",
    "export_to_excel",
    "highlight_top_sponsored_topics"
]
