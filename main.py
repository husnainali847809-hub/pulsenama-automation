
import os
import re
import json
import time
import hashlib
import logging
import xml.etree.ElementTree as ET

from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

import requests
import cloudinary
import cloudinary.uploader

from google import genai
from PIL import Image, ImageDraw, ImageFont


# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

BUFFER_API_KEY = os.environ["BUFFER_API_KEY"]

BUFFER_CHANNEL_ID = os.getenv(
    "BUFFER_CHANNEL_ID",
    "6aeb3cc2e29c69a1715d606e"
)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

AI_HORDE_API_KEY = os.getenv(
    "AI_HORDE_API_KEY",
    ""
)

CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
CLOUDINARY_API_KEY = os.environ["CLOUDINARY_API_KEY"]
CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]

TEXT_MODEL = os.getenv(
    "GEMINI_TEXT_MODEL",
    "gemini-3.8-flash"
)

MAX_ARTICLES_PER_RUN = int(
    os.getenv("MAX_ARTICLES_PER_RUN", "1")
)

SEEN_FILE = Path("seen.json")

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================
# CLOUDINARY CONFIGURATION
# ==========================================

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


# ==========================================
# NEWS SOURCE
# ==========================================

NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q="
    + quote_plus("(Pakistan OR world) when:1d")
    + "&hl=en-PK&gl=PK&ceid=PK:en"
)


# ==========================================
# DUPLICATE NEWS MANAGEMENT
# ==========================================

def load_seen():

    if not SEEN_FILE.exists():
        return set()

    try:
        data = json.loads(
            SEEN_FILE.read_text(encoding="utf-8")
        )

        return set(
            data if isinstance(data, list) else []
        )

    except (json.JSONDecodeError, OSError):

        logging.warning(
            "seen.json could not be read."
        )

        return set()


def save_seen(seen):

    SEEN_FILE.write_text(
        json.dumps(
            sorted(seen)[-1000:],
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8",
    )


def article_key(article):

    return hashlib.sha256(
        article["link"].encode("utf-8")
    ).hexdigest()


# ==========================================
# FETCH NEWS
# ==========================================

def fetch_news():

    response = requests.get(
        NEWS_RSS_URL,
        timeout=30
    )

    response.raise_for_status()

    root = ET.fromstring(
        response.content
    )

    items = []

    for item in root.findall(".//item"):

        title = (
            item.findtext("title") or ""
        ).strip()

        link = (
            item.findtext("link") or ""
        ).strip()

        description = re.sub(
            r"<[^>]+>",
            " ",
            item.findtext("description") or ""
        )

        description = re.sub(
            r"\s+",
            " ",
            description
        ).strip()

        pub_date = (
            item.findtext("pubDate") or ""
        ).strip()

        if title and link:

            items.append({
                "title": title,
                "link": link,
                "summary": description[:1200],
                "published": pub_date,
            })

    return items


# ==========================================
# GEMINI NEWS REVIEW AND POST COPY
# ==========================================

def make_post_copy(article):

    prompt = f"""
You are the careful editor of a news page called Unique News.

Use ONLY the facts in this supplied news item.

Do not add facts, numbers, quotes, names, or claims
that are not supported by the item.

If the item is unclear or appears sensational or unverified,
return exactly: UNSUITABLE

News title: {article['title']}
News summary: {article['summary']}
Publisher/link: {article['link']}
Published: {article['published']}

Return valid JSON only, with these keys:

headline: concise, accurate headline (maximum 14 words)

caption: clear Facebook caption (2-4 short sentences),
neutral tone, mention uncertainty if source text is incomplete,
then add source URL

hashtags: 2 to 4 relevant hashtags

image_brief: a visual description for an original editorial
illustration. Use fictional characters only. No real-person
likenesses, fabricated evidence, or extra factual claims.
"""

    result = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )

    raw = (
        result.text or ""
    ).strip()

    if raw.upper() == "UNSUITABLE":
        return None

    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw,
        flags=re.I
    )

    try:

        data = json.loads(raw)

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            f"Gemini did not return valid JSON: {raw[:500]}"
        ) from exc

    for key in (
        "headline",
        "caption",
        "hashtags",
        "image_brief"
    ):

        if not data.get(key):

            raise RuntimeError(
                f"Gemini response missing {key}"
            )

    return data


# ==========================================
# NEWS CATEGORY
# ==========================================

def get_news_category(headline, image_brief):

    text = (
        str(headline) + " " + str(image_brief)
    ).lower()

    categories = {

        "BUSINESS": [
            "business", "economy", "market",
            "gold", "price", "stock", "trade",
            "bank", "finance", "currency"
        ],

        "HEALTH": [
            "health", "hospital", "medical",
            "polio", "vaccine", "disease",
            "doctor", "medicine"
        ],

        "SPORTS": [
            "sport", "cricket", "football",
            "match", "player", "team",
            "tournament", "championship"
        ],

        "TECHNOLOGY": [
            "technology", "tech",
            "artificial intelligence",
            "computer", "digital", "software",
            "internet", "robot"
        ],

        "POLITICS": [
            "government", "minister", "election",
            "political", "policy", "parliament",
            "president", "prime minister"
        ],

        "EDUCATION": [
            "education", "university", "school",
            "student", "college", "exam"
        ]
    }

    for category, keywords in categories.items():

        if any(
            keyword in text
            for keyword in keywords
        ):

            return category

    return "LATEST NEWS"


# ==========================================
# FONT AND HEADLINE HELPERS
# ==========================================

def load_news_font(size, bold=True):

    if bold:

        font_path = (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
        )

    else:

        font_path = (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        )

    try:

        return ImageFont.truetype(
            font_path,
            size
        )

    except OSError:

        return ImageFont.load_default()


def wrap_headline(draw, headline, font, max_width):

    words = str(headline).split()

    lines = []
    current_line = ""

    for word in words:

        test_line = (
            current_line + " " + word
        ).strip()

        if draw.textlength(
            test_line,
            font=font
        ) <= max_width:

            current_line = test_line

        else:

            if current_line:
                lines.append(current_line)

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


# ==========================================
# PILLOW FALLBACK GRAPHIC
# ==========================================

def draw_category_visual(
    draw,
    category,
    yellow,
    white
):

    if category == "BUSINESS":

        points = [
            (810, 850),
            (900, 760),
            (980, 800),
            (1090, 650)
        ]

        draw.line(
            points,
            fill=yellow,
            width=14,
            joint="curve"
        )

        for x, y in points:

            draw.ellipse(
                (x - 13, y - 13, x + 13, y + 13),
                fill=white
            )

        for x, y1, y2 in [
            (800, 900, 1010),
            (890, 850, 1010),
            (980, 890, 1010)
        ]:

            draw.rectangle(
                (x, y1, x + 50, y2),
                fill=yellow
            )

    elif category == "HEALTH":

        draw.rounded_rectangle(
            (900, 680, 1010, 1010),
            radius=20,
            fill=yellow
        )

        draw.rounded_rectangle(
            (790, 790, 1120, 900),
            radius=20,
            fill=yellow
        )

    elif category == "SPORTS":

        draw.ellipse(
            (790, 680, 1120, 1010),
            outline=yellow,
            width=16
        )

        draw.line(
            (790, 845, 1120, 845),
            fill=white,
            width=6
        )

        draw.line(
            (955, 680, 955, 1010),
            fill=white,
            width=6
        )

    elif category == "TECHNOLOGY":

        for x in range(800, 1120, 65):

            draw.line(
                (x, 690, x, 1000),
                fill=yellow,
                width=4
            )

        for y in range(700, 1010, 65):

            draw.line(
                (800, y, 1110, y),
                fill=yellow,
                width=4
            )

        draw.ellipse(
            (890, 780, 1020, 910),
            outline=white,
            width=10
        )

    else:

        draw.ellipse(
            (790, 680, 1120, 1010),
            outline=yellow,
            width=14
        )

        draw.arc(
            (850, 680, 1060, 1010),
            0,
            360,
            fill=white,
            width=6
        )

        draw.arc(
            (790, 760, 1120, 930),
            0,
            360,
            fill=white,
            width=6
        )


