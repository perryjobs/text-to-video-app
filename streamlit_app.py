import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests, os, io, random, textwrap, tempfile
from gtts import gTTS

# ---------------------------
# CONFIG
# ---------------------------
DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Safe on Streamlit Cloud
SAMPLE_MUSIC_DIR = "sample_music"  # put royalty‑free .mp3 files here
TEMP_DIR = tempfile.mkdtemp()

# ---------------------------
# PAGE & SIDEBAR
# ---------------------------
st.set_page_config(page_title="Motivational Video Maker", layout="wide")
st.title("📽️ Motivational Video Maker 2.0")

st.sidebar.header("🎛️ Settings")
fmt = st.sidebar.selectbox("Video Format", ["Vertical (720×1280)", "Square (720×720)"])
W, H = (720, 1280) if fmt.startswith("Vertical") else (720, 720)

# Background image
bg_src = st.sidebar.radio("Background Image", ["Upload", "Unsplash"], horizontal=True)
if bg_src == "Upload":
    bg_file = st.sidebar.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
else:
    unsplash_kw = st.sidebar.text_input("Unsplash keyword", "nature")

# Music
music_src = st.sidebar.radio("Background Music", ["Upload", "Sample"], horizontal=True)
if music_src == "Upload":
    music_file = st.sidebar.file_uploader("Upload .mp3", type=["mp3"])
else:
    sample_tracks = [f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
    music_choice = st.sidebar.selectbox("Choose track", sample_tracks) if sample_tracks else None

# Watermark
wm_file = st.sidebar.file_uploader("Watermark / Logo (optional)", type=["png", "jpg", "jpeg"])
wm_scale = st.sidebar.slider("Watermark scale % (of width)", 5, 30, 15)

# Text & voice
font_size = st.sidebar.slider("Font Size", 30, 100, 60)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote", 3, 15, 6)
voiceover = st.sidebar.checkbox("AI voice narration (gTTS)")
voice_lang = st.sidebar.selectbox("Voice language", ["en", "es", "fr"], disabled=not voiceover)

# ---------------------------
# MAIN INPUTS
# ---------------------------
quotes_raw = st.text_area("Enter quotes (blank line between quotes)", height=200)
if st.button("🎬 Generate Video"):
    # ---------------------------
    # VALIDATION
    # ---------------------------
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Please enter at least one quote (separate with blank lines).")
        st.stop()

    # Background image acquire
    if bg_src == "Upload":
        if not bg_file:
            st.error("Please upload a background image or choose Unsplash."); st.stop()
        bg_bytes = bg_file.read()
    else:
        with st.spinner("Fetching image from Unsplash …"):
            url = f"https://source.unsplash.com/random/{W}x{H}?{unsplash_kw}"
            resp = requests.get(url)
            if resp.status_code != 200:
                st.error("Unsplash fetch failed"); st.stop()
            bg_bytes = resp.content

    # Music acquire
    if music_src == "Upload":
        if not music_file:
            st.error("Please upload an MP3 or choose a sample track."); st.stop()
        music_path = os.path.join(TEMP_DIR, "music.mp3")
        with open(music_path, "wb") as f: f.write(music_file.read())
    else:
        if not sample_tracks:
            st.error("No sample tracks found in sample_music folder."); st.stop()
        music_path = os.path.join(SAMPLE_MUSIC_DIR, music_choice)

    # Prepare background PIL image (resize to format)
    base_bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    # Load watermark if any
    wm_img = None
    if wm_file is not None:
        wm_img = Image.open(wm_file).convert("RGBA")
        wm_w = int(W * wm_scale / 100)
        wm_h = int(wm_w * wm_img.height / wm_img.width)
        wm_img = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)

    # Prepare font
    try:
        font = ImageFont.truetype(DEFAULT_FONT, font_size)
    except IOError:
        font = ImageFont.load_default()

    # ---------------------------
    # BUILD FRAMES PER QUOTE
    # ---------------------------
    clips = []
    for idx, quote in enumerate(quotes):
        frame = base_bg.copy()
        draw = ImageDraw.Draw(frame)
        # Wrap text to fit width
        wrapped = []
        for line in textwrap.wrap(quote, width=30):
            wrapped.append(line)
        total_text_height = len(wrapped) * (font_size + 10)
        y = (H - total_text_height) // 2
        for line in wrapped:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) / 2, y), line, font=font, fill=text_color)
            y += font_size + 10
        # Watermark
        if wm_img:
            frame.paste(wm_img, (W - wm_img.width - 20, H - wm_img.height - 20), wm_img)
        # Save temp frame
        frame_path = os.path.join(TEMP_DIR, f"frame_{idx}.png")
        frame.save(frame_path)
        clips.append(ImageClip(frame_path).set_duration(quote_dur))

    # Add simple crossfade transitions
    video = concatenate_videoclips(clips, method="compose", padding=-1, transition=clips[0].crossfadein(1))

    # ---------------------------
    # AUDIO LAYER
    # ---------------------------
    bg_music = AudioFileClip(music_path).volumex(0.3).set_duration(video.duration)

    if voiceover:
        with st.spinner("Generating voice‑over …"):
            tts_text = " ".join(quotes)
            tts_path = os.path.join(TEMP_DIR, "voice.mp3")
            gTTS(tts_text, lang=voice_lang).save(tts_path)
            voice_clip = AudioFileClip(tts_path)
            # Ensure length match
            if voice_clip.duration < video.duration:
                voice_clip = voice_clip.audio_loop(duration=video.duration)
        final_audio = CompositeAudioClip([bg_music, voice_clip])
    else:
        final_audio = bg_music

    final_video = video.set_audio(final_audio)

    out_path = os.path.join(TEMP_DIR, "output.mp4")
    with st.spinner("Rendering video … this may take a moment."):
        final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac")

    st.success("✅ Video created!")
    st.video(out_path)
    with open(out_path, "rb") as f:
        st.download_button("📥 Download Video", data=f, file_name="motivational_video.mp4", mime="video/mp4")
