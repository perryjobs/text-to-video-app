import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import os

# Set final resolution
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()

# Streamlit UI
st.set_page_config(layout="wide")
st.title("🎬 Video + Text Overlay Test")

uploaded_video = st.file_uploader("Upload a vertical MP4 video", type=["mp4"])
quote_text = st.text_input("Enter your quote text", "You are enough.")

if st.button("Generate Quote Video"):
    if not uploaded_video:
        st.error("Please upload a video first.")
        st.stop()

    # Save uploaded video to temp file
    video_path = os.path.join(TEMP_DIR, "input.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    # Load video
    clip = VideoFileClip(video_path).resize((W, H)).subclip(0, 6)

    # Create text image using Pillow
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    img = Image.new("RGB", (W, H), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), quote_text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - w) // 2, (H - h) // 2), quote_text, font=font, fill="white")

    # Turn it into a clip
    txt_clip = ImageClip(np.array(img)).set_duration(clip.duration)

    # Composite
    final = CompositeVideoClip([clip, txt_clip])

    # Output
    output_path = os.path.join(TEMP_DIR, "output.mp4")
    final.write_videofile(output_path, fps=24, preset="ultrafast")
    st.success("✅ Video Generated!")
    st.video(output_path)
    st.download_button("Download", open(output_path, "rb"), "quote_video.mp4")
