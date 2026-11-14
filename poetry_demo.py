#!/usr/bin/env python3
"""Standalone, manual-only cinematic poetry demo. Never publishes to Buffer."""
import json, os, re, subprocess, sys, math, random, wave, struct
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 24
KEY=os.getenv("OPENROUTER_API_KEY","").strip()
PEXELS=os.getenv("PEXELS_API_KEY","").strip()
MODEL=os.getenv("OPENROUTER_MODEL","openrouter/free")
MOOD=os.getenv("POETRY_MOOD","sad").lower()
LANG=os.getenv("POETRY_LANGUAGE","Urdu")
DURATION=max(15,min(35,int(os.getenv("POETRY_DURATION","24"))))
OUT,WORK=Path("poetry_demo.mp4"),Path("poetry_demo_work")
WORK.mkdir(exist_ok=True)

def run(cmd): subprocess.run(cmd,check=True)

def fallback_poem():
    """Original local fallback so a temporary AI/API response issue does not stop the demo."""
    poems = {
      "Urdu": {
        "sad": ("خاموش رات", ["بارش کی بوندیں کچھ کہتی ہیں", "خاموش گلی میں یادیں رہتی ہیں", "چراغ جلتا ہے تنہائی کے ساتھ", "دل ڈھونڈتا ہے گزری ہوئی بات", "صبح آئے گی، یہ یقین رہے", "ہر اندھیرے کے بعد روشنی رہے"]),
        "deep": ("خاموش سوال", ["ستاروں سے اک سوال کیا", "خاموشی نے جواب دیا", "جو راستے دل سے نکلتے ہیں", "وہ منزلوں تک پہنچتے ہیں", "وقت ہر راز کھولتا ہے", "صبر نیا حوصلہ دیتا ہے"]),
        "peaceful": ("سکون کا لمحہ", ["ہوا آہستہ گنگناتی ہے", "جھیل چپکے سے مسکراتی ہے", "فکر کے بادل دور ہوئے", "دل کے موسم روشن ہوئے", "یہ لمحہ بس ٹھہر جائے", "روح کو تھوڑا سکون مل جائے"]),
      },
      "Roman Urdu": {
        "sad": ("Khamosh Raat", ["Barish ki boondein kuch kehti hain", "Khamosh gali mein yaadein rehti hain", "Chiragh jalta hai tanhai ke saath", "Dil dhoondta hai guzri hui baat", "Subah aaye gi, ye yaqeen rahe", "Har andhere ke baad roshni rahe"]),
        "deep": ("Khamosh Sawal", ["Sitaron se aik sawal kiya", "Khamoshi ne jawab diya", "Jo raste dil se nikalte hain", "Woh manzilon tak pohanchte hain", "Waqt har raaz kholta hai", "Sabr naya hosla deta hai"]),
        "peaceful": ("Sukoon Ka Lamha", ["Hawa aahista gungunati hai", "Jheel chupke se muskurati hai", "Fikr ke badal door huay", "Dil ke mausam roshan huay", "Ye lamha bas thehar jaye", "Rooh ko thora sukoon mil jaye"]),
      },
      "English": {
        "sad": ("After the Rain", ["The quiet streets remember rain", "Soft lights glow through windowpanes", "Some distant moments gently stay", "Then slowly drift and fade away", "A new dawn waits beyond the blue", "And brings a little hope anew"]),
        "deep": ("Quiet Questions", ["The stars keep secrets of the night", "The silence holds a softer light", "Each road can teach the heart to grow", "Each passing hour has more to show", "Be patient with the things unseen", "Tomorrow brings a space between"]),
        "peaceful": ("A Gentle Moment", ["The lake is calm beneath the sky", "A silver cloud goes drifting by", "The breeze moves softly through the trees", "The world slows down with every breeze", "Let this small moment softly stay", "And carry all the noise away"]),
      }
    }
    lang = LANG if LANG in poems else "English"
    mood = MOOD if MOOD in poems[lang] else "sad"
    title, lines = poems[lang][mood]
    print("Using built-in original poem fallback; AI response was unavailable or invalid.")
    return title, lines

