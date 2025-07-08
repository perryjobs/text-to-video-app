import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageColor
import numpy as np
import tempfile
import os
import base64

# Constants
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

st.set_page_config(layout="wide")
st.title("🎬 Simple Quote Video Maker")

# Inputs
uploaded_video = st.file_uploader("Upload a vertical MP4 video", type=["mp4"])
quote = st.text_area("Quote text", "You are stronger than you think.", height=150)
text_color = st.color_picker("Text color", "#FFFFFF")
font_size = st.slider("Font Size", 30, 120, 80)
duration = st.slider("Clip Duration (sec)", 3, 15, 6)

# Generate
if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save video
    video_path = os.path.join(TEMP_DIR, "input.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    # Load and resize background
    bg_clip = VideoFileClip(video_path).resize((W, H)).subclip(0, duration)

    # Create a transparent image with text
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, font_size)
    color = ImageColor.getrgb(text_color)

    # Wrap text and center it
    lines = quote.split("\n")
    y = H // 2 - (len(lines) * (font.size + 10)) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) // 2, y), line, font=font, fill=color + (255,))
        y += font.size + 10

    # Convert to ImageClip and match duration
    txt_img = np.array(img.convert("RGB"))
    txt_clip = ImageClip(txt_img).set_duration(duration).set_position("center")

    # Combine video and text
    final = CompositeVideoClip([bg_clip, txt_clip])
    output_path = os.path.join(TEMP_DIR, "final.mp4")
    final.write_videofile(output_path, fps=24)

    # Display
    st.success("✅ Video created!")
    video_bytes = open(output_path, "rb").read()
    st.video(video_bytes)
    st.download_button("📥 Download Video", video_bytes, "quote_video.mp4")
