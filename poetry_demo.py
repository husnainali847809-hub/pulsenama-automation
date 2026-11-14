#!/usr/bin/env python3
"""Standalone, manual-only cinematic poetry demo. Never publishes to Buffer."""
import json, os, re, subprocess, sys, math, random, wave, struct
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 24
KEY=os.getenv("OPENROUTER_API_KEY","").strip()
PEXELS=os.getenv("PEXELS_API_KEY","").strip()
PIXABAY=os.getenv("PIXABAY_API_KEY","").strip()
MODEL=os.getenv("OPENROUTER_MODEL","openrouter/free")
# Automatically choose creative settings; no workflow questions.
MOOD=random.choice(["sad","romantic","motivational","deep","peaceful","rain","memories"])
LANG=random.choice(["English","Urdu"])
DURATION=random.choice([18,20,22,24])
OUT,WORK=Path("poetry_demo.mp4"),Path("poetry_demo_work")
WORK.mkdir(exist_ok=True)

def run(cmd): subprocess.run(cmd,check=True)

def fallback_poem():
    """Original local fallback so a temporary AI/API response issue does not stop the demo."""
    poems = {
      "Urdu": {
        "sad": ("خاموش رات", ["بارش میں تیری یاد آئی، دل پھر خاموش ہو گیا", "جو خواب کبھی اپنا تھا، آج دھند میں کھو گیا"]),
        "deep": ("خاموش سوال", ["خاموشی بھی کبھی دل کی صدا بن جاتی ہے", "جو بات کہہ نہ سکیں، وہ دعا بن جاتی ہے"]),
        "peaceful": ("سکون کا لمحہ", ["ہوا کے ساتھ کچھ خواب بہنے دو", "آج دل کو ذرا سکون سے رہنے دو"]),
      },
      "Roman Urdu": {
        "sad": ("Khamosh Raat", ["Barish mein teri yaad phir laut aayi", "Khamosh dil ne bas teri sada lagayi"]),
        "deep": ("Khamosh Sawal", ["Khamoshi mein bhi ek awaaz hoti hai", "Har raat ke baad nayi subah hoti hai"]),
        "peaceful": ("Sukoon Ka Lamha", ["Hawa se keh do zara dheere chale", "Aaj dil ko apne khayalon mein rehne de"]),
      },
      "English": {
        "sad": ("After the Rain", ["Some memories still whisper in the rain", "Some goodbyes keep echoing again"]),
        "deep": ("Quiet Questions", ["The quiet holds what words cannot say", "Even the darkest night gives way"]),
        "peaceful": ("A Gentle Moment", ["Let the world grow quiet for a while", "And let your tired heart learn to smile"]),
      }
    }
    lang = LANG if LANG in poems else "English"
    mood = MOOD if MOOD in poems[lang] else ("peaceful" if MOOD in ("romantic","peaceful") else ("deep" if MOOD in ("motivational","deep") else "sad"))
    title, lines = poems[lang][mood]
    print("Using built-in original poem fallback; AI response was unavailable or invalid.")
    return title, lines

def make_poem():
    if not KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY GitHub secret.")
    prompt=f"""Create text for a {MOOD} cinematic vertical poetry video in {LANG}.
Randomly choose ONE format: (A) a beautiful original 2-3 line poem, (B) a memorable quote, or (C) a famous, accurately attributed public-domain literary/poetry line.
Use well-known poets/writers where appropriate, but NEVER invent a famous author or falsely attribute words. If unsure of exact wording or attribution, write an original line instead.
Return ONLY valid JSON: {{"title":"short title","lines":["short line 1","short line 2","optional short attribution or third line"]}}.
Use 2 or 3 short lines total, emotionally strong and easy to read on a phone. No paragraphs, no explanations, no decorative quote marks, no emojis. Keep every line concise enough to fit on a 1080x1920 video. For Urdu, write proper Urdu script; for English, write natural English."""
    try:
        r=requests.post("https://openrouter.ai/api/v1/chat/completions",
          headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"},
          json={"model":MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0.75,"max_tokens":500},timeout=90)
        r.raise_for_status()
        payload=r.json()
        choices=payload.get("choices") or []
        message=choices[0].get("message") if choices else None
        content=message.get("content") if isinstance(message,dict) else None
        if isinstance(content,list):
            content="\n".join(str(part.get("text","")) for part in content if isinstance(part,dict))
        if not isinstance(content,str) or not content.strip():
            reason=(choices[0].get("finish_reason") if choices else None) or payload.get("error") or "empty AI content"
            print(f"OpenRouter returned no poem text ({reason}); switching to fallback.")
            return fallback_poem()
        raw=content.strip()
        if raw.startswith("```"):
            raw=raw.split("\\n",1)[1] if "\\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw=raw[:-3].strip()
        data=json.loads(raw)
        lines=[str(x).strip() for x in data.get("lines",[]) if str(x).strip()]
        if len(lines)<2:
            print("OpenRouter returned fewer than four lines; switching to fallback.")
            return fallback_poem()
        return str(data.get("title") or "")[:80],lines[:3]
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"OpenRouter poem request failed ({exc}); switching to fallback.")
        return fallback_poem()

