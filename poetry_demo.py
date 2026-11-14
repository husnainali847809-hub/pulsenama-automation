#!/usr/bin/env python3
"""Standalone, manual-only cinematic poetry demo. Never publishes to Buffer."""
import json, os, re, subprocess, sys, math, random, wave, struct
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 720, 1280, 24
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

def get_pexels_video():
    if not PEXELS:
        print("No PEXELS_API_KEY; using original generated cinematic artwork."); return None
    terms={"sad":"rainy city night rain window","romantic":"romantic sunset lake",
      "motivational":"sunrise mountain nature","deep":"starry night sky","peaceful":"calm ocean waves"}
    r=requests.get("https://api.pexels.com/videos/search",headers={"Authorization":PEXELS},
      params={"query":terms.get(MOOD,"cinematic nature"),"orientation":"portrait","per_page":8},timeout=30)
    r.raise_for_status(); choices=[]
    for v in r.json().get("videos",[]):
        for f in v.get("video_files",[]):
            if f.get("link") and f.get("file_type")=="video/mp4":
                w,h=int(f.get("width") or 0),int(f.get("height") or 0)
                if h>=720 and h>w: choices.append((w*h,f["link"]))
    if not choices: return None
    path=WORK/"background.mp4"
    with requests.get(max(choices)[1],stream=True,timeout=90) as r:
        r.raise_for_status()
        with path.open("wb") as out:
            for chunk in r.iter_content(1024*1024):
                if chunk: out.write(chunk)
    if path.stat().st_size<100000: raise RuntimeError("Pexels video download incomplete.")
    print("Using portrait background footage from Pexels."); return path

def generated_background():
    img=Image.new("RGB",(W,H)); px=img.load()
    for y in range(H):
        for x in range(W):
            glow=max(0,1-(((x-500)/430)**2+((y-400)/520)**2))
            px[x,y]=(int(5+18*glow),int(9+22*glow),int(19+40*glow))
    glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
    if MOOD in ("sad","deep"):
        gd.ellipse((400,220,660,500),fill=(255,190,90,50))
        img=Image.alpha_composite(img.convert("RGBA"),glow.filter(ImageFilter.GaussianBlur(80)))
        d=ImageDraw.Draw(img,"RGBA")
        for i in range(230):
            x=(i*71)%W; y=(i*137)%H
            d.line((x,y,x-9,y+45),fill=(160,190,220,55),width=1)
        d.line((520,320,520,850),fill=(255,210,145,110),width=5)
        d.ellipse((475,275,565,365),fill=(255,220,160,100))
    elif MOOD=="romantic":
        d=ImageDraw.Draw(img,"RGBA"); d.ellipse((420,270,610,460),fill=(255,175,95,190))
        d.rectangle((0,780,W,H),fill=(18,42,62,255))
        for y in range(820,1120,36): d.line((300,y,650,y+10),fill=(255,190,130,45),width=3)
    else:
        d=ImageDraw.Draw(img,"RGBA")
        for i in range(180):
            x=(i*97)%W; y=(i*193)%H
            d.ellipse((x,y,x+3,y+3),fill=(235,235,255,200))
    path=WORK/"background.jpg"; img.convert("RGB").save(path,quality=92); return path

def get_font(size):
    for p in ("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            try: return ImageFont.truetype(p,size)
            except Exception: pass
    return ImageFont.load_default()

def text_png(text,index):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    rtl=LANG.lower()=="urdu"; f=get_font(43 if rtl else 39)
    words=text.split(); rows=[]; current=""
    for word in words:
        candidate=(current+" "+word).strip()
        try: width=d.textlength(candidate,font=f,direction="rtl" if rtl else None)
        except Exception: width=d.textlength(candidate,font=f)
        if width>610 and current: rows.append(current); current=word
        else: current=candidate
    if current: rows.append(current)
    rows=rows[:2]; y=560-len(rows)*31
    for row in rows:
        try:
            kw={"direction":"rtl"} if rtl else {}
            box=d.textbbox((0,0),row,font=f,stroke_width=2,**kw); x=(W-(box[2]-box[0]))//2
            d.text((x+2,y+4),row,font=f,fill=(0,0,0,220),stroke_width=4,stroke_fill=(0,0,0,180),**kw)
            d.text((x,y),row,font=f,fill=(255,250,240,255),stroke_width=1,stroke_fill=(20,20,25,210),**kw)
        except Exception: d.text((50,y),row,font=f,fill=(255,250,240,255))
        y+=65
    p=WORK/f"line_{index}.png"; layer.save(p); return p


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
    inputs=[]
    if bg.suffix==".mp4":
        inputs+=["-stream_loop","-1","-i",str(bg)]
        base="[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,zoompan=z='min(zoom+0.00045,1.10)':d=1:s=720x1280:fps=24,setsar=1,fade=t=in:st=0:d=0.45[bg]"
    else:
        inputs+=["-loop","1","-i",str(bg)]
        base="[0:v]scale=720:1280,zoompan=z='min(zoom+0.00045,1.10)':d=1:s=720x1280:fps=24,setsar=1,fade=t=in:st=0:d=0.45[bg]"
    segment=DURATION/len(lines); overlays=[]
    for i,line in enumerate(lines):
        p=text_png(line,i); inputs+=["-loop","1","-i",str(p)]
        overlays.append((i+1,i*segment,(i+1)*segment))
    cmd=["ffmpeg","-y",*inputs,"-i",str(music)]
    filters=[base]; previous="bg"
    for n,start,end in overlays:
        label=f"v{n}"
        filters.append(f"[{n}:v]format=rgba,fade=t=in:st={start:.3f}:d=0.65:alpha=1[t{n}]")
        filters.append(f"[{previous}][t{n}]overlay=(W-w)/2:(H-h)/2:enable='between(t,{start:.3f},{end:.3f})'[{label}]")
        previous=label
    audio_index=len(lines)+1
    filters.append(f"[{audio_index}:a]volume=1.10,alimiter=limit=0.95,afade=t=in:st=0:d=0.18,afade=t=out:st={max(0,DURATION-3)}:d=3[aout]")
    cmd+=["-filter_complex",";".join(filters),"-map",f"[{previous}]","-map","[aout]","-t",str(DURATION),
      "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
      "-movflags","+faststart",str(OUT)]
    run(cmd)
    Path("poetry_demo.txt").write_text(f"Title: {title}\nMood: {MOOD}\nLanguage: {LANG}\nDuration: {DURATION}s\n\n"+
      "\n".join(lines)+"\n\nDemo only: no Buffer or Facebook publishing.\n",encoding="utf-8")

def main():
    print(f"Generating {MOOD} / {LANG} / {DURATION}s poetry demo.")
    title,lines=make_poem(); bg=get_pexels_video() or generated_background()
    music=make_mood_music(title,lines)
    render_video(title,lines,bg,music)
    print(f"SUCCESS: {OUT} ({OUT.stat().st_size} bytes). No social post was created.")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise
