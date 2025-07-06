import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests, os, io, random, textwrap, tempfile
from gtts import gTTS

# ---------------------------
# CONFIG & CONSTANTS
# ---------------------------
DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # safe font path on Streamlit Cloud
SAMPLE_MUSIC_DIR = "sample_music"  # royalty–free .mp3 files go here
TEMP_DIR = tempfile.mkdtemp()

UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

# ---------------------------
# HELPERS
# ---------------------------

def fetch_unsplash_image(keyword: str, w: int, h: int):
    if not UNSPLASH_KEY:
        return None
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    url = f"https://api.unsplash.com/photos/random?query={keyword}&orientation=portrait"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            img_url = r.json()["urls"]["regular"]
            img = requests.get(img_url, timeout=10)
            return img.content
    except Exception:
        pass
    return None


def fetch_pexels_video(keyword: str):
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


def draw_text_on_image(base_img: Image.Image, quote: str, font: ImageFont.FreeTypeFont, color: str):
    W, H = base_img.size
    txt_overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_overlay)
    wrapped = textwrap.wrap(quote, width=30)
    total_h = len(wrapped) * (font.size + 10)
    y = (H - total_h) // 2
    for line in wrapped:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=color)
        y += font.size + 10
    return Image.alpha_composite(base_img.convert("RGBA"), txt_overlay)


def create_text_overlay_frame(size, quote, font, color):
    W, H = size
    transparent = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(transparent)
    wrapped = textwrap.wrap(quote, width=30)
    total_h = len(wrapped) * (font.size + 10)
    y = (H - total_h) // 2
    for line in wrapped:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=color)
        y += font.size + 10
    path = os.path.join(TEMP_DIR, f"text_overlay_{random.randint(0,99999)}.png")
    transparent.save(path)
    return path

# ---------------------------
# PAGE UI
# ---------------------------
st.set_page_config(page_title="Motivational Video Maker", layout="wide")
st.title("📽️ Motivational Video Maker 3.0")

st.sidebar.header("🎛 Settings")
media_type = st.sidebar.selectbox("Background Media", ["Image", "Video"])
fmt = st.sidebar.selectbox("Video Format", ["Vertical (720×1280)", "Square (720×720)"])
W, H = (720, 1280) if fmt.startswith("Vertical") else (720, 720)

# Background source selection
if media_type == "Image":
    bg_src = st.sidebar.radio("Image Source", ["Upload", "Unsplash"], horizontal=True)
    if bg_src == "Upload":
        bg_file = st.sidebar.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
    else:
        unsplash_kw = st.sidebar.text_input("Unsplash keyword", "nature")
else:
    vid_src = st.sidebar.radio("Video Source", ["Upload", "Pexels"], horizontal=True)
    if vid_src == "Upload":
        vid_file = st.sidebar.file_uploader("Upload video", type=["mp4", "mov"])
    else:
        pexels_kw = st.sidebar.text_input("Pexels keyword", "nature")

# Music controls
music_src = st.sidebar.radio("Background Music", ["Upload", "Sample"], horizontal=True)
if music_src == "Upload":
    music_file = st.sidebar.file_uploader("Upload .mp3", type=["mp3"])