BACKGROUND_CREDIT = "Source details unavailable"

def mood_search_terms():
    # Rotate through photographic subjects so consecutive videos do not reuse one look.
    choices = {
      "sad":["moody rainy street photography night reflections","misty forest cinematic photography","rain on window city lights photography"],
      "romantic":["golden hour ocean sunset photography","soft pink sky wildflowers cinematic photography","romantic mountain lake sunset landscape photo"],
      "motivational":["dramatic sunrise mountain landscape photography","golden sunlight ocean cliffs photography","winding mountain road sunrise cinematic photo"],
      "deep":["starry sky mountains long exposure photography","dramatic cloudy mountains fine art landscape","moonlit ocean night photography"],
      "peaceful":["misty lake forest morning photography","calm turquoise ocean aerial landscape photo","sunlight through green forest nature photography"],
      "rain":["rainy city street reflections cinematic photography","misty mountain rain landscape photography","rain drops on glass blurred city lights photo"],
      "memories":["old European street golden hour photography","vintage countryside road sunset photo","nostalgic seaside town film photography"],
    }
    return random.choice(choices.get(MOOD, ["cinematic nature landscape photography","fine art mountain landscape photo"]))

def get_pexels_video():
    """Return a mood-matched portrait Pexels video, or None if unavailable."""
    if not PEXELS:
        print("No PEXELS_API_KEY; moving to online image sources.")
        return None
    try:
        r=requests.get("https://api.pexels.com/videos/search",
          headers={"Authorization":PEXELS},
          params={"query":mood_search_terms(),"orientation":"portrait","per_page":12},timeout=30)
        r.raise_for_status()
        choices=[]
        for video in r.json().get("videos",[]):
            for item in video.get("video_files",[]):
                if item.get("link") and item.get("file_type")=="video/mp4":
                    vw,vh=int(item.get("width") or 0),int(item.get("height") or 0)
                    if vh>=720 and vh>vw:
                        choices.append((vw*vh,item["link"]))
        if not choices:
            print("No suitable portrait Pexels video found.")
            return None
        path=WORK/"background.mp4"
        with requests.get(max(choices)[1],stream=True,timeout=90) as response:
            response.raise_for_status()
            with path.open("wb") as out:
                for chunk in response.iter_content(1024*1024):
                    if chunk: out.write(chunk)
        if path.stat().st_size<100000:
            path.unlink(missing_ok=True)
            return None
        print("Using mood-matched portrait video from Pexels.")
        return path
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Pexels video search failed; trying images: {exc}")
        return None


def get_pixabay_video():
    """Fetch a mood-matched, portrait Pixabay video and record its creator/source."""
    global BACKGROUND_CREDIT
    if not PIXABAY:
        print("No PIXABAY_API_KEY; skipping Pixabay video search.")
        return None
    try:
        r=requests.get("https://pixabay.com/api/videos/",
          params={"key":PIXABAY,"q":mood_search_terms(),"video_type":"film",
                  "safesearch":"true","per_page":20},timeout=30)
        r.raise_for_status()
        hits=r.json().get("hits",[])
        random.shuffle(hits)
        choices=[]
        for hit in hits:
            files=hit.get("videos") or {}
            for quality in ("large","medium","small","tiny"):
                item=files.get(quality) or {}
                url=item.get("url")
                vw,vh=int(item.get("width") or 0),int(item.get("height") or 0)
                if url and vh>=600 and vh>vw:
                    choices.append((vw*vh,hit,item))
                    break
        if not choices:
            print("No suitable portrait Pixabay video found.")
            return None
        # Prefer the largest portrait version, while shuffling equal-sized candidates.
        choices.sort(key=lambda x:x[0],reverse=True)
        for _,hit,item in choices:
            try:
                path=WORK/"background.mp4"
                with requests.get(item["url"],stream=True,timeout=90) as response:
                    response.raise_for_status()
                    with path.open("wb") as out:
                        for chunk in response.iter_content(1024*1024):
                            if chunk: out.write(chunk)
                if path.stat().st_size<100000:
                    path.unlink(missing_ok=True)
                    continue
                creator=hit.get("user","Pixabay contributor")
                page=hit.get("pageURL","https://pixabay.com/videos/")
                BACKGROUND_CREDIT=f"Pixabay video by {creator} | {page}"
                print(f"Using mood-matched portrait Pixabay video by {creator}.")
                return path
            except (requests.RequestException,OSError) as exc:
                print(f"Pixabay video candidate failed; trying another: {exc}")
                path.unlink(missing_ok=True)
                continue
    except (requests.RequestException,ValueError,KeyError) as exc:
        print(f"Pixabay video search failed; trying other sources: {exc}")
    return None


