#!/usr/bin/env python3
"""Standalone, manual-only cinematic poetry demo. Never publishes to Buffer."""
import json, os, re, subprocess, sys
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
            raw=re.sub(r"^```(?:json)?\\s*","",raw,flags=re.I)
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

def render_video(title,lines,bg):
    inputs=[]
    if bg.suffix==".mp4":
        inputs+=["-stream_loop","-1","-i",str(bg)]
        base="[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24[bg]"
    else:
        inputs+=["-loop","1","-i",str(bg)]
        base="[0:v]scale=720:1280,zoompan=z='min(zoom+0.00035,1.08)':d=1:s=720x1280:fps=24,setsar=1[bg]"
    segment=DURATION/len(lines); overlays=[]
    for i,line in enumerate(lines):
        p=text_png(line,i); inputs+=["-loop","1","-i",str(p)]
        overlays.append((i+1,i*segment,(i+1)*segment))
    cmd=["ffmpeg","-y",*inputs,"-f","lavfi","-i",f"sine=frequency=196:sample_rate=44100:duration={DURATION}"]
    filters=[base]; previous="bg"
    for n,start,end in overlays:
        label=f"v{n}"
        filters.append(f"[{n}:v]format=rgba,fade=t=in:st={start:.3f}:d=0.65:alpha=1[t{n}]")
        filters.append(f"[{previous}][t{n}]overlay=(W-w)/2:(H-h)/2:enable='between(t,{start:.3f},{end:.3f})'[{label}]")
        previous=label
    audio_index=len(lines)+1
    filters.append(f"[{audio_index}:a]volume=0.035,lowpass=f=700,afade=t=in:st=0:d=2,afade=t=out:st={max(0,DURATION-3)}:d=3[aout]")
    cmd+=["-filter_complex",";".join(filters),"-map",f"[{previous}]","-map","[aout]","-t",str(DURATION),
      "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
      "-movflags","+faststart",str(OUT)]
    run(cmd)
    Path("poetry_demo.txt").write_text(f"Title: {title}\nMood: {MOOD}\nLanguage: {LANG}\nDuration: {DURATION}s\n\n"+
      "\n".join(lines)+"\n\nDemo only: no Buffer or Facebook publishing.\n",encoding="utf-8")

def main():
    print(f"Generating {MOOD} / {LANG} / {DURATION}s poetry demo.")
    title,lines=make_poem(); bg=get_pexels_video() or generated_background()
    render_video(title,lines,bg)
    print(f"SUCCESS: {OUT} ({OUT.stat().st_size} bytes). No social post was created.")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise
