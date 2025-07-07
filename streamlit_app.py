# streamlit_app.py (v6 – Cleaned syntax, proper BG loading, transitions)
import streamlit as st
from moviepy.editor import *
import requests, os, io, textwrap, tempfile, numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

# --- Pillow / MoviePy compatibility patch ----------------
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# --- Constants ------------------------------------------
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SAMPLE_MUSIC_DIR = "sample_music"
TEMP_DIR = tempfile.mkdtemp()
UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

# ------------------------------------------------ Helpers

def fetch_unsplash(keyword):
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    r = requests.get(f"https://api.unsplash.com/photos/random?query={keyword}", headers=headers, timeout=10)
    if r.status_code == 200:
        return requests.get(r.json()["urls"]["regular"], timeout=10).content
    return None

def fetch_pexels_video(keyword):
    headers = {"Authorization": PEXELS_KEY}
    r = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1", headers=headers, timeout=10)
    if r.status_code == 200 and r.json().get("videos"):
        return r.json()["videos"][0]["video_files"][0]["link"]
    return None

def wrap_lines(text, draw, font, max_w):
    words, line, lines = text.split(), "", []
    for w in words:
        trial = f"{line} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def text_frame(size, text, font, color):
    W, H = size
    img = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(img)
    lines = wrap_lines(text, draw, font, W-80)
    y = (H - len(lines)*(font.size+10))//2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((W-w)//2, y), ln, font=font, fill=color)
        y += font.size+10
    return img.convert("RGB")

def typewriter_clip(size, text, font, color, duration):
    chars = list(text)
    def make_frame(t):
        i = min(int(len(chars)*t/duration), len(chars))
        partial = ''.join(chars[:i])
        img = Image.new("RGBA", size, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        lines = wrap_lines(partial, draw, font, size[0]-80)
        y = size[1] - len(lines)*(font.size+10) - 40
        for ln in lines:
            w = draw.textlength(ln, font=font)
            draw.text(((size[0]-w)//2, y), ln, font=font, fill=color)
            y += font.size+10
        return np.array(img.convert("RGB"))
    return VideoClip(make_frame=make_frame, duration=duration).set_position(("center","bottom"))

def animated_text(size, text, font, color, mode, duration):
    if mode == "Typewriter":
        return typewriter_clip(size, text, font, color, duration)
    base = text_frame(size, text, font, color)
    clip = ImageClip(np.array(base)).set_duration(duration)
    if mode == "Ascend":
        return clip.set_position(lambda t: ("center", size[1]*(1-t/duration)-base.height/2))
    if mode == "Shift":
        return clip.set_position(lambda t: (size[0]*(1-t/duration)-base.width/2, "center"))
    return clip.set_position("center")

# ---------------------------- UI ------------------------
st.set_page_config(page_title="Quote Video Maker", layout="wide")
st.title("🎬 Quote Video Maker")

st.sidebar.header("Settings")
media_type = st.sidebar.selectbox("Media Type", ["Image","Video"])
fmt = st.sidebar.selectbox("Format", ["Vertical","Square"])
W,H = (720,1280) if fmt=="Vertical" else (720,720)

if media_type=="Image":
    img_src = st.sidebar.radio("Image Source", ["Upload","Unsplash"], horizontal=True)
    if img_src=="Upload":
        img_files = st.sidebar.file_uploader("Upload images", accept_multiple_files=True, type=["jpg","jpeg","png"])
    else:
        kw_img = st.sidebar.text_input("Unsplash keyword", "nature")
        num_imgs = st.sidebar.slider("# images",1,5,3)
else:
    vid_src = st.sidebar.radio("Video Source", ["Upload","Pexels"], horizontal=True)
    if vid_src=="Upload":
        vid_files = st.sidebar.file_uploader("Upload videos", accept_multiple_files=True, type=["mp4"])
    else:
        kw_vid = st.sidebar.text_input("Pexels keyword", "nature")
        num_vids = st.sidebar.slider("# videos",1,3,1)

music_mode = st.sidebar.radio("Music", ["Upload","Sample"], horizontal=True)
if music_mode=="Upload":
    music_file = st.sidebar.file_uploader("Upload mp3", type=["mp3"])
else:
    samples=[f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
    sample_choice = st.sidebar.selectbox("Sample track", samples) if samples else None

font_size = st.sidebar.slider("Font size",30,100,60)
text_color = st.sidebar.color_picker("Text color","#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote",3,15,6)
text_anim = st.sidebar.selectbox("Text animation",["None","Typewriter","Ascend","Shift"])
trans_dur = st.sidebar.slider("Transition (sec)",0.5,2.0,1.0,0.1)
voiceover = st.sidebar.checkbox("AI narration")
voice_lang = st.sidebar.selectbox("Voice language",["en","es","fr"],disabled=not voiceover)

quotes_raw = st.text_area("Quotes (blank line separated)", height=250)

if st.button("Generate Video"):
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Enter at least one quote."); st.stop()

    font = ImageFont.truetype(FONT_PATH, font_size)

    # -------- Load BG clips ----------
    bg_clips = []
    if media_type == "Image":
        if img_src == "Upload":
            if not img_files: st.error("Upload images"); st.stop()
            for f in img_files:
                img = Image.open(f).convert("RGB").resize((W,H))
                bg_clips.append(ImageClip(np.array(img)).set_duration(quote_dur))
        else:
            for _ in range(num_imgs):
                data = fetch_unsplash(kw_img)
                if data:
                    img = Image.open(io.BytesIO(data)).convert("RGB").resize((W,H))
                    bg_clips.append(ImageClip(np.array(img)).set_duration(quote_dur))
    else:
        if vid_src == "Upload":
            if not vid_files: st.error("Upload videos"); st.stop()
            for f in vid_files:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                tmp.write(f.read()); tmp.close()
                bg_clips.append(VideoFileClip(tmp.name).subclip(0,quote_dur).without_audio().on_color(size=(W,H), pos="center"))
        else:
            for i in range(num_vids):
                link = fetch_pexels_video(kw_vid)
                if link:
                    path = os.path.join(TEMP_DIR, f"pexels_{i}.mp4")
                    with open(path,"wb") as fp: fp.write(requests.get(link, timeout=15).content)
                    bg_clips.append(VideoFileClip(path).subclip(0,quote_dur).without_audio().on_color(size=(W,H), pos="center"))

    if not bg_clips:
        st.error("No background media loaded."); st.stop()

    # -------- Build quote clips ---------
