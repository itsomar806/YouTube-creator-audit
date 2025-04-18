import os
import re
import requests
import pandas as pd
import openai
from dotenv import load_dotenv

load_dotenv()  # Load .env values into environment


# Set your API keys from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

sponsor_cache = {}

def extract_channel_id_from_url(url):
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    elif "/@" in url:
        handle = url.split("/@")[1].split("/")[0]
        data = call_youtube_api("search", {"q": f"@{handle}", "type": "channel", "part": "snippet"})
        return data['items'][0]['snippet']['channelId'] if data['items'] else None
    else:
        raise ValueError("Invalid YouTube channel URL.")

def call_youtube_api(endpoint, params):
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}"
    params['key'] = YOUTUBE_API_KEY
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"YouTube API error: {response.text}")
    return response.json()

def get_channel_metadata(channel_id):
    data = call_youtube_api("channels", {"id": channel_id, "part": "snippet,statistics"})
    if not data.get('items'):
        raise ValueError("Invalid or unknown channel ID.")
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

def get_recent_videos(channel_id, metadata, max_results=50):
    uploads_response = call_youtube_api("channels", {"id": channel_id, "part": "contentDetails"})
    playlist_id = uploads_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    playlist_items = call_youtube_api("playlistItems", {"part": "snippet", "playlistId": playlist_id, "maxResults": max_results})
    video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_items['items']]
    videos = call_youtube_api("videos", {"part": "snippet,statistics", "id": ','.join(video_ids)})
    result = []
    for item in videos['items']:
        desc = item['snippet']['description']
        sponsor = detect_sponsor("\n".join(desc.splitlines()[:5]))
        result.append({
            'videoId': item['id'],
            'title': item['snippet']['title'],
            'description': desc,
            'publishedAt': item['snippet']['publishedAt'],
            'views': int(item['statistics'].get('viewCount', 0)),
            'likes': int(item['statistics'].get('likeCount', 0)),
            'comments': int(item['statistics'].get('commentCount', 0)),
            'video_url': f"https://www.youtube.com/watch?v={item['id']}",
            'sponsor': sponsor if sponsor.lower() not in ["youtube", "instagram"] else ''
        })
    return result

def detect_sponsor(description):
    if description in sponsor_cache:
        return sponsor_cache[description]
    try:
        # Clean & isolate first 5 non-empty lines
        first_lines = "\n".join([line.strip() for line in description.splitlines() if line.strip()][:5])

        # Optimized prompt for OpenAI
        prompt = f"""
You are a sponsorship detection agent.
Your task is to extract the name of a company *not owned by the creator* (external sponsor) being promoted in a YouTube description.
Ignore: the creator’s own products (mentorships, newsletters, courses, etc.), and platforms like YouTube or Instagram.
Only return the sponsor brand name (e.g., 'HubSpot', 'NordVPN', 'Squarespace', etc). Respond only with the brand name or 'None'.

Text:
{first_lines}
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You extract sponsor brand names from YouTube descriptions."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=20,
            temperature=0
        )
        answer = response.choices[0].message.content.strip()

        # Filter common false positives
        if answer.lower() in ["none", "youtube", "instagram", "tiktok"]:
            sponsor_cache[description] = ''
        else:
            sponsor_cache[description] = answer
        return sponsor_cache[description]

    except Exception:
        sponsor_cache[description] = ''
        return ''

def export_to_excel(video_data, metadata):
    df = pd.DataFrame(video_data)
    filename = f"{metadata['title'].replace(' ', '_')}_channel_analysis.xlsx"
    df.to_excel(filename, index=False)
    return filename

def highlight_top_sponsored_topics(video_data):
    df = pd.DataFrame(video_data)
    df = df[df['sponsor'] != '']
    if df.empty:
        return "No sponsored videos to analyze."
    grouped = df.groupby('sponsor').agg({
        'views': 'mean',
        'likes': 'mean',
        'comments': 'mean',
        'title': 'count'
    }).rename(columns={'title': 'video_count'}).sort_values(by='views', ascending=False)
    return grouped.reset_index().to_markdown(index=False)