def generate_image(
    image_brief,
    headline,
    output_path="news_image.png"
):

    width = 1200
    height = 1200

    yellow = (255, 204, 35)
    white = (255, 255, 255)
    grey = (185, 185, 185)
    dark = (12, 12, 17)

    category = get_news_category(
        headline,
        image_brief
    )

    img = Image.new(
        "RGB",
        (width, height)
    )

    draw = ImageDraw.Draw(img)

    for y in range(height):

        shade = int(
            12 + (y / height) * 15
        )

        draw.line(
            (0, y, width, y),
            fill=(shade, shade, shade + 5)
        )

    draw.ellipse(
        (730, 300, 1350, 920),
        outline=(45, 45, 45),
        width=5
    )

    draw.ellipse(
        (800, 370, 1280, 850),
        outline=(65, 55, 30),
        width=4
    )

    # Header

    draw.rectangle(
        (0, 0, width, 115),
        fill=(5, 5, 8)
    )

    draw.rectangle(
        (0, 110, width, 117),
        fill=yellow
    )

    logo_font = load_news_font(34)

    logo_text = "UNIQUE NEWS"

    logo_width = draw.textlength(
        logo_text,
        font=logo_font
    )

    draw.text(
        (width - logo_width - 65, 38),
        logo_text,
        font=logo_font,
        fill=yellow
    )

    # Category label

    label_font = load_news_font(23)

    draw.rounded_rectangle(
        (65, 165, 350, 220),
        radius=9,
        fill=yellow
    )

    draw.text(
        (85, 178),
        category,
        font=label_font,
        fill=dark
    )

    # Headline

    max_width = 1060
    font_size = 68

    while font_size >= 38:

        headline_font = load_news_font(
            font_size
        )

        lines = wrap_headline(
            draw,
            headline,
            headline_font,
            max_width
        )

        if len(lines) <= 5:
            break

        font_size -= 4

    if len(lines) > 5:

        lines = lines[:5]

        lines[-1] = (
            lines[-1].rstrip("., ") + "..."
        )

    y_position = 285

    for line in lines:

        draw.text(
            (65, y_position),
            line,
            font=headline_font,
            fill=white,
            stroke_width=1,
            stroke_fill=(0, 0, 0)
        )

        y_position += font_size + 22

    draw_category_visual(
        draw,
        category,
        yellow,
        white
    )

    draw.rounded_rectangle(
        (65, 1030, 350, 1042),
        radius=5,
        fill=yellow
    )

    footer_font = load_news_font(24)
    small_font = load_news_font(19, bold=False)

    draw.text(
        (65, 1080),
        "UNIQUE NEWS  |  STAY INFORMED",
        font=footer_font,
        fill=yellow
    )

    draw.text(
        (65, 1125),
        "EDITORIAL NEWS GRAPHIC",
        font=small_font,
        fill=grey
    )

    img.save(
        output_path,
        format="PNG",
        optimize=True
    )

    logging.info(
        "Pillow fallback graphic created: %s",
        output_path
    )

    return output_path


# ==========================================
# AI HORDE IMAGE GENERATION
# ==========================================

