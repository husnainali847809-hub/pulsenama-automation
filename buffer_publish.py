#!/usr/bin/env python3
"""Publish a generated Pulsenama MP4 to a Buffer channel queue."""
import json
import os
import sys
from pathlib import Path

import requests


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
    lines = details.splitlines()
    title = next((line.partition(":")[2].strip() for line in lines if line.startswith("Title:")), "Pulsenama")
    try:
        start = lines.index("")
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("Background:")), len(lines))
        poem = [line.strip() for line in lines[start + 1:end] if line.strip()]
    except ValueError:
        poem = []
    caption = "\n".join([title, *poem]).strip() or "A new poetry video from Pulsenama."

    query = f"""
    mutation CreatePost {{
      createPost(input: {{
        text: {JSON.stringify("PLACEHOLDER")}
        channelId: {JSON.stringify("CHANNEL_PLACEHOLDER")}
        schedulingType: automatic
        mode: addToQueue
        assets: [{{ video: {{ url: {JSON.stringify("URL_PLACEHOLDER")} }} }}]
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
    query = query.replace({JSON.stringify("PLACEHOLDER")}, json.dumps(caption, ensure_ascii=False))
    query = query.replace({JSON.stringify("CHANNEL_PLACEHOLDER")}, json.dumps(channel_id))
    query = query.replace({JSON.stringify("URL_PLACEHOLDER")}, json.dumps(video_url))
    response = requests.post(
        "https://api.buffer.com",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
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
