import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION
import requests, os, io, textwrap, tempfile, numpy as np, base64
from gtts import gTTS

# --- Constants ---
W, H = 1080, 1920  # Final video resolution
PREVIEW_W, PREVIEW_H = 360, 640  # Scaled preview size
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TEMP_DIR = tempfile.mkdtemp()
UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")
trans_dur = 1  # Crossfade duration

# Fix for Pillow >= 10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# --- Helpers ---
def wrap_lines(text, draw, font, max_w):
    words, line, lines = text.split(), "", []
    for w in words:
        if draw.textlength(f"{line} {w}", font=font) <= max_w:
            line += f" {w}" if line else w
        else:
            lines.append(line)
            line = w
    if line: lines.append(line)
    return lines

def typewriter_clip(size, text, font, color, duration):
    chars = list(text)
    def make_frame(t):
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        n_chars = min(int(len(chars) * t / duration), len(chars))
        partial = ''.join(chars[:n_chars])
        lines = wrap_lines(partial, draw, font, size[0]-80)
        y = (size[1] - len(lines)*(font.size+10)) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((size[0]-w)//2, y), line, font=font, fill=color)
            y += font.size+10
        return np.array(img.convert("RGB"))
    return VideoClip(make_frame=make_frame, duration=duration)

def static_text_clip(size, text, font, color, duration):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = wrap_lines(text, draw, font, size[0]-80)
    y = (size[1] - len(lines)*(font.size+10)) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((size[0]-w)//2, y), line, font=font, fill=color)
        y += font.size+10
    return ImageClip(np.array(img.convert("RGB"))).set_duration(duration)

# --- Streamlit UI ---
st.set_page_config("Quote Video Maker", layout="wide")
st.title("🎞️ Quote Video Maker – Animated & Merged")

st.sidebar.header("Settings")
vid_file = st.sidebar.file_uploader("Upload a video background", type=["mp4"])
font_size = st.sidebar.slider("Font size", 40, 120, 80)
text_color = st.sidebar.color_picker("Text color", "#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote", 3, 15, 6)
text_anim = st.sidebar.selectbox("Text animation", ["Static", "Typewriter"])
voiceover = st.sidebar.checkbox("Add Voiceover (gTTS)")
voice_lang = st.sidebar.selectbox("Voice Language", ["en", "es", "fr"], disabled=not voiceover)

quotes_raw = st.text_area("Enter quotes (separate each with a blank line)", height=300)

if st.button("Generate Video"):
    with st.spinner("Generating video..."):
        quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
        if not quotes:
            st.error("Please enter at least one quote.")
            st.stop()

        if not vid_file:
            st.error("Please upload a video background.")
            st.stop()

        tmp_path = os.path.join(TEMP_DIR, "bg.mp4")
        with open(tmp_path, "wb") as f:
            f.write(vid_file.read())

        font = ImageFont.truetype(FONT_PATH, font_size)
        bg_video = VideoFileClip(tmp_path).without_audio().resize((W, H))
        clips = []

        for quote in quotes:
            if text_anim == "Typewriter":
                txt_clip = typewriter_clip((W, H), quote, font, text_color, quote_dur)
            else:
                txt_clip = static_text_clip((W, H), quote, font, text_color, quote_dur)

            clip = CompositeVideoClip([
                bg_video.subclip(0, quote_dur),
                txt_clip.set_position("center")
            ])
            clips.append(clip)

        if not clips:
            st.error("No video clips were created. Please check your inputs.")
            st.stop()

        if len(clips) == 1:
            video = clips[0]
        else:
            timeline = []
            current_start = 0
            for idx, c in enumerate(clips):
                if idx == 0:
                    timeline.append(c.set_start(current_start))
                else:
                    timeline.append(c.set_start(current_start).crossfadein(trans_dur))
                current_start += quote_dur - trans_dur
            video = CompositeVideoClip(timeline, size=(W, H)).set_duration(current_start + trans_dur)

        if voiceover:
            tts_path = os.path.join(TEMP_DIR, "voice.mp3")
            gTTS(" ".join(quotes), lang=voice_lang).save(tts_path)
            voice_clip = AudioFileClip(tts_path)
            if voice_clip.duration < video.duration:
                voice_clip = voice_clip.audio_loop(duration=video.duration)
            video = video.set_audio(voice_clip)

        out = os.path.join(TEMP_DIR, "final.mp4")
        video.write_videofile(out, fps=24, preset="ultrafast")

        st.success("Done!")

        # --- Video Preview & Download ---
        video_bytes = open(out, "rb").read()
        encoded_video = base64.b64encode(video_bytes).decode()
        st.markdown(
            f"""
            <video controls style="width: 360px; height: 640px; border-radius: 12px;">
                <source src="data:video/mp4;base64,{encoded_video}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            """,
            unsafe_allow_html=True,
        )
        st.download_button("📥 Download Video", video_bytes, "quote_video.mp4")
