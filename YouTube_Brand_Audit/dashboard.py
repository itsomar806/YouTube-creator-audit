import os
import re
import csv
import requests
import openai
from datetime import datetime
import pandas as pd
import streamlit as st
from collections import defaultdict

sponsor_cache = {}

YOUTUBE_API_KEY = "AIzaSyCZvrlrMXE1jCPDLZ6NVMDe1uf_OXhYBkM"
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

def call_youtube_api(endpoint: str, params: dict):
    params['key'] = YOUTUBE_API_KEY
    response = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params)
    if response.status_code in [400, 403]:
        raise requests.HTTPError(f"{response.status_code} Error: {response.text}")
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

def detect_sponsor(description: str) -> str:
    if description in sponsor_cache:
        return sponsor_cache[description]

    try:
        # Try common sponsor patterns first
        sponsor_patterns = [
            r"https?://(?:www\.)?([\w\-]+)\.com.*?utm_source=([\w\-]+)",
            r"sponsored by ([\w\s]+)",
            r"partnered with ([\w\s]+)",
            r"https?://(?:www\.)?([\w\-]+)\.com/[\w\-\?=]+"
        ]
        for pattern in sponsor_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                sponsor = match.group(1).strip()
                sponsor_cache[description] = sponsor
                return sponsor

        # Fallback to OpenAI
        lines = description.strip().splitlines()
        context = "\n".join(lines[:10])
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
        sponsor_cache[description] = '' if answer.lower() in ['none', 'no sponsor', 'n/a', ''] else answer
        return sponsor_cache[description]

    except Exception:
        sponsor_cache[description] = ''
        return ''


def get_channel_metadata(channel_id: str):
    data = call_youtube_api("channels", {
        "id": channel_id,
        "part": "snippet,statistics,brandingSettings"
    })
    if not data.get('items'):
        raise ValueError("Invalid or unknown channel ID. Please check that the channel exists.")
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
            'video_url': f"https://www.youtube.com/watch?v={vid}",
            'sponsor': detect_sponsor(snippet['description'])
        }
        result.append(video_info)
    return result

def highlight_top_sponsored_topics(video_data: list):
    df = pd.DataFrame(video_data)
    df = df[df['sponsor'] != '']
    if df.empty:
        return pd.DataFrame()
    df['topic'] = df['title'].apply(lambda x: x.split('|')[0].strip() if '|' in x else x.split(':')[0].strip())
    summary = df.groupby('topic')[['views', 'likes', 'comments']].mean().sort_values(by='views', ascending=False)
    return summary

def export_to_excel(video_data: list, metadata: dict):
    df = pd.DataFrame(video_data)
    filename = f"{metadata['title'].replace(' ', '_')}_channel_analysis.xlsx"
    df.to_excel(filename, index=False)
    return filename

__all__ = [
    "call_youtube_api",
    "extract_channel_id_from_url",
    "get_channel_metadata",
    "get_recent_videos",
    "detect_sponsor",
    "export_to_excel",
    "highlight_top_sponsored_topics"  # ✅ make sure this is included
]
