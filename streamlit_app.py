import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageColor, __version__ as PILLOW_VERSION
import numpy as np
import tempfile
import os
import textwrap
import base64

# ✅ Monkey patch for Pillow >=10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# --- Constants ---
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# --- UI ---
st.set_page_config(layout="wide")
st.title("🎬 Quote Video Maker – Animated Text Options")

uploaded_video = st.file_uploader("Upload vertical MP4 video (9:16)", type=["mp4"])
quote_text = st.text_area("Enter your quote", "Believe in yourself. You're stronger than you think.", height=200)
font_size = st.slider("Font Size", 40, 120, 90)
text_color = st.color_picker("Text Color", "#FFFFFF")
duration_limit = st.slider("Clip Duration (seconds)", 3, 15, 6)
text_effect = st.selectbox("Text Animation", ["Static", "Fade In", "Typewriter"])

# --- Helper: wrap text lines ---
def wrap_text(text, font, max_chars=25):
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, width=max_chars))
    return lines

# --- Helper: Typewriter animation ---
def typewriter_clip(text, font, color, duration):
    chars = list(text)
    def make_frame(t):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        n_chars = min(int(len(chars) * (t / duration)), len(chars))
        partial = ''.join(chars[:n_chars])
        lines = wrap_text(partial, font)
        line_heights = [font.getbbox(line)[3] for line in lines]
        total_height = sum(line_heights) + (len(lines) - 1) * 10
        y = (H - total_height) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=color)
            y += font.getbbox(line)[3] + 10
        return np.array(img.convert("RGB"))
    return VideoClip(make_frame, duration=duration)

# --- Action ---
if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save uploaded video
    video_path = os.path.join(TEMP_DIR, "input.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    # Load & resize video
    bg_clip = VideoFileClip(video_path).resize((W, H)).subclip(0, duration_limit)

    # Load font
    font = ImageFont.truetype(FONT_PATH, font_size)
    color_rgb = ImageColor.getrgb(text_color)
    color_rgba = color_rgb + (255,)

    if text_effect == "Typewriter":
        txt_clip = typewriter_clip(quote_text, font, color_rgb, bg_clip.duration).set_position("center")

    else:
        # Create transparent RGBA image
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        wrapped_lines = wrap_text(quote_text, font)

        line_heights = [
            draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
            for line in wrapped_lines
        ]
        total_height = sum(line_heights) + (len(wrapped_lines) - 1) * 10
        y = (H - total_height) // 2

        for line in wrapped_lines:
            w = draw.textlength(line, font=font)
            h = draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
            draw.text(((W - w) // 2, y), line, font=font, fill=color_rgba)
            y += h + 10

        np_img = np.array(img.convert("RGB"))
        txt_clip = ImageClip(np_img).set_duration(bg_clip.duration).set_position("center")

        if text_effect == "Fade In":
            txt_clip = txt_clip.fadein(1.0)

    final = CompositeVideoClip([bg_clip, txt_clip])

    # Export
    out = os.path.join(TEMP_DIR, "final.mp4")
    final.write_videofile(out, fps=24, preset="ultrafast")

    st.success("✅ Done!")

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
