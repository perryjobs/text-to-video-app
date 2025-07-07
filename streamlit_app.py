import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import os

# Final resolution
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()

st.set_page_config(layout="wide")
st.title("🛠️ Fixing Black Screen – Transparent Text on Video")

uploaded_video = st.file_uploader("Upload vertical MP4 video (9:16)", type=["mp4"])
quote_text = st.text_input("Enter quote", "Believe in yourself.")

if st.button("Generate"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save video
    video_path = os.path.join(TEMP_DIR, "input.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())

    # Load video
    bg_clip = VideoFileClip(video_path).resize((W, H)).subclip(0, 6)

    # Transparent image for text overlay
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Centered text
    lines = quote_text.split("\n")
    total_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines])
    y = (H - total_height) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += h + 10

    # Convert to clip
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
