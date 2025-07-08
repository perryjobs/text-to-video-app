import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import os
import textwrap

# --- Constants ---
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# --- UI ---
st.set_page_config(layout="wide")
st.title("🎬 Quote Video Maker – No Black Screen, Centered Text")

uploaded_video = st.file_uploader("Upload vertical MP4 video (9:16)", type=["mp4"])
quote_text = st.text_area("Enter your quote", "Believe in yourself. You're stronger than you think.", height=200)
font_size = st.slider("Font Size", 40, 120, 90)
text_color = st.color_picker("Text Color", "#FFFFFF")
duration_limit = st.slider("Clip Duration (seconds)", 3, 15, 6)

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

    # Create transparent image
    font = ImageFont.truetype(FONT_PATH, font_size)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Wrap text into lines
    max_chars_per_line = 25
    wrapped_lines = []
    for line in quote_text.splitlines():
        wrapped_lines.extend(textwrap.wrap(line, width=max_chars_per_line))

    # Calculate height for vertical centering
    line_heights = [
        draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
        for line in wrapped_lines
    ]
    total_height = sum(line_heights) + (len(wrapped_lines) - 1) * 10
    y = (H - total_height) // 2

    # Draw each line centered
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((W - w) // 2, y), line, font=font, fill=text_color)
        y += h + 10

    # Create text clip
    txt_clip = (ImageClip(np.array(img), ismask=False)
                .set_duration(bg_clip.duration)
                .set_position("center"))

    # Combine
    final = CompositeVideoClip([bg_clip, txt_clip])

    # Export
    output_path = os.path.join(TEMP_DIR, "output.mp4")
    final.write_videofile(output_path, fps=24, preset="ultrafast")

    st.success("✅ Done!")
    st.video(output_path)
    st.download_button("Download", open(output_path, "rb"), "quote_video.mp4")
