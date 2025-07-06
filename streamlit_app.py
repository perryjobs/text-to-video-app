import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests, os, io, textwrap, tempfile
from gtts import gTTS

# ---------------------------
# CONFIG
# ---------------------------
DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # safe on Streamlit Cloud
SAMPLE_MUSIC_DIR = "sample_music"  # folder for royalty‑free mp3s
TEMP_DIR = tempfile.mkdtemp()

UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def fetch_unsplash_image(keyword: str, w: int, h: int):
    """Return image bytes from Unsplash API or None."""
    if not UNSPLASH_KEY:
        return None
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    url = f"https://api.unsplash.com/photos/random?query={keyword}&orientation=portrait"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            img_url = r.json()["urls"]["regular"]
            return requests.get(img_url, timeout=10).content
    except Exception:
        pass
    return None


def fetch_pexels_video(keyword: str):
    """Return direct MP4 URL or None from Pexels."""
    if not PEXELS_KEY:
        return None
    headers = {"Authorization": PEXELS_KEY}
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=vertical&size=medium&per_page=1"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and r.json().get("videos"):
            return r.json()["videos"][0]["video_files"][0]["link"]
    except Exception:
        pass
    return None


def wrap_text(text: str, max_width: int, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont):
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = f"{current} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def create_frame_image(base_img: Image.Image, quote: str, font, color: str, wm_img, wm_scale: int):
    W, H = base_img.size
    frame = base_img.copy().convert("RGBA")
    draw = ImageDraw.Draw(frame)
    lines = wrap_text(quote, W - 80, draw, font)
    total_h = len(lines) * (font.size + 10)
    y = (H - total_h) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) // 2, y), line, font=font, fill=color)
        y += font.size + 10
    if wm_img:
        wm_w = int(W * wm_scale / 100)
        wm_h = int(wm_w * wm_img.height / wm_img.width)
        wm_resized = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)
        frame.paste(wm_resized, (W - wm_w - 20, H - wm_h - 20), wm_resized)
    path = os.path.join(TEMP_DIR, f"frame_{hash(quote)}.png")
    frame.convert("RGB").save(path)
    return path


def create_text_overlay(size: tuple, quote: str, font, color: str):
    W, H = size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    lines = wrap_text(quote, W - 80, draw, font)
    total_h = len(lines) * (font.size + 10)
    y = (H - total_h) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) // 2, y), line, font=font, fill=color)
        y += font.size + 10
    path = os.path.join(TEMP_DIR, f"overlay_{hash(quote)}.png")
    overlay.save(path)
    return path

# ---------------------------
# STREAMLIT UI
# ---------------------------

st.set_page_config(page_title="Motivational Video Maker", layout="wide")
st.title("📽️ Motivational Video Maker")

# Sidebar controls
st.sidebar.header("🎛 Settings")
media_type = st.sidebar.selectbox("Background Media", ["Image", "Video"])
fmt = st.sidebar.selectbox("Video Format", ["Vertical (720×1280)", "Square (720×720)"])
W, H = (720, 1280) if fmt.startswith("Vertical") else (720, 720)

if media_type == "Image":
    bg_src = st.sidebar.radio("Image Source", ["Upload", "Unsplash"], horizontal=True)
    if bg_src == "Upload":
        bg_file = st.sidebar.file_uploader("Upload background image", type=["png", "jpg", "jpeg"])
    else:
        unsplash_kw = st.sidebar.text_input("Unsplash keyword", "nature")
else:
    vid_src = st.sidebar.radio("Video Source", ["Upload", "Pexels"], horizontal=True)
    if vid_src == "Upload":
        vid_file = st.sidebar.file_uploader("Upload background video", type=["mp4", "mov"])
    else:
        pexels_kw = st.sidebar.text_input("Pexels keyword", "nature")

music_src = st.sidebar.radio("Background Music", ["Upload", "Sample"], horizontal=True)
if music_src == "Upload":
    music_file = st.sidebar.file_uploader("Upload .mp3", type=["mp3"])
else:
    sample_tracks = [f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
    music_choice = st.sidebar.selectbox("Choose sample track", sample_tracks) if sample_tracks else None

wm_file = st.sidebar.file_uploader("Watermark / Logo (optional)", type=["png", "jpg", "jpeg"])
wm_scale = st.sidebar.slider("Watermark size (% of width)", 5, 30, 15)

font_size = st.sidebar.slider("Font Size", 30, 100, 60)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote", 3, 15, 6)
voiceover = st.sidebar.checkbox("AI voice narration (gTTS)")
voice_lang = st.sidebar.selectbox("Voice language", ["en", "es", "fr"], disabled=not voiceover)

# Main input
quotes_raw = st.text_area("Enter quotes (blank line between quotes)", height=250)

if st.button("🎬 Generate Video"):
    # Parse quotes
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Please enter at least one quote.")
        st.stop()

    # -------------------- Acquire Background Media --------------------
    if media_type == "Image":
        if bg_src == "Upload":
            if not bg_file:
                st.error("Upload an image or choose Unsplash."); st.stop()
            bg_bytes = bg_file.read()
        else:
            with st.spinner("Fetching image from Unsplash…"):
                bg_bytes = fetch_unsplash_image(unsplash_kw, W, H)
                if not bg_bytes:
                    st.error("Unsplash fetch failed."); st.stop()
        base_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    else:  # Video
        if vid_src == "Upload":
            if not vid_file:
                st.error("Upload a video or choose Pexels."); st.stop()
            vid_path = os.path.join(TEMP_DIR, "bg_video.mp4")
            with open(vid_path, "wb") as f:
                f.write(vid_file.read())
        else:
            with st.spinner("Fetching video from Pexels…"):
                vid_url = fetch_pexels_video(pexels_kw)
                if not vid_url:
                    st.error("Pexels fetch failed."); st.stop()
                vid_path = os.path.join(TEMP_DIR, "bg_video.mp4")
                with open(vid_path, "wb") as f:
                    f.write(requests.get(vid_url, timeout=20).content)
        try:
            base_vid = VideoFileClip(vid_path).resize(height=H if fmt.startswith("Vertical") else W).without_audio()
            base_vid_w, base_vid_h = base_vid.size
        except Exception as e:
            st.error(f"Video load failed: {e}"); st.stop()

    # -------------------- Music --------------------
    if music_src == "Upload":
        if not music_file:
            st.error("Upload an MP3 or choose sample track."); st.stop()
        music_path = os.path.join(TEMP_DIR, "music.mp3")
        with open(m
