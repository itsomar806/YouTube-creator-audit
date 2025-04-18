import os
import re
import requests
import pandas as pd
import openai

# Set your API keys from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

sponsor_cache = {}

# fallback keywords list for basic brand detection
KNOWN_BRANDS = [
    "nordvpn", "hubspot", "hostinger", "squarespace", "skillshare", "audible",
    "betterhelp", "masterclass", "expressvpn", "shopify", "clickup", "monday.com"
]

KNOWN_SPONSOR_DOMAINS = [
    "clickhubspot", "hostinger.com", "nordvpn", "expressvpn", "audible.com",
    "betterhelp.com", "squarespace.com", "skillshare.com", "shopify.com"
]

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

def detect_sponsor(description):
    lines = [line.strip() for line in description.strip().splitlines() if line.strip()]
    first_line = lines[0] if lines else ''
    lowered = first_line.lower()

    if first_line in sponsor_cache:
        return sponsor_cache[first_line]

    # 1. Skip common platform mentions
    banned_terms = ["youtube", "instagram", "newsletter", "course", "discord", "twitter", "github"]
    if any(term in lowered for term in banned_terms):
        sponsor_cache[first_line] = ''
        return ''

    # 2. Try fallback from known domains first
    for domain in KNOWN_SPONSOR_DOMAINS:
        if domain in lowered:
            sponsor = domain.split(".")[0].capitalize()
            sponsor_cache[first_line] = sponsor
            return sponsor

    # 3. Try fallback from known brands
    for brand in KNOWN_BRANDS:
        if brand in lowered:
            sponsor_cache[first_line] = brand.capitalize()
            return brand.capitalize()

    # 4. GPT fallback (tight prompt, clean)
    try:
        prompt = f"""
Given the following single-line description from a YouTube video, extract the brand or third-party sponsor being promoted.

Only return the **brand name**. If it’s a personal offer, generic social platform, or nothing sponsored, return "None".

Description:
"{first_line}"
"""
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You extract external sponsor brand names."},
                {"role": "user", "content": prompt.strip()}
            ],
            max_tokens=20,
            temperature=0
        )
        result = response.choices[0].message.content.strip()
        sponsor = result if result.lower() != 'none' else ''
    except Exception:
        sponsor = ''

    sponsor_cache[first_line] = sponsor
    return sponsor

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
