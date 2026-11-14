#!/usr/bin/env python3
"""Publish a generated Pulsenama MP4 to Buffer with a language- and mood-matched caption."""
import json
import os
import sys
from pathlib import Path

import requests


URDU_MOOD_CAPTIONS = {
    "sad": "کچھ احساس لفظوں سے زیادہ گہرے ہوتے ہیں۔",
    "romantic": "محبت کے خوبصورت احساسات کے نام۔",
    "motivational": "ہر نئی صبح ایک نیا حوصلہ لاتی ہے۔",
    "deep": "کچھ باتیں دل میں اتر جاتی ہیں۔",
    "peaceful": "چند لمحے سکون کے نام۔",
    "rain": "بارش، یادیں اور دل کی خاموشی۔",
    "memories": "کچھ یادیں ہمیشہ ساتھ رہتی ہیں۔",
}
ENGLISH_MOOD_CAPTIONS = {
    "sad": "Some feelings are deeper than words.",
    "romantic": "For the little moments that feel like love.",
    "motivational": "A little reminder to keep moving forward.",
    "deep": "Some words stay with us long after we read them.",
    "peaceful": "Take a moment, breathe, and feel the calm.",
    "rain": "Rainy moments and the memories they bring.",
    "memories": "Some memories never really leave.",
}

URDU_HASHTAGS = {
    "sad": ["#اداس_شاعری", "#درد_دل", "#اردو_شاعری"],
    "romantic": ["#محبت", "#عشق", "#اردو_شاعری"],
    "motivational": ["#حوصلہ", "#کامیابی", "#مثبت_سوچ"],
    "deep": ["#گہری_باتیں", "#زندگی", "#اردو_اقوال"],
    "peaceful": ["#سکون", "#زندگی", "#اردو_شاعری"],
    "rain": ["#بارش", "#یادیں", "#اداس_شاعری"],
    "memories": ["#یادیں", "#ماضی", "#اردو_شاعری"],
}
ENGLISH_HASHTAGS = {
    "sad": ["#SadPoetry", "#HeartTouching", "#PoetryLovers"],
    "romantic": ["#LovePoetry", "#RomanticQuotes", "#PoetryLovers"],
    "motivational": ["#Motivation", "#DailyInspiration", "#KeepGoing"],
    "deep": ["#DeepQuotes", "#LifeThoughts", "#PoetryLovers"],
    "peaceful": ["#PeacefulMind", "#PositiveVibes", "#DailyPoetry"],
    "rain": ["#RainyDays", "#RainyMood", "#PoetryLovers"],
    "memories": ["#Memories", "#Nostalgia", "#DeepFeelings"],
}


def build_caption(details):
    lines = details.splitlines()
    values = {}
    for line in lines:
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip().lower()] = value.strip()

    title = values.get("title", "Pulsenama")
    mood = values.get("mood", "peaceful").lower()
    language = values.get("language", "English").lower()

    try:
        start = lines.index("")
        end = next(
            (i for i in range(start + 1, len(lines))
             if lines[i].startswith("Background:")),
            len(lines),
        )
        poem = [line.strip() for line in lines[start + 1:end] if line.strip()]
    except ValueError:
        poem = []

    poem_text = "\n".join(poem[:3])
    if language == "urdu":
        mood_line = URDU_MOOD_CAPTIONS.get(mood, URDU_MOOD_CAPTIONS["peaceful"])
        hashtags = URDU_HASHTAGS.get(mood, URDU_HASHTAGS["peaceful"])
        hashtags += ["#UrduPoetry", "#Shayari", "#Pulsenama"]
    else:
        mood_line = ENGLISH_MOOD_CAPTIONS.get(mood, ENGLISH_MOOD_CAPTIONS["peaceful"])
        hashtags = ENGLISH_HASHTAGS.get(mood, ENGLISH_HASHTAGS["peaceful"])
        hashtags += ["#EnglishPoetry", "#Poetry", "#Pulsenama"]

    caption_parts = [title, poem_text, mood_line, "Follow for more poetry." if language != "urdu" else "مزید شاعری کے لیے فالو کریں۔"]
    caption = "\n\n".join(part for part in caption_parts if part)
    return caption + "\n\n" + " ".join(hashtags)


def main():
    api_key = os.getenv("BUFFER_API_KEY", "").strip()
    channel_id = os.getenv("BUFFER_CHANNEL_ID", "").strip()
    video_url = os.getenv("BUFFER_VIDEO_URL", "").strip()

    if not api_key or not channel_id:
        print("Buffer publishing skipped: add BUFFER_API_KEY and BUFFER_CHANNEL_ID repository secrets.")
        return 0
    if not video_url:
        raise RuntimeError("BUFFER_VIDEO_URL is missing; the video must be hosted at a public URL.")

    details = Path("poetry_demo.txt").read_text(encoding="utf-8")
    caption = build_caption(details)
    print("Prepared a language- and mood-matched caption with hashtags.")

    query = f"""
    mutation CreatePost {{
      createPost(input: {{
        text: {json.dumps(caption, ensure_ascii=False)}
        channelId: {json.dumps(channel_id)}
        schedulingType: automatic
        mode: addToQueue
        assets: [{{ video: {{ url: {json.dumps(video_url)} }} }}]
      }}) {{
        ... on PostActionSuccess {{
          post {{ id text dueAt status }}
        }}
        ... on MutationError {{
          message
        }}
      }}
    }}
    """
    response = requests.post(
        "https://api.buffer.com",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    result = ((payload.get("data") or {}).get("createPost") or {})
    post = result.get("post")
    if not post:
        raise RuntimeError(result.get("message") or "Buffer did not confirm post creation.")
    print(f"Buffer queued post {post.get('id')} for {post.get('dueAt') or 'the next queue slot'}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Buffer publishing failed: {exc}", file=sys.stderr)
        raise