def get_pixabay_image():
    """Fetch a real, mood-matched portrait photo from Pixabay."""
    global BACKGROUND_CREDIT
    if not PIXABAY:
        print("No PIXABAY_API_KEY; skipping Pixabay photo search.")
        return None
    try:
        r=requests.get("https://pixabay.com/api/",
          params={"key":PIXABAY,"q":mood_search_terms(),"image_type":"photo",
                  "orientation":"vertical","safesearch":"true","per_page":20,
                  "order":"popular"},timeout=30)
        r.raise_for_status()
        hits=r.json().get("hits",[])
        random.shuffle(hits)
        hits.sort(key=lambda hit:int(hit.get("imageWidth",0))*int(hit.get("imageHeight",0)),reverse=True)
        for hit in hits:
            url=hit.get("largeImageURL") or hit.get("webformatURL")
            if not url: continue
            try:
                path=WORK/"online_background.jpg"
                with requests.get(url,stream=True,timeout=60) as response:
                    response.raise_for_status()
                    if "image" not in response.headers.get("Content-Type","").lower():
                        continue
                    with path.open("wb") as out:
                        for chunk in response.iter_content(1024*1024):
                            if chunk: out.write(chunk)
                if path.stat().st_size<20000:
                    path.unlink(missing_ok=True)
                    continue
                try:
                    with Image.open(path) as check: check.verify()
                except Exception:
                    path.unlink(missing_ok=True)
                    continue
                creator=hit.get("user","Pixabay contributor")
                page=hit.get("pageURL","https://pixabay.com/")
                BACKGROUND_CREDIT=f"Pixabay photo by {creator} | {page}"
                print(f"Using real mood-matched Pixabay photo by {creator}.")
                return path
            except (requests.RequestException,OSError) as exc:
                print(f"Pixabay photo candidate failed; trying another: {exc}")
                path.unlink(missing_ok=True)
                continue
    except (requests.RequestException,ValueError,KeyError) as exc:
        print(f"Pixabay photo search failed; trying other sources: {exc}")
    return None

