import os
import re
import json
import hashlib
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime, timezone

import requests
import cloudinary
import cloudinary.uploader
from google import genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BUFFER_API_KEY = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "6aeb3cc2e29c69a1715d606e")
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
CLOUDINARY_API_KEY = os.environ["CLOUDINARY_API_KEY"]
CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", "1"))
SEEN_FILE = Path("seen.json")

client = genai.Client(api_key=GEMINI_API_KEY)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

# Google News RSS query. You can change the region/language later.
NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q="
    + quote_plus("(Pakistan OR world) when:1d")
    + "&hl=en-PK&gl=PK&ceid=PK:en"
)

def load_seen():
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except (json.JSONDecodeError, OSError):
        logging.warning("seen.json could not be read; starting with an empty history.")
        return set()

def save_seen(seen):
    # Keep the file small enough for GitHub Actions commits.
    SEEN_FILE.write_text(
        json.dumps(sorted(seen)[-1000:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def fetch_news():
    response = requests.get(NEWS_RSS_URL, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        description = re.sub(r"\s+", " ", description).strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "summary": description[:1200],
                "published": pub_date,
            })
    return items

def article_key(article):
    return hashlib.sha256(article["link"].encode("utf-8")).hexdigest()

def make_post_copy(article):
    prompt = f""" You are the careful editor of a news page called Unique News. Use ONLY the facts in this supplied news item. Do not add facts, numbers, quotes, names, or claims that are not supported by the item. If the item is unclear or appears sensational/unverified, return exactly: UNSUITABLE News title: {article['title']} News summary: {article['summary']} Publisher/link: {article['link']} Published: {article['published']} Return valid JSON only, with these keys: headline: concise, accurate headline (maximum 14 words) caption: clear Facebook caption (2-4 short sentences), neutral tone, mention uncertainty if the source text is incomplete, then add source URL hashtags: 2 to 4 relevant hashtags image_brief: a visual description for an editorial illustration; no real person likenesses, no fabricated evidence, no extra factual claims. """
    result = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    raw = (result.text or "").strip()
    if raw == "UNSUITABLE":
        return None
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini did not return valid JSON: {raw[:500]}") from exc

    for key in ("headline", "caption", "hashtags", "image_brief"):
        if not data.get(key):
            raise RuntimeError(f"Gemini response missing {key}")
    return data

def generate_image(image_brief, headline, output_path="news_image.png"):
    prompt = f""" Create a polished cinematic editorial NEWS GRAPHIC for the brand UNIQUE NEWS. Story visual: {image_brief} Headline text to display exactly and legibly: "{headline}" Branding requirements: - Put a compact "UNIQUE NEWS" brand mark in the TOP-RIGHT corner. - Use a consistent black, white, and yellow visual identity. - Use a story-specific background and composition, not a repeated generic layout. - Strong readable headline typography, high contrast, professional newsroom design. - Label the visual "AI-GENERATED ILLUSTRATION" in small but readable text. - Do not depict a real public figure or imitate a real person's face. - Do not invent charts, statistics, documents, logos, or photographic evidence. - Do not add any extra headline or factual claim. - Square 1:1 social media composition, safe margins, clean typography. """
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
    )
    for part in response.parts:
        if getattr(part, "inline_data", None) is not None:
            image = part.as_image()
            image.save(output_path)
            return output_path
    raise RuntimeError("Gemini returned no image. Check image model access/quota.")

def upload_image(image_path):
    result = cloudinary.uploader.upload(
        image_path,
        folder="unique-news",
        resource_type="image",
        overwrite=False,
    )
    url = result.get("secure_url")
    if not url:
        raise RuntimeError("Cloudinary upload did not return a secure URL.")
    return url

def publish_to_buffer(caption, headline, image_url):
    # Buffer requires Facebook's post type and a publicly accessible image URL.
    query = """ mutation CreateUniqueNewsPost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id text dueAt assets { id mimeType } } } ... on MutationError { message } } } """
    payload = {
        "text": f"{headline}\n\n{caption}",
        "channelId": BUFFER_CHANNEL_ID,
        "schedulingType": "automatic",
        "mode": "addToQueue",
        "assets": [{"image": {"url": image_url}}],
        "metadata": {"facebook": {"type": "post"}},
        "aiAssisted": True,
    }
    response = requests.post(
        "https://api.buffer.com",
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": {"input": payload}},
        timeout=45,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError(f"Buffer GraphQL error: {body['errors']}")
    result = body.get("data", {}).get("createPost", {})
    if result.get("message"):
        raise RuntimeError(f"Buffer rejected post: {result['message']}")
    post = result.get("post")
    if not post:
        raise RuntimeError(f"Unexpected Buffer response: {body}")
    logging.info("Queued Buffer post id=%s dueAt=%s", post.get("id"), post.get("dueAt"))

def main():
    seen = load_seen()
    articles = fetch_news()
    logging.info("Fetched %d news items", len(articles))
    processed = 0

    for article in articles:
        key = article_key(article)
        if key in seen:
            continue

        logging.info("Reviewing: %s", article["title"])
        copy = make_post_copy(article)
        if copy is None:
            logging.info("Skipped as unsuitable/unverified.")
            seen.add(key)
            continue

        image_path = generate_image(copy["image_brief"], copy["headline"])
        image_url = upload_image(image_path)
        hashtags = copy["hashtags"]
        if isinstance(hashtags, list):
            hashtags = " ".join(str(tag) for tag in hashtags)
        caption = f"{copy['caption']}\n\n{hashtags}".strip()

        publish_to_buffer(caption, copy["headline"], image_url)
        seen.add(key)
        processed += 1
        save_seen(seen)

        if processed >= MAX_ARTICLES_PER_RUN:
            break

    save_seen(seen)
    logging.info("Finished. New posts queued: %d", processed)

if __name__ == "__main__":
    main()