def make_poem():
    if not KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY GitHub secret.")
    prompt=f"""Write a completely original short {LANG} poem for a {MOOD} cinematic vertical video.
Return ONLY valid JSON: {{"title":"short title","lines":["line 1","line 2","line 3","line 4","line 5","line 6"]}}.
Exactly 6 concise lines, natural language, emotionally meaningful, no famous or copyrighted poetry, no quotes, no emojis, no explanation."""
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
        if len(lines)<4:
            print("OpenRouter returned fewer than four lines; switching to fallback.")
            return fallback_poem()
        return str(data.get("title") or "A quiet moment")[:80],lines[:6]
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"OpenRouter poem request failed ({exc}); switching to fallback.")
        return fallback_poem()

BACKGROUND_CREDIT = "Source details unavailable"

def mood_search_terms():
    return {
      "sad":"rainy city night rain window",
      "romantic":"romantic sunset flowers ocean",
      "motivational":"sunrise mountain nature",
      "deep":"starry night sky galaxy",
      "peaceful":"calm ocean lake forest",
      "rain":"rain drops window city",
      "memories":"old street golden hour"
    }.get(MOOD, "cinematic nature landscape")

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
                    BACKGROUND_CREDIT=f"Pexels photo by {photo.get('photographer','Pexels contributor')} (Pexels licence)"
                    print("Using a licensed mood-matched Pexels photo.")
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
            lic=(meta.get("LicenseShortName") or {}).get("value","")
            if any(tag in lic.lower() for tag in ("cc0","public domain","cc by","cc-by")):
                url=info.get("thumburl") or info.get("url")
                if url: candidates.append((page,info,lic,url))
        for page,info,lic,url in candidates:
            path=WORK/"online_background.jpg"
            with requests.get(url,stream=True,timeout=60) as response:
                response.raise_for_status()
                with path.open("wb") as out:
                    for chunk in response.iter_content(1024*1024):
                        if chunk: out.write(chunk)
            if path.stat().st_size>20000:
                meta=info.get("extmetadata",{})
                artist=(meta.get("Artist") or {}).get("value","Unknown")
                page_url="https://commons.wikimedia.org/wiki/"+page.get("title","").replace(" ","_")
                BACKGROUND_CREDIT=f"Wikimedia Commons: {page.get('title','image')} | Creator: {artist} | Licence: {lic} | {page_url}"
                print("Using a reusable Wikimedia Commons image; attribution recorded.")
                return path
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Wikimedia Commons image search failed: {exc}")
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
    for p in ("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            try: return ImageFont.truetype(p,size)
            except Exception: pass
    return ImageFont.load_default()

def text_page_png(title, lines):
    """Render the complete poem/quote on one elegant, readable page."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    panel=Image.new("RGBA",(W,H),(0,0,0,0))
    pd=ImageDraw.Draw(panel)
    pd.rounded_rectangle((63,428,W-63,1500),radius=34,fill=(4,10,18,174),outline=(245,220,185,115),width=2)
    panel=panel.filter(ImageFilter.GaussianBlur(0.4))
    layer=Image.alpha_composite(layer,panel)
    d=ImageDraw.Draw(layer)
    rtl=LANG.lower()=="urdu"
    title_font=get_font(65 if rtl else 59)
    body_font=get_font(53 if rtl else 48)
    try:
        kw={"direction":"rtl"} if rtl else {}
        tb=d.textbbox((0,0),title,font=title_font,**kw)
        tx=(W-(tb[2]-tb[0]))//2
        d.text((tx,350),title,font=title_font,fill=(255,218,160,255),stroke_width=1,stroke_fill=(0,0,0,180),**kw)
    except Exception:
        d.text((65,350),title,font=title_font,fill=(255,218,160,255))
    y=665
    max_width=885
    for line in lines[:8]:
        # Keep each original poem line intact where possible; wrap only if required.
        chunks=[]; current=""
        for word in str(line).split():
            candidate=(current+" "+word).strip()
            try: width=d.textlength(candidate,font=body_font,direction="rtl" if rtl else None)
            except Exception: width=d.textlength(candidate,font=body_font)
            if width>max_width and current:
                chunks.append(current); current=word
            else: current=candidate
        if current: chunks.append(current)
        for chunk in chunks:
            try:
                kw={"direction":"rtl"} if rtl else {}
                box=d.textbbox((0,0),chunk,font=body_font,**kw)
                x=(W-(box[2]-box[0]))//2
                d.text((x+2,y+3),chunk,font=body_font,fill=(0,0,0,220),stroke_width=2,stroke_fill=(0,0,0,170),**kw)
                d.text((x,y),chunk,font=body_font,fill=(255,252,244,255),stroke_width=1,stroke_fill=(0,0,0,130),**kw)
            except Exception:
                d.text((65,y),chunk,font=body_font,fill=(255,252,244,255))
            y+=143
        y+=9
    # Small, consistent brand watermark on every generated video.
    watermark_font=get_font(27)
    d.text((W-285,H-92),"PULSENAMA",font=watermark_font,fill=(255,255,255,190),
      stroke_width=2,stroke_fill=(0,0,0,150))
    path=WORK/"complete_poem_page.png"
    layer.save(path)
    return path

def make_mood_music(title, lines):
    """Create an original, royalty-free instrumental bed matched to the poem mood.
    No voice, speech, or text-to-speech is used."""
    profiles = {
        "sad":          {"bpm": 66, "progression": [[0,3,7],[8,0,3],[5,8,0],[3,7,10]], "scale":[0,2,3,5,7,8,10], "brightness":0.45},
        "romantic":     {"bpm": 78, "progression": [[0,4,7],[9,0,4],[5,9,0],[7,11,2]], "scale":[0,2,4,5,7,9,11], "brightness":0.68},
        "peaceful":     {"bpm": 72, "progression": [[0,4,7],[5,9,0],[2,5,9],[7,11,2]], "scale":[0,2,4,5,7,9,11], "brightness":0.58},
        "deep":         {"bpm": 62, "progression": [[0,3,7],[6,10,1],[8,0,3],[3,7,10]], "scale":[0,2,3,5,7,8,10], "brightness":0.40},
        "motivational": {"bpm": 96, "progression": [[0,4,7],[7,11,2],[9,0,4],[5,9,0]], "scale":[0,2,4,5,7,9,11], "brightness":0.82},
        "rain":         {"bpm": 68, "progression": [[0,3,7],[8,0,3],[5,8,0],[3,7,10]], "scale":[0,2,3,5,7,8,10], "brightness":0.48},
        "memories":     {"bpm": 70, "progression": [[0,3,7],[5,8,0],[8,0,3],[3,7,10]], "scale":[0,2,3,5,7,8,10], "brightness":0.46},
    }
    mood = MOOD if MOOD in profiles else "peaceful"
    p = profiles[mood]
    seed_text = title + "|" + "|".join(lines) + "|" + mood
    rng = random.Random(sum((i+1)*ord(c) for i,c in enumerate(seed_text)))
    sample_rate = 22050
    total = int(DURATION * sample_rate)
    beat = 60.0 / p["bpm"]
    bar = beat * 4
    root = 48 if mood in ("sad","deep","rain","memories") else 50
    progression = p["progression"]
    scale = p["scale"]
    melody = []
    for bar_i in range(int(math.ceil(DURATION / bar)) + 1):
        base = root + rng.choice((0, 0, 12))
        degree = rng.choice(scale)
        melody.append((bar_i * bar + rng.uniform(0.05, 0.35), base + degree + 12))
        if rng.random() < 0.55:
            melody.append((bar_i * bar + beat * rng.choice((1, 2, 3)), base + rng.choice(scale) + 12))
    melody.sort()
    out = WORK / "mood_matched_instrumental.wav"
    with wave.open(str(out), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        chunk = bytearray()
        for n in range(total):
            t = n / sample_rate
            bar_i = int(t / bar)
            chord = progression[bar_i % len(progression)]
            chord_notes = [root + x for x in chord]
            # Warm, slowly swelling chord pad.
            pad = 0.0
            for j, midi in enumerate(chord_notes):
                freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
                pad += math.sin(2 * math.pi * freq * t + j * 0.17) * (0.075 if j == 0 else 0.052)
                pad += math.sin(2 * math.pi * (freq * 2.003) * t + j) * 0.008
            # Gentle piano-like plucks, with notes chosen from the mood's scale.
            pluck = 0.0
            for onset, midi in melody:
                age = t - onset
                if 0 <= age < 1.8:
                    freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
                    env = math.exp(-age * (2.8 if mood == "motivational" else 2.0))
                    pluck += (math.sin(2*math.pi*freq*age) + 0.24*math.sin(2*math.pi*freq*2.01*age)) * 0.13 * env
            # A very soft pulse gives uplifting moods movement without overpowering the poem.
            pulse = 0.0
            if mood == "motivational":
                pulse = math.sin(2*math.pi*82*t) * (0.025 * max(0.0, 1.0 - (t % beat)/0.16))
            sample = max(-0.85, min(0.85, pad + pluck + pulse))
            fade_in = min(1.0, t / 0.16)
            fade_out = min(1.0, max(0.0, (DURATION - t) / 2.2))
            sample *= fade_in * fade_out * 0.90
            # Slight stereo width; both channels remain fully instrumental.
            left = int(max(-1.0, min(1.0, sample * 0.96)) * 32767)
            right = int(max(-1.0, min(1.0, sample * 1.04)) * 32767)
            chunk.extend(struct.pack("<hh", left, right))
            if len(chunk) >= 65536:
                wav.writeframesraw(chunk)
                chunk.clear()
        if chunk:
            wav.writeframesraw(chunk)
    print(f"Created original {mood} mood-matched instrumental (no vocals).")
    return out

def render_video(title,lines,bg,music):
    page=text_page_png(title,lines)
    if bg.suffix.lower()==".mp4":
        inputs=["-stream_loop","-1","-i",str(bg),"-loop","1","-i",str(page),"-i",str(music)]
    else:
        inputs=["-loop","1","-i",str(bg),"-loop","1","-i",str(page),"-i",str(music)]
    base="[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.00012,1.06)':d=1:s=1080x1920:fps=24,setsar=1,trim=duration="+str(DURATION)+",setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.45[bg]"
    filters=[base,
      "[1:v]format=rgba,fade=t=in:st=0.20:d=0.55:alpha=1[poem]",
      "[bg][poem]overlay=(W-w)/2:(H-h)/2:enable='between(t,0.15,"+str(DURATION)+")'[vout]",
      "[2:a]volume=1.10,alimiter=limit=0.95,afade=t=in:st=0:d=0.18,afade=t=out:st="+str(max(0,DURATION-3))+":d=3[aout]"]
    cmd=["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),
      "-map","[vout]","-map","[aout]","-t",str(DURATION),"-r",str(FPS),
      "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-s","1080x1920",
      "-c:a","aac","-b:a","160k","-movflags","+faststart",str(OUT)]
    run(cmd)
    Path("poetry_demo.txt").write_text(f"Title: {title}\nMood: {MOOD}\nLanguage: {LANG}\nDuration: {DURATION}s\n\n"+
      "\n".join(lines)+"\n\nBackground: "+BACKGROUND_CREDIT+"\nFull poem displayed with watermark. No voice-over.\n",encoding="utf-8")

def main():
    print(f"Generating {MOOD} / {LANG} / {DURATION}s poetry demo.")
    title,lines=make_poem()
    bg=get_pexels_video()
    if bg is None:
        bg=get_online_image()
    if bg is None:
        raise RuntimeError("No reusable internet image was found. Add PEXELS_API_KEY or retry later; no AI image will be generated.")
    music=make_mood_music(title,lines)
    render_video(title,lines,bg,music)
    print(f"SUCCESS: {OUT} ({OUT.stat().st_size} bytes). No social post was created.")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise
