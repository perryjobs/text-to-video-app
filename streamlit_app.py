# streamlit_app.py (Fixed black screen for video backgrounds)
import streamlit as st
from moviepy.editor import *
import requests, os, io, textwrap, tempfile, numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

# ✅ Monkey patch for Pillow >=10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# ✅ Ensure Pillow version is compatible
if int(PILLOW_VERSION.split('.')[0]) < 10:
    st.error("This app requires Pillow >= 10. Please upgrade Pillow.")
    st.stop()

# --- Constants ---
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SAMPLE_MUSIC_DIR = "sample_music"
TEMP_DIR = tempfile.mkdtemp()
UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

# --- Helpers ---
def fetch_unsplash(keyword):
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    r = requests.get(f"https://api.unsplash.com/photos/random?query={keyword}", headers=headers)
    if r.status_code == 200:
        return requests.get(r.json()["urls"]["regular"]).content
    return None

def fetch_pexels_video(keyword):
    headers = {"Authorization": PEXELS_KEY}
    r = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1", headers=headers)
    if r.status_code == 200 and r.json()["videos"]:
        return r.json()["videos"][0]["video_files"][0]["link"]
    return None

def wrap_lines(text, draw, font, max_w):
    words, line, lines = text.split(), "", []
    for w in words:
        if draw.textlength(f"{line} {w}", font=font) <= max_w:
            line += f" {w}" if line else w
        else:
            lines.append(line); line = w
    if line: lines.append(line)
    return lines

def text_frame(size, text, font, color):
    W, H = size
    img = Image.new("RGB", size, (0, 0, 0)); draw = ImageDraw.Draw(img)
    lines = wrap_lines(text, draw, font, W - 80)
    y = (H - len(lines) * (font.size + 10)) // 2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((W - w) // 2, y), ln, font=font, fill=color)
        y += font.size + 10
    return img

def typewriter_frames(size, text, font, color, duration):
    chars = list(text)
    def make_frame(t):
        i = min(int(len(chars) * t / duration), len(chars))
        partial = ''.join(chars[:i])
        img = Image.new("RGB", size, (0,0,0))
        draw = ImageDraw.Draw(img)
        lines = wrap_lines(partial, draw, font, size[0]-80)
        y = size[1] - len(lines)*(font.size+10) - 40
        for ln in lines:
            w = draw.textlength(ln, font=font)
            draw.text(((size[0]-w)//2, y), ln, font=font, fill=color)
            y += font.size+10
        return np.array(img)
    return VideoClip(make_frame=make_frame, duration=duration)

def animated_text_clip(size, text, font, color, mode, duration):
    if mode == "Typewriter":
        return typewriter_frames(size, text, font, color, duration).set_position("center")
    base_img = text_frame(size, text, font, color)
    base_clip = ImageClip(np.array(base_img)).set_duration(duration)
    if mode == "Ascend":
        return base_clip.set_position(lambda t: ("center", size[1] * (1 - t / duration) - base_img.height / 2))
    elif mode == "Shift":
        return base_clip.set_position(lambda t: (size[0] * (1 - t / duration) - base_img.width / 2, "center"))
    else:
        return base_clip.set_position("center")

# ---------------- Streamlit UI -----------------
st.set_page_config("Quote Video Maker", layout="wide")
st.title("🎞️ Quote Video Maker – Animated & Merged")

st.sidebar.header("Settings")
media_type = st.sidebar.selectbox("Background Media", ["Image", "Video"])
fmt = st.sidebar.selectbox("Format", ["Vertical", "Square"])
W,H = (720,1280) if fmt=="Vertical" else (720,720)

if media_type=="Image":
    img_src = st.sidebar.radio("Image Source", ["Upload","Unsplash"], horizontal=True)
    if img_src=="Upload":
        img_files = st.sidebar.file_uploader("Upload images", accept_multiple_files=True, type=["jpg","jpeg","png"])
    else:
        kw = st.sidebar.text_input("Unsplash keyword", "nature")
        num_imgs = st.sidebar.slider("# random images",1,5,3)
else:
    vid_src = st.sidebar.radio("Video Source", ["Upload","Pexels"], horizontal=True)
    if vid_src=="Upload":
        vid_files = st.sidebar.file_uploader("Upload videos", accept_multiple_files=True, type=["mp4"])
    else:
        kw = st.sidebar.text_input("Pexels keyword", "nature")
        num_vids = st.sidebar.slider("# random videos",1,3,1)

music_mode = st.sidebar.radio("Music", ["Upload","Sample"], horizontal=True)
if music_mode=="Upload":
    music_file = st.sidebar.file_uploader("Upload mp3", type=["mp3"])
else:
    samples=[f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
    sample_choice= st.sidebar.selectbox("Sample track", samples) if samples else None

font_size = st.sidebar.slider("Font size",30,100,60)
text_color = st.sidebar.color_picker("Text color","#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote",3,15,6)
text_anim = st.sidebar.selectbox("Text animation",["None","Typewriter","Ascend","Shift"])
trans_dur = st.sidebar.slider("Transition (sec)",0.5,2.0,1.0,0.1)
voiceover = st.sidebar.checkbox("AI narration (gTTS)")
voice_lang = st.sidebar.selectbox("Voice language",["en","es","fr"],disabled=not voiceover)

quotes_raw = st.text_area("Quotes – separate each by blank line",height=250)

if st.button("Generate Video"):
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Provide at least one quote.")
        st.stop()

    font = ImageFont.truetype(FONT_PATH, font_size)
    clips = []
    bg_clips = []

    if media_type == "Image":
        for _ in range(num_imgs):
            content = fetch_unsplash(kw) if img_src == "Unsplash" else None
            img = Image.open(io.BytesIO(content)) if content else Image.open(img_files[0])
            bg_clips.append(ImageClip(np.array(img.convert("RGB"))).set_duration(quote_dur).resize((W, H)))
    else:
        if vid_src == "Pexels":
            for i in range(num_vids):
                url = fetch_pexels_video(kw)
                if url:
                    path = os.path.join(TEMP_DIR, f"pexels_{i}.mp4")
                    with open(path, "wb") as f:
                        f.write(requests.get(url).content)
                    bg_clips.append(VideoFileClip(path).resize((W, H)).subclip(0, quote_dur))
        else:
            for file in vid_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(file.read())
                    tmp.flush()
                    bg_clips.append(VideoFileClip(tmp.name).resize((W, H)).subclip(0, quote_dur))

    for i, q in enumerate(quotes):
        bg = bg_clips[i % len(bg_clips)].set_duration(quote_dur)
        txt = animated_text_clip((W, H), q, font, text_color, text_anim, quote_dur)
        clips.append(CompositeVideoClip([bg, txt], size=(W, H)))

    if len(clips) == 1:
        video = clips[0]
    else:
        timeline = []
        current_start = 0
        for idx, c in enumerate(clips):
            timeline.append(c.set_start(current_start).crossfadein(trans_dur if idx > 0 else 0))
            current_start += quote_dur - (trans_dur if idx > 0 else 0)
        video = CompositeVideoClip(timeline, size=(W, H)).set_duration(current_start + trans_dur)

    bg_audio = None
    if music_mode == "Upload" and music_file:
        path = os.path.join(TEMP_DIR, "music.mp3")
        open(path, "wb").write(music_file.read())
        bg_audio = AudioFileClip(path).volumex(0.3).audio_loop(duration=video.duration)
    elif music_mode == "Sample" and sample_choice:
        path = os.path.join(SAMPLE_MUSIC_DIR, sample_choice)
        bg_audio = AudioFileClip(path).volumex(0.3).audio_loop(duration=video.duration)

    if voiceover:
        voice_path = os.path.join(TEMP_DIR, "voice.mp3")
        gTTS(" ".join(quotes), lang=voice_lang).save(voice_path)
        voice_clip = AudioFileClip(voice_path)
        if voice_clip.duration < video.duration:
            voice_clip = voice_clip.audio_loop(duration=video.duration)
        final_audio = CompositeAudioClip([voice_clip, bg_audio]) if bg_audio else voice_clip
    else:
        final_audio = bg_audio

    if final_audio:
        video = video.set_audio(final_audio)

    out = os.path.join(TEMP_DIR, "final.mp4")
    video.write_videofile(out, fps=24, preset="ultrafast")
    st.success("Done!")
    st.video(out)
    st.download_button("Download", open(out, "rb"), "video.mp4")
