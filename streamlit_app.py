import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION
import numpy as np, os, tempfile, io
from gtts import gTTS
import requests

# --- Constants ---
W, H = 1080, 1920  # 9:16 vertical format
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SAMPLE_MUSIC_DIR = "sample_music"
TEMP_DIR = tempfile.mkdtemp()
UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

# --- Compatibility Fixes ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# --- Helpers ---
def wrap_text(text, draw, font, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if draw.textlength(test_line, font=font) <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def typewriter_clip(text, font, duration):
    def make_frame(t):
        chars = int(len(text) * (t / duration))
        partial = text[:chars]
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        lines = wrap_text(partial, draw, font, W - 100)
        y = H // 2 - len(lines) * (font.size + 10) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255))
            y += font.size + 10
        return np.array(img.convert("RGB"))
    return VideoClip(make_frame=make_frame, duration=duration)

def animated_text_clip(text, font, mode, duration):
    if mode == "Typewriter":
        return typewriter_clip(text, font, duration)
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        lines = wrap_text(text, draw, font, W - 100)
        y = H // 2 - len(lines) * (font.size + 10) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255))
            y += font.size + 10
        clip = ImageClip(np.array(img.convert("RGB"))).set_duration(duration)
        if mode == "Ascend":
            return clip.set_position(lambda t: ("center", H * (1 - t / duration)))
        elif mode == "Shift":
            return clip.set_position(lambda t: (W * (1 - t / duration), "center"))
        else:
            return clip.set_position("center")

# --- Streamlit UI ---
st.set_page_config("Quote Video Maker", layout="wide")
st.title("🎞️ Quote Video Maker")

media_type = st.sidebar.selectbox("Media Type", ["Video"])
text_anim = st.sidebar.selectbox("Text Animation", ["None", "Typewriter", "Ascend", "Shift"])
font_size = st.sidebar.slider("Font Size", 30, 100, 70)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
quote_dur = st.sidebar.slider("Quote Duration (s)", 3, 15, 6)
transition_dur = st.sidebar.slider("Transition (s)", 0.5, 2.0, 1.0)

voiceover = st.sidebar.checkbox("Add voice narration")
lang = st.sidebar.selectbox("Voice Language", ["en", "es", "fr"], disabled=not voiceover)

music_file = st.sidebar.file_uploader("Background Music (optional)", type=["mp3"])
video_files = st.sidebar.file_uploader("Upload Video Backgrounds", accept_multiple_files=True, type=["mp4"])

quotes_input = st.text_area("Enter quotes (one per paragraph)", height=200)

if st.button("🎬 Generate Video"):
    quotes = [q.strip() for q in quotes_input.split("\n\n") if q.strip()]
    if not quotes or not video_files:
        st.error("Please upload background videos and enter at least one quote.")
        st.stop()

    font = ImageFont.truetype(FONT_PATH, font_size)
    bg_clips = []

    for file in video_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tempf:
            tempf.write(file.read())
            clip = VideoFileClip(tempf.name).subclip(0, quote_dur).resize((W, H)).without_audio()
            bg_clips.append(clip)

    final_clips = []
    for i, quote in enumerate(quotes):
        bg = bg_clips[i % len(bg_clips)].copy().set_duration(quote_dur)
        txt = animated_text_clip(quote, font, text_anim, quote_dur).set_duration(quote_dur)
        comp = CompositeVideoClip([bg, txt.set_position("center")], size=(W, H))
        final_clips.append(comp)

    timeline = []
    current_start = 0
    for idx, clip in enumerate(final_clips):
        clip = clip.set_start(current_start)
        if idx != 0:
            clip = clip.crossfadein(transition_dur)
        timeline.append(clip)
        current_start += quote_dur - transition_dur

    final_video = CompositeVideoClip(timeline, size=(W, H)).set_duration(current_start + transition_dur)

    if music_file:
        music_path = os.path.join(TEMP_DIR, "bg.mp3")
        with open(music_path, "wb") as f:
            f.write(music_file.read())
        music = AudioFileClip(music_path).volumex(0.3).audio_loop(duration=final_video.duration)
    else:
        music = None

    if voiceover:
        tts_path = os.path.join(TEMP_DIR, "tts.mp3")
        gTTS(" ".join(quotes), lang=lang).save(tts_path)
        voice = AudioFileClip(tts_path)
        if voice.duration < final_video.duration:
            voice = voice.audio_loop(duration=final_video.duration)
        final_audio = CompositeAudioClip([voice, music]) if music else voice
    else:
        final_audio = music

    if final_audio:
        final_video = final_video.set_audio(final_audio)

    out_path = os.path.join(TEMP_DIR, "final.mp4")
    final_video.write_videofile(out_path, fps=24, preset="ultrafast")
    st.success("✅ Video created!")
    st.video(out_path)
    st.download_button("Download Video", open(out_path, "rb"), "quote_video.mp4")
