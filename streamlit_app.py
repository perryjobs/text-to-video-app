# streamlit_app.py (Clean Rebuild – Fixed Black Screen, 1080x1920)
import streamlit as st
from moviepy.editor import *
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os, io, tempfile, requests, textwrap

# --- Constants ---
W, H = (1080, 1920)  # 9:16 format
FPS = 24
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TEMP_DIR = tempfile.mkdtemp()
SAMPLE_MUSIC_DIR = "sample_music"

# --- Streamlit UI ---
st.set_page_config("📽️ Quote Video Generator", layout="wide")
st.title("🎬 Quote Video Generator with 9:16 Format")

st.sidebar.header("Settings")
media_type = st.sidebar.selectbox("Background Type", ["Video", "Image"])
text_anim = st.sidebar.selectbox("Text Animation", ["None", "Typewriter"])
font_size = st.sidebar.slider("Font Size", 30, 120, 80)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per Quote", 3, 15, 6)
voiceover = st.sidebar.checkbox("AI Voiceover", value=False)
voice_lang = st.sidebar.selectbox("Voice Language", ["en", "es", "fr"], disabled=not voiceover)

# Background Upload
if media_type == "Image":
    img_files = st.sidebar.file_uploader("Upload Image(s)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
else:
    vid_files = st.sidebar.file_uploader("Upload Video(s)", type=["mp4"], accept_multiple_files=True)

# Quotes
quotes_raw = st.text_area("Enter Quotes (Separate with blank lines)", height=250)

if st.button("Generate Video"):
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Please enter at least one quote.")
        st.stop()

    font = ImageFont.truetype(FONT_PATH, font_size)
    clips = []

    # --- Load Backgrounds ---
    bg_clips = []
    if media_type == "Image":
        if not img_files:
            st.error("Please upload image(s).")
            st.stop()
        for f in img_files:
            img = Image.open(f).convert("RGB").resize((W, H))
            bg_clips.append(ImageClip(np.array(img)).set_duration(quote_dur))
    else:
        if not vid_files:
            st.error("Please upload video(s).")
            st.stop()
        for f in vid_files:
            path = os.path.join(TEMP_DIR, f.name)
            with open(path, "wb") as out:
                out.write(f.read())
            bg = VideoFileClip(path).subclip(0, quote_dur).resize((W, H)).without_audio()
            bg_clips.append(bg)

    # --- Helper for text frame ---
    def generate_text_clip(text):
        def make_frame(t):
            partial = text[:int(len(text) * t / quote_dur)] if text_anim == "Typewriter" else text
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            wrapped = textwrap.wrap(partial, width=25)
            y = (H - len(wrapped)*(font.size+10)) // 2
            for line in wrapped:
                w_txt = draw.textlength(line, font=font)
                draw.text(((W - w_txt)//2, y), line, font=font, fill=text_color)
                y += font.size + 10
            return np.array(img.convert("RGB"))

        return VideoClip(make_frame, duration=quote_dur).set_position("center")

    # --- Compose each quote ---
    for i, quote in enumerate(quotes):
        bg = bg_clips[i % len(bg_clips)].set_duration(quote_dur)
        txt_clip = generate_text_clip(quote)
        clips.append(CompositeVideoClip([bg, txt_clip], size=(W, H)))

    final_video = concatenate_videoclips(clips, method="compose")

    # --- Voiceover ---
    if voiceover:
        tts_path = os.path.join(TEMP_DIR, "voice.mp3")
        gTTS(" ".join(quotes), lang=voice_lang).save(tts_path)
        voice_clip = AudioFileClip(tts_path)
        voice_clip = voice_clip.audio_loop(duration=final_video.duration) if voice_clip.duration < final_video.duration else voice_clip
        final_video = final_video.set_audio(voice_clip)

    # --- Export ---
    out_path = os.path.join(TEMP_DIR, "final_output.mp4")
    final_video.write_videofile(out_path, fps=FPS, preset="ultrafast")

    st.success("Done! 🎉")
    st.video(out_path)
    st.download_button("Download Video", open(out_path, "rb"), "quote_video.mp4")
