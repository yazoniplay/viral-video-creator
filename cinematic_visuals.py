"""Original, locally generated motion footage. No stock clips or image-generation APIs."""
import math, re, subprocess, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import VIDEO_WIDTH, VIDEO_HEIGHT

FPS = 60
W, H = VIDEO_WIDTH, VIDEO_HEIGHT
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(size, bold=True):
    p = FONT_BOLD if bold else FONT_REG
    try: return ImageFont.truetype(p, size)
    except OSError: return ImageFont.load_default()

def palette(seed):
    digest = hashlib.sha256(seed.encode("utf-8", "ignore")).digest()
    hue = int.from_bytes(digest[:2], "big") / 65535
    import colorsys
    def c(h, s=.66, v=.92):
        return tuple(int(x*255) for x in colorsys.hsv_to_rgb(h % 1, s, v))
    return c(hue), c(hue+.11, .78, .98), c(hue+.52, .56, .92)

def wrap(draw, text, f, max_width):
    words = str(text).split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0,0), test, font=f)[2] <= max_width: line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def make_scene(topic, scene, index, output, duration=None):
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    seconds = max(1.0, float(duration or scene.get("duration") or 5))
    frames = max(60, int(round(seconds*FPS)))
    purpose = str(scene.get("purpose") or f"Scene {index}").replace("_", " ").strip()
    prompt = str(scene.get("prompt") or purpose)
    seed = f"{topic}|{purpose}|{prompt}|{index}"
    c1,c2,accent = palette(seed)
    digest = hashlib.sha256(seed.encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:4],"big"))
    # Render at half-resolution for rich layered animation, then upscale cleanly.
    rw,rh = W//2,H//2
    yy,xx=np.mgrid[0:rh,0:rw].astype(np.float32)
    u=xx/max(1,rw-1); v=yy/max(1,rh-1)
    base=np.zeros((rh,rw,3),dtype=np.float32)
    # Deep cinematic gradient with moving light fields.
    for k in range(3):
        base[:,:,k]=c1[k]*(1-v)+c2[k]*v
    particles=[]
    for _ in range(72):
        particles.append((rng.uniform(0,1),rng.uniform(0,1),rng.uniform(1.0,4.8),rng.uniform(.15,1.0),rng.uniform(0,math.tau)))
    tmp=output.with_suffix(".frames"); tmp.mkdir(exist_ok=True)
    f_hero=font(64); f_sub=font(26,False); f_index=font(22)
    short_topic=" ".join(re.sub(r"[^\w\s'-]"," ",topic).split())
    words=wrap(ImageDraw.Draw(Image.new("RGB",(1,1))), short_topic, f_hero, W-130)[:3]
    # Give every scene a different visual language; all elements are animated.
    mode=index % 6
    for n in range(frames):
        t=n/FPS
        phase=t/seconds
        drift=.5+.5*math.sin(t*.55+index*.7)
        light1=np.exp(-(((u-(.25+.22*math.sin(t*.42+index)))*1.9)**2+((v-(.30+.16*math.cos(t*.37)))*1.4)**2)*3)
        light2=np.exp(-(((u-(.78+.13*math.cos(t*.31+index)))*1.7)**2+((v-(.69+.12*math.sin(t*.51)))*1.6)**2)*3)
        frame=base.copy()
        for k in range(3):
            frame[:,:,k]+=light1*(accent[k]-c1[k])*.42+light2*(c2[k]-c1[k])*.28
        # Moving contour waves and a subtle film-like grain.
        wave=np.sin(u*(8+index%5)+t*1.25)*np.cos(v*7-t*.8)
        frame += wave[:,:,None]*4
        frame=np.clip(frame,0,255).astype(np.uint8)
        img=Image.fromarray(frame,"RGB").resize((W,H),Image.Resampling.BICUBIC)
        # Add a controlled bloom behind the subject.
        glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow,"RGBA")
        cx=int(W*(.5+.20*math.sin(t*.38+index)))
        cy=int(H*(.39+.12*math.cos(t*.45+index*.4)))
        radius=int(180+90*(.5+.5*math.sin(t*1.1)))
        gd.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=(*accent,30))
        glow=glow.filter(ImageFilter.GaussianBlur(95))
        img=Image.alpha_composite(img.convert("RGBA"),glow)
        d=ImageDraw.Draw(img,"RGBA")
        # Parallax particle field: continuous movement makes the shots feel alive.
        for px,py,size,speed,offset in particles:
            x=int(((px + t*speed*.018 + offset*.05)%1)*W)
            y=int(((py + math.sin(t*.55+offset)*.035)%1)*H)
            r=max(1,int(size*(.7+.3*math.sin(t*2+offset))))
            alpha=int(65+100*(.5+.5*math.sin(t*1.4+offset)))
            d.ellipse((x-r,y-r,x+r,y+r),fill=(*accent,alpha))
        # Scene-specific moving geometry: orbit, perspective grid, rings, bars, or sweeping beam.
        if mode in (0,3):
            for j in range(5):
                rr=int((150+j*105)*(1+.035*math.sin(t*1.3+j)))
                ox=int(W*.5+math.cos(t*.42+j*.48)*W*.16)
                oy=int(H*.47+math.sin(t*.53+j*.57)*H*.06)
                d.ellipse((ox-rr,oy-rr,ox+rr,oy+rr),outline=(*accent,max(25,125-j*16)),width=3 if j else 5)
        elif mode == 1:
            horizon=int(H*.58)
            for j in range(13):
                x=int(j*W/12)
                d.line((W//2,horizon,x,H),fill=(*accent,45),width=2)
            for j in range(9):
                yyline=int(horizon+(j*j+1)*H*.005+((t*80)%70))
                if yyline<H: d.line((0,yyline,W,yyline),fill=(*accent,30),width=2)
        elif mode == 2:
            for j in range(8):
                bw=34+j*5; x=int((j*W/8 + math.sin(t*1.2+j)*55)%W)
                height=int(H*(.12+.22*(.5+.5*math.sin(t*1.7+j*.8))))
                d.rounded_rectangle((x,H*.62-height,x+bw,H*.62),radius=14,fill=(*accent,90),outline=(*accent,180),width=2)
        elif mode == 4:
            sweep=int((phase*1.6%1)*W)
            d.polygon([(sweep-230,0),(sweep-90,0),(sweep+300,H),(sweep+100,H)],fill=(*accent,22))
            d.line((sweep,0,sweep-140,H),fill=(*accent,100),width=4)
        else:
            for j in range(6):
                x=int(W*(.5+.36*math.sin(t*.65+j*.9)))
                y=int(H*(.36+.27*math.cos(t*.8+j*.7)))
                r=24+j*12
                d.line((x-r,y,x+r,y),fill=(*accent,130),width=3)
                d.line((x,y-r,x,y+r),fill=(*accent,130),width=3)
        # Minimal editorial typography, with a live progress line.
        d.rounded_rectangle((58,66,W-58,72),radius=3,fill=(255,255,255,48))
        d.rounded_rectangle((58,66,58+int((W-116)*phase),72),radius=3,fill=(*accent,230))
        d.text((62,92),f"FIELD NOTES  /  {index:02d}",font=f_index,fill=(255,255,255,180))
        # Title rises in and settles instead of remaining a static slide.
        rise=int(34*(1-min(1,phase*4)))
        ty=int(H*.63)+rise
        for j,line in enumerate(words):
            d.text((64,ty+j*76),line,font=f_hero,fill=(255,255,255,248),stroke_width=2,stroke_fill=(0,0,0,80))
        subtitle=purpose.upper()[:68]
        d.text((66,min(H-90,ty+len(words)*78+18)),subtitle,font=f_sub,fill=(*accent,240))
        # Gentle camera push simulated via small crop offset and scale.
        img=img.convert("RGB")
        if mode in (0,2,4):
            zoom=1.0+.018*phase
            zw,zh=int(W/zoom),int(H/zoom)
            left=int((W-zw)*(.35+.3*phase)); top=int((H-zh)*(.45+.1*math.sin(t*.5)))
            img=img.crop((left,top,left+zw,top+zh)).resize((W,H),Image.Resampling.LANCZOS)
        img.save(tmp/f"{n:05d}.jpg",quality=91,optimize=False)
    try:
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),"-i",str(tmp/"%05d.jpg"),
            "-frames:v",str(frames),"-an","-c:v","libx264","-preset","veryfast","-crf","18",
            "-pix_fmt","yuv420p","-r",str(FPS),"-fps_mode","cfr","-movflags","+faststart",str(output)],check=True)
    finally:
        for p in tmp.glob("*.jpg"): p.unlink(missing_ok=True)
        tmp.rmdir()
    return {"path":str(output),"renderer":"original_cinematic_procedural","index":index,"fps":FPS,"frames":frames,"duration":seconds}