def get_online_image():
    """Fetch a mood-matched reusable image from Pexels or Wikimedia Commons."""
    global BACKGROUND_CREDIT
    terms=mood_search_terms()
    if PEXELS:
        try:
            r=requests.get("https://api.pexels.com/v1/search",
              headers={"Authorization":PEXELS},
              params={"query":terms,"orientation":"portrait","per_page":15},timeout=30)
            r.raise_for_status()
            photos=sorted(r.json().get("photos",[]),
              key=lambda p:p.get("width",0)*p.get("height",0),reverse=True)
            for photo in photos:
                srcs=photo.get("src") or {}
                url=srcs.get("portrait") or srcs.get("large2x") or srcs.get("large")
                if not url: continue
                path=WORK/"online_background.jpg"
                with requests.get(url,stream=True,timeout=60) as response:
                    response.raise_for_status()
                    with path.open("wb") as out:
                        for chunk in response.iter_content(1024*1024):
                            if chunk: out.write(chunk)
                if path.stat().st_size>20000:
                    BACKGROUND_CREDIT=f"Pexels photo by {photo.get('photographer','Pexels contributor')} "
                    print("Using a mood-matched Pexels photo.")
                    return path
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            print(f"Pexels photo search failed; trying Wikimedia Commons: {exc}")

    try:
        params={"action":"query","format":"json","generator":"search",
          "gsrsearch":terms+" filetype:bitmap","gsrnamespace":6,"gsrlimit":15,
          "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1600}
        r=requests.get("https://commons.wikimedia.org/w/api.php",params=params,
          headers={"User-Agent":"PulsenamaPoetryVideo/1.0 (attribution recorded)"},timeout=30)
        r.raise_for_status()
        pages=(r.json().get("query") or {}).get("pages") or {}
        candidates=[]
        for page in pages.values():
            info=(page.get("imageinfo") or [{}])[0]
            meta=info.get("extmetadata") or {}
            url=info.get("thumburl") or info.get("url")
            if url: candidates.append((page,info,url))
        for page,info,url in candidates:
            meta=info.get("extmetadata",{})
            artist=(meta.get("Artist") or {}).get("value","Unknown")
            filename=page.get("title","").replace("File:","",1)
            # Commons thumbnail URLs can occasionally return 403. Try the original
            # URL and Commons' own FilePath redirect independently, then continue
            # to the next candidate instead of aborting the entire search.
            urls=[url]
            if info.get("url") and info.get("url") not in urls:
                urls.append(info["url"])
            if filename:
                from urllib.parse import quote
                redirect="https://commons.wikimedia.org/wiki/Special:FilePath/"+quote(filename)
                if redirect not in urls: urls.append(redirect)
            for candidate_url in urls:
                try:
                    path=WORK/"online_background.jpg"
                    with requests.get(candidate_url,stream=True,timeout=60,
                      headers={"User-Agent":"PulsenamaPoetryVideo/1.0 (image download; contact: project owner)",
                               "Referer":"https://commons.wikimedia.org/"}) as response:
                        response.raise_for_status()
                        content_type=response.headers.get("Content-Type","").lower()
                        if "image" not in content_type:
                            continue
                        with path.open("wb") as out:
                            for chunk in response.iter_content(1024*1024):
                                if chunk: out.write(chunk)
                    if path.stat().st_size>20000:
                        try:
                            with Image.open(path) as check: check.verify()
                        except Exception:
                            path.unlink(missing_ok=True)
                            continue
                        page_url="https://commons.wikimedia.org/wiki/"+page.get("title","").replace(" ","_")
                        BACKGROUND_CREDIT=f"Wikimedia Commons: {page.get('title','image')} | Creator: {artist} | {page_url}"
                        print("Using a reusable Wikimedia Commons image; attribution recorded.")
                        return path
                except (requests.RequestException, OSError) as exc:
                    print(f"Commons candidate download failed; trying another URL/image: {exc}")
                    continue
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Wikimedia Commons image search failed: {exc}")
    return None


def get_unsplash_image():
    """Fetch a real photograph from Unsplash's public search endpoint; never generate art."""
    global BACKGROUND_CREDIT
    # Short search phrases work better than long keyword strings on photo libraries.
    terms = {
      "sad": ["rainy street night", "misty forest", "rain window city lights"],
      "romantic": ["sunset ocean", "wildflowers golden hour", "mountain lake sunset"],
      "motivational": ["mountain sunrise", "ocean cliffs sunrise", "mountain road dawn"],
      "deep": ["starry mountains", "dramatic cloudy mountains", "moonlit ocean"],
      "peaceful": ["misty lake forest", "calm turquoise ocean", "sunlight green forest"],
      "rain": ["rainy city reflections", "misty mountains rain", "raindrops window city"],
      "memories": ["old street golden hour", "countryside road sunset", "seaside town film"],
    }.get(MOOD, ["cinematic nature landscape"])
    headers = {
      "User-Agent": "Mozilla/5.0 (compatible; PulsenamaPoetryVideo/1.0)",
      "Accept": "application/json",
      "Referer": "https://unsplash.com/",
    }
    for query in terms:
        try:
            response = requests.get(
              "https://unsplash.com/napi/search/photos",
              params={"query": query, "per_page": 20, "orientation": "portrait"},
              headers=headers, timeout=30)
            response.raise_for_status()
            photos = response.json().get("results", [])
            random.shuffle(photos)
            for photo in photos:
                urls = photo.get("urls") or {}
                image_url = urls.get("regular") or urls.get("full") or urls.get("raw")
                if not image_url:
                    continue
                path = WORK / "online_background.jpg"
                try:
                    with requests.get(image_url, stream=True, timeout=60, headers=headers) as image_response:
                        image_response.raise_for_status()
                        if "image" not in image_response.headers.get("Content-Type", "").lower():
                            continue
                        with path.open("wb") as out:
                            for chunk in image_response.iter_content(1024 * 1024):
                                if chunk:
                                    out.write(chunk)
                    if path.stat().st_size < 20000:
                        path.unlink(missing_ok=True)
                        continue
                    try:
                        with Image.open(path) as check:
                            check.verify()
                    except Exception:
                        path.unlink(missing_ok=True)
                        continue
                    user = photo.get("user") or {}
                    creator = user.get("name", "Unsplash contributor")
                    profile = user.get("links", {}).get("html", "https://unsplash.com/")
                    page_url = photo.get("links", {}).get("html", "https://unsplash.com/")
                    BACKGROUND_CREDIT = (
                      f"Unsplash photo by {creator} | "
                      f"Photo: {page_url} | Creator: {profile}"
                    )
                    print(f"Using a real mood-matched Unsplash photograph: {creator}.")
                    return path
                except (requests.RequestException, OSError) as exc:
                    print(f"Unsplash photo candidate failed; trying another: {exc}")
                    path.unlink(missing_ok=True)
                    continue
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Unsplash search unavailable for '{query}': {exc}")
            continue
    return None


def generated_background():
    """Create a fresh, original cinematic nature illustration for every run (no stock footage)."""
    rng = random.Random()
    rng_sun_x = rng.uniform(0.35, 0.68)
    img = Image.new("RGB", (W, H))
    px = img.load()
    palettes = {
        "sad": ((10, 19, 34), (80, 91, 112), (205, 142, 105)),
        "rain": ((12, 25, 39), (66, 91, 111), (160, 183, 194)),
        "romantic": ((48, 31, 55), (190, 105, 92), (255, 197, 132)),
        "peaceful": ((12, 42, 54), (74, 139, 135), (235, 207, 151)),
        "deep": ((5, 11, 29), (43, 57, 88), (194, 176, 151)),
        "motivational": ((20, 42, 65), (111, 132, 126), (255, 202, 120)),
        "memories": ((27, 25, 42), (119, 88, 93), (226, 173, 135)),
    }
    top, horizon, light = palettes.get(MOOD, palettes["peaceful"])
    horizon_y = int(H * rng.uniform(0.43, 0.53))
    for y in range(H):
        t = y / max(1, horizon_y)
        if y <= horizon_y:
            q = min(1.0, t)
            col = tuple(int(top[k] * (1-q) + horizon[k] * q) for k in range(3))
        else:
            q = (y-horizon_y) / (H-horizon_y)
            col = tuple(int(horizon[k] * (1-q) + max(0, horizon[k]*0.35) * q) for k in range(3))
        for x in range(W):
            glow = max(0.0, 1.0 - (((x-W*rng_sun_x)/W)**2 + ((y-horizon_y*0.72)/(H*0.42))**2))
            px[x,y] = tuple(min(255, int(col[k] + light[k]*0.18*glow)) for k in range(3))
    d = ImageDraw.Draw(img, "RGBA")
    sun_x = int(W*rng_sun_x); sun_y = int(horizon_y*rng.uniform(0.58,0.82))
    radius = rng.randint(48,82)
    for rr, alpha in ((radius+34,12),(radius+18,20),(radius,210)):
        d.ellipse((sun_x-rr,sun_y-rr,sun_x+rr,sun_y+rr),fill=(*light,alpha))
    # Layered mountain silhouettes with varied original contours.
    for layer, base_y in enumerate((horizon_y+45,horizon_y+115,horizon_y+205)):
        pts=[(0,H)]
        x=0
        while x<=W:
            peak_x=x+rng.randint(35,115)
            peak_y=base_y-rng.randint(80,250)//(layer+1)
            pts.extend([(x,base_y),(min(W,peak_x),max(horizon_y-40,peak_y))])
            x=peak_x
        pts.extend([(W,H)])
        shade=(17+layer*10,28+layer*12,43+layer*13,235-layer*22)
        d.polygon(pts,fill=shade)
    # Lake/river with a broken reflection under the light.
    water_top=horizon_y+210
    d.rectangle((0,water_top,W,H),fill=(12,27,39,95))
    for i in range(95):
        yy=rng.randint(water_top,H-8)
        half=rng.randint(5,100)
        xx=sun_x+rng.randint(-half*2,half*2)
        d.line((xx-half,yy,xx+half,yy),fill=(*light,rng.randint(12,55)),width=rng.randint(1,4))
    # Dark pine silhouettes frame the scene without covering the text area.
    for side in (0,1):
        for i in range(13):
            x=rng.randint(0,150) if side==0 else rng.randint(W-150,W)
            y=rng.randint(horizon_y+80,H-40)
            height=rng.randint(90,260)
            d.rectangle((x-3,y-height//5,x+3,y),fill=(5,13,19,190))
            for k in range(4):
                yy=y-height+k*height//5
                width=(k+1)*rng.randint(12,22)
                d.polygon([(x,yy-height//4),(x-width,yy+height//8),(x+width,yy+height//8)],fill=(5,20,25,190))
    # Soft atmospheric haze and cinematic vignette.
    haze=Image.new("RGBA",(W,H),(0,0,0,0))
    hd=ImageDraw.Draw(haze)
    hd.ellipse((W*0.12,horizon_y-100,W*0.9,horizon_y+350),fill=(*light,24))
    img=Image.alpha_composite(img.convert("RGBA"),haze.filter(ImageFilter.GaussianBlur(75)))
    vignette=Image.new("L",(W,H),0); vd=ImageDraw.Draw(vignette)
    vd.ellipse((-W*0.22,-H*0.12,W*1.22,H*1.12),fill=210)
    vignette=vignette.filter(ImageFilter.GaussianBlur(95))
    dark=Image.new("RGBA",(W,H),(0,0,0,105))
    dark.putalpha(Image.eval(vignette,lambda v: 105-int(v*0.35)))
    img=Image.alpha_composite(img,dark)
    path=WORK/"original_nature_art.jpg"
    img.convert("RGB").save(path,quality=94)
    print("Created a unique original cinematic nature image; no stock image used.")
    return path

def get_font(size):
    # Use a real Latin font for English and an Arabic-script font for Urdu.
    # Pillow's tiny bitmap default font does not contain these glyphs and shows boxes.
    if LANG.lower() == "urdu":
        candidates = [
          "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
          "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates = [
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
          "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
          "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    raise RuntimeError("Required text font is missing; install DejaVu Sans and Noto Arabic fonts.")

def text_page_png(title, lines):
    """Fit short poetry neatly inside the safe area, like the supplied reference reel."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    rtl=LANG.lower()=="urdu"
    max_width=int(W*0.84)
    visible=[str(line).strip() for line in lines[:3] if str(line).strip()]

    def measure(text,font):
        try:
            return d.textbbox((0,0),text,font=font,direction="rtl" if rtl else None)
        except Exception:
            return d.textbbox((0,0),text,font=font)

    def width(text,font):
        b=measure(text,font)
        return b[2]-b[0]

    # Wrap long AI lines at word boundaries; never allow text beyond the frame.
    wrapped=[]
    for raw in visible:
        words=raw.split()
        current=""
        for word in words:
            candidate=(current+" "+word).strip()
            test_font=get_font(60 if rtl else 54)
            if current and width(candidate,test_font)>max_width:
                wrapped.append(current)
                current=word
            else:
                current=candidate
        if current:
            wrapped.append(current)
    visible=wrapped[:3] or [""]

    # Find the largest font that fits every line and the full upper safe area.
    chosen=None
    for size in range(62 if rtl else 56, 35, -2):
        font=get_font(size)
        boxes=[measure(line,font) for line in visible]
        heights=[max(1,b[3]-b[1]) for b in boxes]
        gap=max(18,int(size*0.34))
        total_h=sum(heights)+gap*max(0,len(heights)-1)
        if max((b[2]-b[0] for b in boxes),default=0)<=max_width and total_h<=int(H*0.25):
            chosen=(font,boxes,heights,gap,total_h)
            break
    if chosen is None:
        font=get_font(36)
        boxes=[measure(line,font) for line in visible]
        heights=[max(1,b[3]-b[1]) for b in boxes]
        gap=12
        total_h=sum(heights)+gap*max(0,len(heights)-1)
    else:
        font,boxes,heights,gap,total_h=chosen

    # Keep text in the upper third, safely away from every frame edge.
    y=max(int(H*0.25),int(H*0.34-total_h/2))
    y=min(y,int(H*0.43-total_h))
    for line,b,height in zip(visible,boxes,heights):
        text_w=b[2]-b[0]
        x=max(36,(W-text_w)//2)
        x=min(x,W-36-text_w)
        kw={"direction":"rtl"} if rtl else {}
        # Soft shadow for contrast, without a text box or panel.
        try:
            d.text((x+2,y+3),line,font=font,fill=(0,0,0,175),
                   stroke_width=3,stroke_fill=(0,0,0,135),**kw)
            d.text((x,y),line,font=font,fill=(255,255,250,255),
                   stroke_width=1,stroke_fill=(25,22,25,190),**kw)
        except Exception:
            d.text((x,y),line,font=font,fill=(255,255,250,255))
        y+=height+gap
    path=WORK/"poetry_overlay.png"
    layer.save(path)
    return path


def get_online_music():
    """Find a popular vocal track, widening the Jamendo search if a mood is quiet."""
    global BACKGROUND_CREDIT
    client_id=os.getenv("JAMENDO_CLIENT_ID","").strip()
    if not client_id:
        print("Missing JAMENDO_CLIENT_ID; add it as a GitHub Actions secret.")
        return None

    mood_tags={
      "sad":"sad emotional",
      "romantic":"romance pop",
      "motivational":"energetic rock",
      "deep":"emotional soul",
      "peaceful":"chillout acoustic",
      "rain":"sad chillout",
      "memories":"nostalgic emotional",
    }.get(MOOD,"emotional pop")

    # Jamendo's tracks endpoint returns album tracks only by default.
    # Explicitly include singles too, and widen the search before giving up.
    common={
      "client_id":client_id,"format":"json","limit":100,
      "type":"single albumtrack",
      "vocalinstrumental":"vocal",
      "audioformat":"mp32","audiodlformat":"mp32",
      "boost":"popularity_week",
    }
    searches=[
      {"fuzzytags":mood_tags.replace(" ","+"),"durationbetween":"35_600"},
      {"fuzzytags":mood_tags.replace(" ","+")},
      {"durationbetween":"35_600"},
      {},
    ]

    seen=set()
    try:
        for index,extra in enumerate(searches,1):
            params={**common,**extra}
            response=requests.get("https://api.jamendo.com/v3.0/tracks/",params=params,timeout=40)
            response.raise_for_status()
            payload=response.json()
            headers=payload.get("headers") or {}
            if headers.get("status")!="success":
                raise RuntimeError(headers.get("error_message") or "Jamendo API error")
            tracks=payload.get("results") or []
            print(f"Jamendo vocal search {index}: {len(tracks)} tracks returned.")
            for track in tracks:
                track_id=str(track.get("id",""))
                if not track_id or track_id in seen:
                    continue
                seen.add(track_id)
                allowed=track.get("audiodownload_allowed")
                can_download=(allowed is True or str(allowed).lower() in ("1","true")) and bool(track.get("audiodownload"))
                if not can_download:
                    continue
                path=WORK/"jamendo_vocal_song.mp3"
                try:
                    with requests.get(track["audiodownload"],stream=True,timeout=90) as download:
                        download.raise_for_status()
                        with path.open("wb") as out:
                            for chunk in download.iter_content(256*1024):
                                if chunk:
                                    out.write(chunk)
                    if path.stat().st_size<50000:
                        path.unlink(missing_ok=True)
                        continue
                    probe=subprocess.run(
                      ["ffmpeg","-v","error","-i",str(path),"-t","2","-f","null","-"],
                      stdout=subprocess.DEVNULL,stderr=subprocess.PIPE
                    )
                    if probe.returncode!=0:
                        path.unlink(missing_ok=True)
                        continue
                    title=track.get("name","Jamendo song")
                    artist=track.get("artist_name","Jamendo artist")
                    page=f"https://www.jamendo.com/track/{track_id}"
                    BACKGROUND_CREDIT += f"\\nSong: {title} — {artist} | Jamendo: {page}"
                    print(f"Using a popular vocal song from Jamendo: {title} — {artist}.")
                    return path
                except (requests.RequestException,OSError,subprocess.SubprocessError) as exc:
                    print(f"Jamendo track download failed; trying the next vocal track: {exc}")
                    path.unlink(missing_ok=True)
        print("Jamendo found no downloadable vocal tracks after four progressively broader searches.")
    except (requests.RequestException,ValueError,KeyError,RuntimeError) as exc:
        print(f"Jamendo vocal-song search failed: {exc}")
    return None

def make_mood_music(title, lines):
    """Compose a fresh, gentle piano-and-strings instrumental using a SoundFont."""
    try:
        import pretty_midi
    except ImportError as exc:
        raise RuntimeError("pretty_midi is required for the piano-and-strings soundtrack.") from exc

    profiles = {
      "sad":          {"bpm":66,"root":57,"chords":[[0,3,7],[8,0,3],[5,8,0],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
      "romantic":     {"bpm":76,"root":57,"chords":[[0,4,7],[9,0,4],[5,9,0],[7,11,2]],"lead":[0,2,4,5,7,9,11]},
      "peaceful":     {"bpm":70,"root":55,"chords":[[0,4,7],[5,9,0],[2,5,9],[7,11,2]],"lead":[0,2,4,5,7,9,11]},
      "deep":         {"bpm":62,"root":55,"chords":[[0,3,7],[6,10,1],[8,0,3],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
      "motivational": {"bpm":88,"root":55,"chords":[[0,4,7],[7,11,2],[9,0,4],[5,9,0]],"lead":[0,2,4,5,7,9,11]},
      "rain":         {"bpm":66,"root":55,"chords":[[0,3,7],[8,0,3],[5,8,0],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
      "memories":     {"bpm":68,"root":57,"chords":[[0,3,7],[5,8,0],[8,0,3],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
    }
    mood=MOOD if MOOD in profiles else "peaceful"
    p=profiles[mood]
    rng=random.Random()
    bpm=p["bpm"]+rng.randint(-3,3)
    beat=60.0/bpm
    bar=beat*4
    midi=pretty_midi.PrettyMIDI(initial_tempo=bpm)
    piano=pretty_midi.Instrument(program=0,name="Soft Grand Piano")
    strings=pretty_midi.Instrument(program=48,name="Warm Strings")
    pad=pretty_midi.Instrument(program=89,name="Warm Atmosphere")
    bell=pretty_midi.Instrument(program=10,name="Soft Music Box")
    progression=list(p["chords"])
    shift=rng.randrange(len(progression))
    progression=progression[shift:]+progression[:shift]
    if rng.random()<0.35: progression=list(reversed(progression))
    bars=int(math.ceil(DURATION/bar))+1
    for bi in range(bars):
        start=bi*bar
        if start>=DURATION:
            continue
        chord=progression[bi%len(progression)]
        # Long, quiet string harmony underneath the piano.
        for j,interval in enumerate(chord):
            note=p["root"]+interval
            strings.notes.append(pretty_midi.Note(
              velocity=42 if j==0 else 34,pitch=note+12,
              start=start,end=min(DURATION,start+bar*1.08)))
            pad.notes.append(pretty_midi.Note(
              velocity=22,pitch=note+24,
              start=start,end=min(DURATION,start+bar*1.2)))
        # Broken-chord piano notes with natural pauses, rather than repetitive beeps.
        arp=[p["root"]+chord[0]+12,p["root"]+chord[1]+12,
             p["root"]+chord[2]+12,p["root"]+chord[1]+24]
        order=[0,1,2,3] if mood in ("motivational","romantic") else [0,2,1,3]
        for k,idx in enumerate(order):
            onset=start+k*beat*0.82+rng.uniform(0,0.035)
            if onset>=DURATION: continue
            pitch=arp[idx]+rng.choice([0,0,0,12])
            dur=beat*rng.uniform(0.55,0.82)
            piano.notes.append(pretty_midi.Note(
              velocity=rng.randint(45,61),pitch=pitch,
              start=onset,end=min(DURATION,onset+dur)))
        # Sparse, lyrical top melody; keep plenty of breathing room.
        if bi%2==0 or mood=="motivational":
            scale=p["lead"]
            degree=rng.choice(scale)
            pitch=p["root"]+24+degree
            onset=start+beat*rng.choice([0.0,1.0,2.0])
            dur=beat*rng.uniform(1.0,1.8)
            if onset<DURATION:
                piano.notes.append(pretty_midi.Note(
                  velocity=rng.randint(34,49),pitch=pitch,
                  start=onset,end=min(DURATION,onset+dur)))
            if mood in ("romantic","peaceful","memories") and rng.random()<0.45 and onset+beat<DURATION:
                bell.notes.append(pretty_midi.Note(
                  velocity=27,pitch=pitch+12,start=onset+beat,
                  end=min(DURATION,onset+beat+beat*0.7)))
    midi.instruments.extend([strings,pad,piano,bell])
    midi_path=WORK/"cinematic_original.mid"
    wav_path=WORK/"cinematic_original.wav"
    midi.write(str(midi_path))
    soundfont="/usr/share/sounds/sf2/TimGM6mb.sf2"
    if not Path(soundfont).exists():
        raise RuntimeError("The General MIDI SoundFont was not installed by the workflow.")
    run(["fluidsynth","-ni",soundfont,str(midi_path),"-F",str(wav_path),"-r","22050"])
    print(f"Composed a fresh {mood} piano-and-strings soundtrack at {bpm} BPM.")
    return wav_path


def render_video(title,lines,bg,music):
    page=text_page_png(title,lines)
    if bg.suffix.lower()==".mp4":
        inputs=["-stream_loop","-1","-i",str(bg),"-loop","1","-i",str(page)]
    else:
        inputs=["-loop","1","-i",str(bg),"-loop","1","-i",str(page)]
    # Loop downloaded music if shorter than the video; generated WAV already matches duration.
    if music.suffix.lower() != ".wav":
        inputs += ["-stream_loop","-1","-i",str(music)]
    else:
        inputs += ["-i",str(music)]
    # A deliberate black opening, then a slow cinematic reveal of the photograph.
    base="[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.00012,1.06)':d=1:s=1080x1920:fps=24,setsar=1,trim=duration="+str(DURATION)+",setpts=PTS-STARTPTS,fade=t=in:st=0.75:d=1.15[bg]"
    filters=[base,
      "[1:v]format=rgba,fade=t=in:st=1.35:d=0.65:alpha=1[poem]",
      "[bg][poem]overlay=(W-w)/2:(H-h)/2:enable='between(t,1.30,"+str(DURATION)+")'[vout]",
      "[2:a]volume=1.6,loudnorm=I=-14:TP=-1.0:LRA=8,alimiter=limit=0.99,afade=t=in:st=0:d=1.25,afade=t=out:st="+str(max(0,DURATION-3))+":d=3[aout]"]
    cmd=["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),
      "-map","[vout]","-map","[aout]","-t",str(DURATION),"-r",str(FPS),
      "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-s","1080x1920",
      "-c:a","aac","-b:a","160k","-movflags","+faststart",str(OUT)]
    run(cmd)
    Path("poetry_demo.txt").write_text(f"Title: {title}\nMood: {MOOD}\nLanguage: {LANG}\nDuration: {DURATION}s\n\n"+
      "\n".join(lines)+"\n\nBackground: "+BACKGROUND_CREDIT+"\nShort 2–3 line poetry displayed directly on background; no text box or watermark. Mood-matched vocal song from Jamendo.\n",encoding="utf-8")

def main():
    print(f"Auto-selected: {MOOD} mood / {LANG} / {DURATION}s.")
    title,lines=make_poem()
    lines=lines[:3]
    # Prefer real portrait video backgrounds, then fall back to real photographs.
    bg=get_pexels_video()
    if bg is None:
        bg=get_pixabay_video()
    if bg is None:
        print("No suitable stock video found; trying online photos.")
        bg=get_online_image()
    if bg is None:
        bg=get_pixabay_image()
    if bg is None:
        print("Pixabay/Pexels/Wikimedia did not return a usable photo; trying Unsplash.")
        bg=get_unsplash_image()
    if bg is None:
        raise RuntimeError("No usable internet photo/video could be downloaded from Pexels, Pixabay, Wikimedia Commons, or Unsplash. Check API keys/network access and retry; no AI image will be generated.")
    music=get_online_music()
    if music is None:
        raise RuntimeError("No downloadable vocal song was found. Add a valid JAMENDO_CLIENT_ID GitHub Actions secret and retry; instrumental-only music is disabled.")
    render_video(title,lines,bg,music)
    print(f"SUCCESS: {OUT} ({OUT.stat().st_size} bytes). No social post was created.")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise