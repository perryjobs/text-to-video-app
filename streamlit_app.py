import streamlit as st
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import numpy as np
import os

# Ensure ffmpeg is available for moviepy
os.environ["IMAGEIO_FFMPEG_EXE"] = "ffmpeg"

from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    ImageClip,
    CompositeVideoClip,
    crossfadein,
    crossfadeout
)

# --- Streamlit UI ---
st.set_page_config(page_title="Text-to-Video App")
st.title("🎬 Text-to-Video Generator")

# Constants
W, H = 720, 1280

# API Keys from secrets
PEXELS_KEY = st.secrets["PEXELS_KEY"]
UNSPLASH_KEY = st.secrets["UNSPLASH_KEY"]

# Input: Text to overlay
text_input = st.text_area("Enter your message:", "Your text here")

# Select mode
vid_mode = st.sidebar.radio("Video Source", ["Upload", "Pexels", "Unsplash"])
num_clips = st.sidebar.slider("Number of Clips", min_value=1, max_value=5, value=3)
clips = []

# Dissolve transition function
def combine_with_dissolve(clips, duration=1):
    combined = clips[0]
    for clip in clips[1:]:
        combined = concatenate_videoclips([
            combined.crossfadeout(duration),
            clip.crossfadein(duration)
        ], method="compose")
    return combined

# --- Fetch from Pexels ---
if vid_mode == "Pexels":
    query = st.sidebar.text_input("Search Pexels", "nature")
    if st.sidebar.button("Get Videos"):
        headers = {"Authorization": PEXELS_KEY}
        res = requests.get(
            f"https://api.pexels.com/videos/search?query={query}&per_page={num_clips}",
            headers=headers
        )
        data = res.json()
        videos = data.get("videos", [])
        if not videos:
            st.error("No videos found.")
            st.stop()

        used_urls = set()

        for video in videos:
            video_files = sorted(video["video_files"], key=lambda v: v["height"], reverse=True)
            mp4_file = next((v for v in video_files if v["file_type"] == "video/mp4"), None)
            if mp4_file:
                video_url = mp4_file["link"]
                if video_url in used_urls:
                    continue
                used_urls.add(video_url)

                vid_temp = tempfile.mktemp(suffix=".mp4")
                with open(vid_temp, "wb") as f:
                    f.write(requests.get(video_url).content)
                clip = VideoFileClip(vid_temp).without_audio().resize(height=H)
                clips.append(clip)

# --- Fetch from Unsplash ---
elif vid_mode == "Unsplash":
    query = st.sidebar.text_input("Search Unsplash", "landscape")
    if st.sidebar.button("Get Images"):
        for _ in range(num_clips):
            res = requests.get(
                f"https://api.unsplash.com/photos/random?query={query}",
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
            )
            data = res.json()
            if data.get("urls"):
                img_url = data["urls"]["regular"]
                image = Image.open(BytesIO(requests.get(img_url).content)).resize((W, H))
                img_clip = ImageClip(np.array(image)).set_duration(5)
                clips.append(img_clip)
            else:
                st.warning("One or more images could not be retrieved.")

# --- Upload multiple videos ---
elif vid_mode == "Upload":
    uploaded_files = st.sidebar.file_uploader("Upload Videos", type=["mp4"], accept_multiple_files=True)
    if not uploaded_files:
        st.warning("Please upload one or more videos.")
        st.stop()
    for vid_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
            tmp_vid.write(vid_file.read())
            clip = VideoFileClip(tmp_vid.name).without_audio().resize(height=H)
            clips.append(clip)

# --- Combine and Render ---
if clips:
    try:
        final = combine_with_dissolve(clips, duration=1)

        # Text Overlay
        img = Image.new("RGBA", final.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        bbox = draw.textbbox((0, 0), text_input, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_position = ((final.size[0] - text_w) // 2, (final.size[1] - text_h) // 2)
        draw.text(text_position, text_input, font=font, fill=(255, 255, 255, 255))

        text_clip = ImageClip(np.array(img)).set_duration(final.duration)
        composed = CompositeVideoClip([final, text_clip])

        # Output
        out_path = tempfile.mktemp(suffix=".mp4")
        composed.write_videofile(out_path, fps=24)

        st.video(out_path)
        with open(out_path, "rb") as f:
            st.download_button("Download Video", f, file_name="final_video.mp4")

    except Exception as e:
        st.error(f"Failed to generate video: {e}")
else:
    st.info("Please select or upload videos/images to begin.")
