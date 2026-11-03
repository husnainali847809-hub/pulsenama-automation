import os
import json
import re
import hashlib
import textwrap
import feedparser
import requests

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageOps

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_TOKEN = os.environ["FB_PAGE_TOKEN"]

TEXT_MODEL = "gemini-flash-latest"
IMAGE_MODEL = "gemini-3.1-flash-image"
GRAPH_VERSION = "v26.0"

SEEN_FILE = "seen.json"
STORY_FILE = "story.jpg"

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.dawn.com/feeds/home",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"
]

client = genai.Client(api_key=GEMINI_API_KEY)


def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen[-1000:], f, ensure_ascii=False, indent=2)


def get_news():
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()

                if not title or not link:
                    continue

                published = entry.get("published")

                if published:
                    try:
                        pub_date = parsedate_to_datetime(published)

                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(
                                tzinfo=timezone.utc
                            )

                        if pub_date < cutoff:
                            continue

                    except (ValueError, TypeError):
                        pass

                articles.append({
                    "title": title,
                    "summary": summary[:2500],
                    "link": link
                })

        except Exception as e:
            print("RSS error:", str(e))

    return articles


def make_post(article):
    prompt = f"""
You are the professional news editor of PulseNama.

Write a Facebook news post in a natural mix of Urdu and English.
Use Urdu script for Urdu sentences.

STRICT RULES:
1. Use only facts provided in the source.
2. Never invent names, dates, numbers or quotes.
3. Do not present allegations as confirmed facts.
4. Do not exaggerate or create clickbait.
5. Write an attractive and accurate headline.
6. Write 2-3 short paragraphs.
7. Add 3-5 relevant hashtags.
8. Do not copy the source wording.
9. If the article is unclear or lacks enough information,
   set publish to false.
10. Return valid JSON only.

JSON format:
{{"publish": true, "post_text": "Complete Facebook post"}}

NEWS TITLE: {article['title']}
NEWS SUMMARY: {article['summary']}
SOURCE: {article['link']}
"""

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt
    )

    raw = (response.text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)

    if not isinstance(data, dict):
        return None

    if data.get("publish") is not True:
        return None

    post_text = data.get("post_text", "").strip()

    if len(post_text) < 100 or len(post_text) > 6000:
        return None

    return post_text


def generate_story_image(article):
    prompt = f"""
Create a professional, realistic editorial news photograph
for a Facebook news Story.

NEWS TOPIC: {article['title']}
NEWS CONTEXT: {article['summary'][:1000]}

Requirements:
- Vertical 9:16 composition.
- High-quality realistic editorial photography.
- Visually relevant to the news topic.
- Professional news-media appearance.
- Strong composition and clear subject.
- No text, no letters, no words.
- No logos, no watermarks.
- Do not depict fictional events as real.
"""

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="9:16"
            )
        )
    )

    generated = None

    for part in response.parts:
        if part.inline_data:
            generated = part.as_image()
            break

    if generated is None:
        raise RuntimeError("Gemini did not return a Story image.")

    image = generated.convert("RGB")
    image = ImageOps.fit(image, (1080, 1920))

    draw = ImageDraw.Draw(image, "RGBA")

    # Dark headline panel
    draw.rectangle(
        (0, 1250, 1080, 1920),
        fill=(0, 0, 0, 185)
    )

    font_path = (
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf"
    )

    try:
        brand_font = ImageFont.truetype(font_path, 48)
        title_font = ImageFont.truetype(font_path, 64)
    except OSError:
        brand_font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    draw.text(
        (65, 1310),
        "PULSENAMA  |  NEWS UPDATE",
        font=brand_font,
        fill=(255, 210, 60, 255)
    )

    title = article["title"]

    words = title.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()

        if draw.textlength(test, font=title_font) <= 950:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    y = 1410

    for line in lines[:5]:
        draw.text(
            (65, y),
            line,
            font=title_font,
            fill=(255, 255, 255, 255)
        )
        y += 85

    draw.text(
        (65, 1850),
        "Follow PulseNama for more updates",
        font=brand_font,
        fill=(255, 255, 255, 255)
    )

    image.save(STORY_FILE, "JPEG", quality=90)

    print("Story image created successfully.")


def publish_to_facebook(message, source_url):
    """
    Publish the news as a Facebook photo post.
    The generated story.jpg is reused as the post image.
    """
    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{FB_PAGE_ID}/photos"
    )

    caption = (
        message
        + "\\n\\nSource: "
        + source_url
        + "\\n\\n© PulseNama"
    )

    with open(STORY_FILE, "rb") as image_file:
        response = requests.post(
            url,
            data={
                "message": caption,
                "published": "true",
                "access_token": FB_PAGE_TOKEN
            },
            files={
                "source": (
                    "pulsenama-news.jpg",
                    image_file,
                    "image/jpeg"
                )
            },
            timeout=120
        )

    result = response.json()

    if response.status_code != 200 or "id" not in result:
        raise RuntimeError(
            "Facebook photo post failed: " + json.dumps(result)
        )

    return result.get("post_id", result["id"])


def publish_story():
    photos_url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{FB_PAGE_ID}/photos"
    )

    with open(STORY_FILE, "rb") as image_file:
        upload_response = requests.post(
            photos_url,
            data={
                "published": "false",
                "access_token": FB_PAGE_TOKEN
            },
            files={
                "source": (
                    "story.jpg",
                    image_file,
                    "image/jpeg"
                )
            },
            timeout=120
        )

    upload_result = upload_response.json()

    if upload_response.status_code != 200:
        raise RuntimeError(
            "Story image upload failed: "
            + json.dumps(upload_result)
        )

    photo_id = upload_result.get("id")

    if not photo_id:
        raise RuntimeError("Facebook did not return a photo ID.")

    story_url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{FB_PAGE_ID}/photo_stories"
    )

    story_response = requests.post(
        story_url,
        data={
            "photo_id": photo_id,
            "access_token": FB_PAGE_TOKEN
        },
        timeout=60
    )

    story_result = story_response.json()

    if story_response.status_code != 200:
        raise RuntimeError(
            "Facebook Story publishing failed: "
            + json.dumps(story_result)
        )

    print("Facebook Story published:", story_result)


def main():
    seen = load_seen()
    articles = get_news()

    print("Articles collected:", len(articles))

    for article in articles:
        article_id = hashlib.sha256(
            article["link"].encode("utf-8")
        ).hexdigest()

        if article_id in seen:
            continue

        try:
            post = make_post(article)

            if not post:
                print("Article skipped:", article["title"])
                seen.append(article_id)
                save_seen(seen)
                continue

            # Generate one branded news image for BOTH the feed post and Story
            generate_story_image(article)

            # Publish the news as a photo post (image + caption)
            post_id = publish_to_facebook(
                post,
                article["link"]
            )

            print("Facebook photo post published:", post_id)

            # Save history after the feed post succeeds
            seen.append(article_id)
            save_seen(seen)

            # Publish the same generated image as a Facebook Story
            try:
                publish_story()

            except Exception as story_error:
                print(
                    "Story publishing failed:",
                    str(story_error)
                )

            return

        except Exception as e:
            print("Processing error:", str(e))
            continue

    print("No suitable new news available.")


if __name__ == "__main__":
    main()
