import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageColor
import numpy as np
import tempfile
import os
import textwrap
import base64

# ✅ Patch for Pillow >=10
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
    for para in text.splitlines():
        lines.extend(textwrap.wrap(para, width=max_chars))
    return lines

# --- Typewriter effect ---
def typewriter_clip(text, font, color, duration):
    chars = list(text)

    def make_frame(t):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        n_chars = min(int(len(chars) * (t / duration)), len(chars))
        partial = ''.join(chars[:n_chars])
        lines = wrap_text(partial, font)
        total_height = sum([font.getbbox(line)[3] for line in lines]) + (len(lines) - 1) * 10
        y = (H - total_height) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=color)
            y += font.getbbox(line)[3] + 10
        return np.array(img.convert("RGB"))

    return VideoClip(make_frame, duration=duration)

# --- Generate Video ---
if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save and load video
    video_path = os.path.join(TEMP_DIR, "input.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    bg_clip = VideoFileClip(video_path).resize((W, H)).subclip(0, duration_limit)

    font = ImageFont.truetype(FONT_PATH, font_size)
    color_rgb = ImageColor.getrgb(text_color)
    color_rgba = color_rgb + (255,)

    if text_effect == "Typewriter":
        txt_clip = typewriter_clip(quote_text, font, color_rgb, bg_clip.duration)
    else:
        # Create static/fade text image
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        wrapped = wrap_text(quote_text, font)
        line_heights = [font.getbbox(line)[3] for line in wrapped]
        total_height = sum(line_heights) + (len(wrapped) - 1) * 10
        y = (H - total_height) // 2

        for line in wrapped:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=color_rgba)
            y += font.getbbox(line)[3] + 10

        np_img = np.array(img.convert("RGB"))
        txt_clip = ImageClip(np_img).set_duration(bg_clip.duration).set_position("center")

        if text_effect == "Fade In":
            txt_clip = txt_clip.fadein(1.0)

    # Final composition
    final = CompositeVideoClip([bg_clip, txt_clip])
    output_path = os.path.join(TEMP_DIR, "final.mp4")
    final.write_videofile(output_path, fps=24, preset="ultrafast")

    st.success("✅ Done!")
    video_bytes = open(output_path, "rb").read()
    encoded = base64.b64encode(video_bytes).decode()

    st.markdown(
        f"""
        <video controls style="width: 360px; height: 640px; border-radius: 12px;">
            <source src="data:video/mp4;base64,{encoded}" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True,
    )
    st.download_button("📥 Download Video", video_bytes, "quote_video.mp4")