else:
    sample_tracks = [f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
    music_choice = st.sidebar.selectbox("Choose track", sample_tracks) if sample_tracks else None

# Watermark / Logo
wm_file = st.sidebar.file_uploader("Watermark / Logo (optional)", type=["png", "jpg", "jpeg"])
wm_scale = st.sidebar.slider("Watermark scale % of width", 5, 30, 15)

# Text & Narration
font_size = st.sidebar.slider("Font Size", 30, 100, 60)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote", 3, 15, 6)
voiceover = st.sidebar.checkbox("AI voice narration (gTTS)")
voice_lang = st.sidebar.selectbox("Voice language", ["en", "es", "fr"], disabled=not voiceover)

# ---------------------------
# MAIN INPUTS
# ---------------------------
quotes_raw = st.text_area("Enter quotes (blank line between quotes)", height=250)

if st.button("🎬 Generate Video"):
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("⚠️ Please enter at least one quote (blank‑line separated).")
        st.stop()

    # --------------------------- MEDIA ACQUISITION ---------------------------
    if media_type == "Image":
        if bg_src == "Upload":
            if not bg_file:
                st.error("Please upload a background image or choose Unsplash.")
                st.stop()
            bg_bytes = bg_file.read()
        else:  # Unsplash
            with st.spinner("Fetching image from Unsplash …"):
                bg_bytes = fetch_unsplash_image(unsplash_kw, W, H)
                if not bg_bytes:
                    st.error("Unsplash fetch failed — check your keyword or API key.")
                    st.stop()
        base_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    else:  # Video
        if vid_src == "Upload":
            if not vid_file:
                st.error("Please upload a background video or choose Pexels.")
                st.stop()
            vid_path = os.path.join(TEMP_DIR, "bg_video.mp4")
            with open(vid_path, "wb") as f:
                f.write(vid_file.read())
        else:
            with st.spinner("Fetching video from Pexels …"):
                vid_url = fetch_pexels_video(pexels_kw)
                if not vid_url:
                    st.error("Pexels fetch failed — check keyword or API key.")
                    st.stop()
                vid_path = os.path.join(TEMP_DIR, "bg_video.mp4")
                with open(vid_path, "wb") as f:
                    f.write(requests.get(vid_url, timeout=15).content)
        try:
            base_vid = VideoFileClip(vid_path)
            base_vid = base_vid.resize(height=H if fmt.startswith("Vertical") else W)
            base_vid_w, base_vid_h = base_vid.size
        except Exception as e:
            st.error(f"Video load failed: {e}")
            st.stop()

    # --------------------------- MUSIC ---------------------------
    if music_src == "Upload":
        if not music_file:
            st.error("Upload an MP3 or choose sample track.")
            st.stop()
        music_path = os.path.join(TEMP_DIR, "music.mp3")
        with open(music_path, "wb") as f:
            f.write(music_file.read())
    else:
        if not sample_tracks:
            st.error("No sample tracks in sample_music folder.")
            st.stop()
        music_path = os.path.join(SAMPLE_MUSIC_DIR, music_choice)

    # --------------------------- WATERMARK ---------------------------
    wm_img = None
    if wm_file is not None:
        wm_img = Image.open(wm_file).convert("RGBA")

    # --------------------------- FONT ---------------------------
    try:
        font = ImageFont.truetype(DEFAULT_FONT, font_size)
    except IOError:
        font = ImageFont.load_default()

    # --------------------------- BUILD CLIPS ---------------------------
    clips = []
    for idx, quote in enumerate(quotes):
        if media_type == "Image":
            frame = draw_text_on_image(base_img.copy(), quote, font, text_color)
            if wm_img:
                wm_w = int(W * wm_scale / 100)
                wm_h = int(wm_w * wm_img.height / wm_img.width)
                wm_resized = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)
                frame.paste(wm_resized, (W - wm_resized.width - 20, H - wm_resized.height - 20), wm_resized)
            frame_path = os.path.join(TEMP_DIR, f"frame_{idx}.png")
            frame.save(frame_path)
            clip = ImageClip(frame_path).set_duration(quote_dur)
        else:  # video background
            subclip = base_vid.fx(vfx.loop, duration=quote_dur).without_audio()
            txt_overlay_path = create_text_overlay_frame((base_vid_w, base_vid_h), quote, font, text_color)
            txt_clip = ImageClip(txt_overlay_path).set_duration(quote_dur)
            if wm_img:
                wm_w = int(base_vid_w * wm_scale / 100)
                wm_h = int(wm_w * wm_img.height / wm_img.width)
                wm_resized = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)
                wm_path = os.path.join(TEMP_DIR, f"wm_{idx}.png")
                wm_resized.save(wm_path)
                wm_clip = ImageClip(wm_path).set_duration(quote_dur).set_position((base_vid_w - wm_w - 20, base_vid_h - wm_h - 20))
                subclip = CompositeVideoClip([subclip, txt_clip.set_position("center"), wm_clip])
            else:
                subclip = CompositeVideoClip([subclip, txt_clip.set_position("center")])
            clip = subclip
        clips.append(clip)

    final_video = concatenate_videoclips(clips, method="compose", padding=-1, transition=clips[0].crossfadein(1)) if len(clips) > 1 else clips[0]

   # --------------------------- AUDIO ---------------------------
# Combine all video clips (after building `clips`)
final_video = concatenate_videoclips(clips, method="compose", padding=-1, transition=clips[0].crossfadein(1)) if len(clips) > 1 else clips[0]

# Add background music
bg_music = AudioFileClip(music_path).volumex(0.3).set_duration(final_video.duration)

# AI voice-over (optional)
if voiceover:
    with st.spinner("Generating voice-over..."):
        tts_text = " ".join(quotes)
        tts_path = os.path.join(TEMP_DIR, "voice.mp3")
        gTTS(tts_text, lang=voice_lang).save(tts_path)
        voice_clip = AudioFileClip(tts_path)
        if voice_clip.duration < final_video.duration:
            voice_clip = voice_clip.audio_loop(duration=final_video.duration)
    final_audio = CompositeAudioClip([bg_music, voice_clip])
else:
    final_audio = bg_music

# Add audio to video
final_video = final_video.set_audio(final_audio)

