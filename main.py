
import os
import json
import re
import hashlib
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from google import genai

# ==============================
# PULSENAMA AUTO PUBLISHER
# ==============================

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_TOKEN = os.environ["FB_PAGE_TOKEN"]

MODEL = "gemini-flash-latest"
GRAPH_VERSION = "v26.0"
MAX_POSTS_PER_RUN = 1
SEEN_FILE = "seen.json"

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
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
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
            print("RSS error:", e)

    return articles


def make_post(article):
    prompt = f"""
You are the professional news editor of PulseNama.

Create a Facebook news post in a natural mix of Urdu
and English. Use Urdu script for Urdu sentences.

STRICT RULES:
1. Use only facts provided in the source.
2. Never invent names, dates, numbers or quotes.
3. Do not present allegations as confirmed facts.
4. Do not exaggerate or create clickbait.
5. Write an attractive, accurate headline.
6. Write 2-3 short paragraphs.
7. Add 3-5 relevant hashtags.
8. Do not copy the source wording.
9. If the article is unclear, misleading or lacks
   enough information, set publish to false.
10. Return valid JSON only.

JSON format:
{{
  "publish": true,
  "post_text": "Complete Facebook post"
}}

NEWS TITLE:
{article['title']}

NEWS SUMMARY:
{article['summary']}

SOURCE:
{article['link']}
"""

    response = client.models.generate_content(
        model=MODEL,
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


def publish_to_facebook(message, source_url):
    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{FB_PAGE_ID}/feed"
    )

    response = requests.post(
        url,
        data={
            "message": (
                message
                + "\n\nSource: "
                + source_url
                + "\n\n© PulseNama"
            ),
            "access_token": FB_PAGE_TOKEN
        },
        timeout=30
    )

    result = response.json()

    if response.status_code != 200 or "id" not in result:
        raise RuntimeError(
            "Facebook publishing failed: "
            + json.dumps(result)
        )

    return result["id"]


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

            post_id = publish_to_facebook(
                post,
                article["link"]
            )

            print("Published successfully:", post_id)

            seen.append(article_id)
            save_seen(seen)
            return

        except Exception as e:
            print("Processing error:", str(e))
            continue

    print("No suitable new news available.")


if __name__ == "__main__":
    main()
