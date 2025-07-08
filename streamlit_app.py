import streamlit as st
from moviepy.editor import *
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageColor

import tempfile, os, base64, textwrap

# ✅ Fix for Pillow >=10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# --- Constants ---
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("🎬 Quote Video Maker – No More Black Screens")

uploaded_video = st.file_uploader("Upload vertical MP4 video", type=["mp4"])
quote_text = st.text_area("Enter your quote", "God is within her, she will not fall.", height=200)
font_size = st.slider("Font Size", 40, 120, 90)
text_color = st.color_picker("Text Color", "#FFFFFF")
duration_limit = st.slider("Clip Duration (seconds)", 3, 15, 6)
text_effect = st.selectbox("Text Animation", ["Static", "Fade In", "Typewriter"])

# --- Text Wrap ---
def wrap_text(text, font, max_chars=25):
    lines = []
    for line in text.splitlines():
        lines += textwrap.wrap(line, width=max_chars)
    return lines

# --- Typewriter TextClip ---
def typewriter_clip(text, font, color, duration):
    chars = list(text)

    def make_frame(t):
        img = Image.new("RGB", (W, H), (0, 0, 0))  # No transparency
        draw = ImageDraw.Draw(img)
        n_chars = min(int(len(chars) * (t / duration)), len(chars))
        visible_text = ''.join(chars[:n_chars])
        lines = wrap_text(visible_text, font)
        line_height = font.getbbox("A")[3]
        total_height = len(lines) * (line_height + 10)
        y = (H - total_height) // 2

        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=color)
            y += line_height + 10

        return np.array(img)

    return VideoClip(make_frame, duration=duration)

# --- Process Button ---
if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save uploaded video
    video_path = os.path.join(TEMP_DIR, "input.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    # Load and resize video
    bg_clip = VideoFileClip(video_path).subclip(0, duration_limit).resize((W, H))

    # Font setup
    font = ImageFont.truetype(FONT_PATH, font_size)
    color_rgb = ImageColor.getrgb(text_color)

    if text_effect == "Typewriter":
        txt_clip = typewriter_clip(quote_text, font, color_rgb, bg_clip.duration)

    else:
        # Static or Fade In: use RGBA → convert to RGB safely
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        lines = wrap_text(quote_text, font)
        line_height = font.getbbox("A")[3]
        total_height = len(lines) * (line_height + 10)
        y = (H - total_height) // 2

        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=color_rgb + (255,))
            y += line_height + 10

        # Convert to RGB frame (avoid transparency)
        final_img = img.convert("RGB")
        txt_clip = ImageClip(np.array(final_img)).set_duration(bg_clip.duration).set_position("center")

        if text_effect == "Fade In":
            txt_clip = txt_clip.fadein(1.0)

    # Composite
    final_clip = CompositeVideoClip([bg_clip, txt_clip])
    output_path = os.path.join(TEMP_DIR, "final.mp4")
    final_clip.write_videofile(output_path, fps=24, codec="libx264", preset="ultrafast")

    # Show video
    st.success("✅ Video ready!")
    video_bytes = open(output_path, "rb").read()
    encoded = base64.b64encode(video_bytes).decode()

    st.markdown(
        f"""
        <video controls style="width: 360px; height: 640px; border-radius: 12px;">
            <source src="data:video/mp4;base64,{encoded}" type="video/mp4">
        </video>
        """, unsafe_allow_html=True
    )

    st.download_button("📥 Download", data=video_bytes, file_name="quote_video.mp4")