def generate_ai_horde_image(
    image_brief,
    headline,
    output_path="news_image.png"
):

    if not AI_HORDE_API_KEY:

        raise RuntimeError(
            "AI_HORDE_API_KEY is missing."
        )

    base_url = "https://aihorde.net/api"

    headers = {
        "apikey": AI_HORDE_API_KEY,
        "Client-Agent": "UniqueNewsPublisher:1.0:GitHub"
    }

    prompt = (
        "Professional cinematic editorial news illustration, "
        "original fictional characters only, no real-person likeness, "
        "professional photography composition, realistic lighting, "
        "detailed environment, black white and yellow visual identity. "
        "Create an original scene based on this description: "
        f"{image_brief} "
        "Do not write any text, letters, logos or watermarks. "
        "### blurry, low quality, distorted, watermark, text, logo"
    )

    payload = {
        "prompt": prompt,

        "params": {
            "width": 1024,
            "height": 1024,
            "steps": 25,
            "cfg_scale": 7.5,
            "n": 1
        },

        "nsfw": False,
        "censor_nsfw": True,
        "r2": True,
        "shared": False,
        "replacement_filter": True
    }

    # Submit image request

    response = requests.post(
        f"{base_url}/v2/generate/async",
        headers=headers,
        json=payload,
        timeout=45
    )

    response.raise_for_status()

    request_id = response.json().get("id")

    if not request_id:

        raise RuntimeError(
            f"AI Horde did not return request ID: "
            f"{response.text[:500]}"
        )

    logging.info(
        "AI Horde request started: %s",
        request_id
    )

    # Wait for image generation

    deadline = time.time() + 480

    while time.time() < deadline:

        check = requests.get(
            f"{base_url}/v2/generate/check/{request_id}",
            headers=headers,
            timeout=30
        )

        check.raise_for_status()

        status = check.json()

        if status.get("faulted"):

            raise RuntimeError(
                "AI Horde image generation failed."
            )

        if status.get("done"):
            break

        time.sleep(5)

    else:

        raise TimeoutError(
            "AI Horde image generation timed out."
        )

    # Retrieve completed generation

    result = requests.get(
        f"{base_url}/v2/generate/status/{request_id}",
        headers=headers,
        timeout=45
    )

    result.raise_for_status()

    generations = result.json().get(
        "generations",
        []
    )

    if not generations:

        raise RuntimeError(
            "AI Horde returned no image generations."
        )

    image_url = generations[0].get("img")

    if not image_url:

        raise RuntimeError(
            "AI Horde image URL is missing."
        )

    # Download generated image

    image_response = requests.get(
        image_url,
        timeout=60
    )

    image_response.raise_for_status()

    img = Image.open(
        BytesIO(image_response.content)
    ).convert("RGB")

    # Fit the image into a square canvas without distortion

    img.thumbnail(
        (1200, 1200),
        Image.Resampling.LANCZOS
    )

    canvas = Image.new(
        "RGB",
        (1200, 1200),
        (12, 12, 17)
    )

    x = (1200 - img.width) // 2
    y = (1200 - img.height) // 2

    canvas.paste(img, (x, y))

    # Add brand header and footer

    overlay = Image.new(
        "RGBA",
        (1200, 1200),
        (0, 0, 0, 0)
    )

    overlay_draw = ImageDraw.Draw(overlay)

    yellow = (255, 204, 35)
    white = (255, 255, 255)

    overlay_draw.rectangle(
        (0, 0, 1200, 115),
        fill=(5, 5, 8, 225)
    )

    overlay_draw.rectangle(
        (0, 110, 1200, 117),
        fill=(255, 204, 35, 255)
    )

    overlay_draw.rectangle(
        (0, 870, 1200, 1200),
        fill=(5, 5, 8, 220)
    )

    img = Image.alpha_composite(
        canvas.convert("RGBA"),
        overlay
    )

    draw = ImageDraw.Draw(img)

    # Logo

    logo_font = load_news_font(34)
    logo = "UNIQUE NEWS"

    logo_width = draw.textlength(
        logo,
        font=logo_font
    )

    draw.text(
        (1200 - logo_width - 55, 38),
        logo,
        font=logo_font,
        fill=yellow
    )

    # Headline

    font_size = 52

    headline_font = load_news_font(
        font_size
    )

    lines = wrap_headline(
        draw,
        headline,
        headline_font,
        1060
    )

    while len(lines) > 3 and font_size > 32:

        font_size -= 4

        headline_font = load_news_font(
            font_size
        )

        lines = wrap_headline(
            draw,
            headline,
            headline_font,
            1060
        )

    if len(lines) > 3:

        lines = lines[:3]

        lines[-1] = (
            lines[-1].rstrip("., ") + "..."
        )

    y_position = 925

    for line in lines:

        draw.text(
            (65, y_position),
            line,
            font=headline_font,
            fill=white
        )

        y_position += font_size + 15

    draw.text(
        (65, 1140),
        "UNIQUE NEWS | STAY INFORMED",
        font=load_news_font(23),
        fill=yellow
    )

    img.convert("RGB").save(
        output_path,
        format="PNG",
        optimize=True
    )

    logging.info(
        "AI Horde news image created: %s",
        output_path
    )

    return output_path


