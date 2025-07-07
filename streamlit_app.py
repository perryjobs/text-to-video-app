# streamlit_app.py
import streamlit as st
import tempfile, os
from moviepy.editor import *
from PIL import ImageFont, ImageDraw, Image
import numpy as np

st.set_page_config(layout="wide")
st.title("🎬 Fix Black Video Background")

W, H = 1080, 1920  # 9:16 resolution

video_file = st.file_uploader("Upload video background", type=["mp4"])
text_input = st.text_area("Enter a quote for your video", "You are stronger than you think.")

if st.button("Generate"):
    if not video_file:
        st.error("Please upload a video.")
        st.stop()

    # Save uploaded video to a temporary file
    temp_video_path = os.path.join(tempfile.gettempdir(), "uploaded_bg.mp4")
    with open(temp_video_path, "wb") as f:
        f.write(video_file.read())

    try:
        bg_clip = VideoFileClip(temp_video_path).resize((W, H)).subclip(0, 5).without_audio()

        # Prepare text image
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        img = Image.new("RGB", (W, H), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = draw.textsize(text_input, font=font)
        draw.text(((W - w) // 2, (H - h) // 2), text_input, font=font, fill="white")

        text_clip = ImageClip(np.array(img)).set_duration(bg_clip.duration)

        final = CompositeVideoClip([bg_clip, text_clip])
        output_path = os.path.join(tempfile.gettempdir(), "final_video.mp4")
        final.write_videofile(output_path, fps=24)

        st.success("Done!")
        st.video(output_path)
        st.download_button("Download Video", open(output_path, "rb"), file_name="quote_video.mp4")

    except Exception as e:
        st.error(f"❌ Error: {e}")