# ==========================================
# IMAGE GENERATION WITH AUTOMATIC FALLBACK
# ==========================================

def create_news_image(image_brief, headline):

    if AI_HORDE_API_KEY:

        try:

            return generate_ai_horde_image(
                image_brief,
                headline
            )

        except Exception as exc:

            logging.warning(
                "AI Horde failed. Using Pillow fallback. Error: %s",
                exc
            )

    else:

        logging.warning(
            "AI Horde API key not found. Using Pillow fallback."
        )

    return generate_image(
        image_brief,
        headline
    )


# ==========================================
# CLOUDINARY IMAGE UPLOAD
# ==========================================

def upload_image(image_path):

    result = cloudinary.uploader.upload(
        image_path,
        folder="unique-news",
        resource_type="image",
        overwrite=False,
    )

    url = result.get("secure_url")

    if not url:

        raise RuntimeError(
            "Cloudinary upload did not return a secure URL."
        )

    return url


# ==========================================
# BUFFER FACEBOOK PUBLISHING
# ==========================================

def publish_to_buffer(
    caption,
    headline,
    image_url
):

    query = """
    mutation CreateUniqueNewsPost($input: CreatePostInput!) {
        createPost(input: $input) {
            ... on PostActionSuccess {
                post {
                    id
                    text
                    dueAt
                    assets {
                        id
                        mimeType
                    }
                }
            }
            ... on MutationError {
                message
            }
        }
    }
    """

    payload = {

        "text": f"{headline}\n\n{caption}",

        "channelId": BUFFER_CHANNEL_ID,

        "schedulingType": "automatic",

        "mode": "addToQueue",

        "assets": [
            {
                "image": {
                    "url": image_url
                }
            }
        ],

        "metadata": {
            "facebook": {
                "type": "post"
            }
        },

        "aiAssisted": True,
    }

    response = requests.post(
        "https://api.buffer.com",

        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },

        json={
            "query": query,
            "variables": {
                "input": payload
            }
        },

        timeout=45,
    )

    response.raise_for_status()

    body = response.json()

    if body.get("errors"):

        raise RuntimeError(
            f"Buffer GraphQL error: {body['errors']}"
        )

    result = body.get(
        "data",
        {}
    ).get(
        "createPost",
        {}
    )

    if result.get("message"):

        raise RuntimeError(
            f"Buffer rejected post: {result['message']}"
        )

    post = result.get("post")

    if not post:

        raise RuntimeError(
            f"Unexpected Buffer response: {body}"
        )

    logging.info(
        "Queued Buffer post id=%s dueAt=%s",
        post.get("id"),
        post.get("dueAt")
    )


# ==========================================
# MAIN AUTOMATION
# ==========================================

def main():

    seen = load_seen()

    articles = fetch_news()

    logging.info(
        "Fetched %d news items",
        len(articles)
    )

    processed = 0

    for article in articles:

        key = article_key(article)

        if key in seen:
            continue

        logging.info(
            "Reviewing: %s",
            article["title"]
        )

        copy = make_post_copy(article)

        if copy is None:

            logging.info(
                "Skipped as unsuitable/unverified."
            )

            seen.add(key)
            save_seen(seen)

            continue

        # Generate AI image or Pillow fallback

        image_path = create_news_image(
            copy["image_brief"],
            copy["headline"]
        )

        # Upload image

        image_url = upload_image(
            image_path
        )

        # Format hashtags

        hashtags = copy["hashtags"]

        if isinstance(hashtags, list):

            hashtags = " ".join(
                str(tag)
                for tag in hashtags
            )

        caption = (
            f"{copy['caption']}\n\n{hashtags}"
        ).strip()

        # Queue Facebook post

        publish_to_buffer(
            caption,
            copy["headline"],
            image_url
        )

        seen.add(key)

        processed += 1

        save_seen(seen)

        if processed >= MAX_ARTICLES_PER_RUN:
            break

    save_seen(seen)

    logging.info(
        "Finished. New posts queued: %d",
        processed
    )


# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    main()
