import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import tempfile
import requests
import os
from io import BytesIO

st.set_page_config(page_title="Text-to-Video App")
st.title("🎬 Text-to-Video Generator")

# Constants
W, H = 720, 1280

# Get API keys from secrets
PEXELS_KEY = st.secrets["PEXELS_KEY"]
UNSPLASH_KEY = st.secrets["UNSPLASH_KEY"]

# Text input
text_input = st.text_area("Enter your message:", "Your text here")

# Mode selection
vid_mode = st.sidebar.radio("Video Source", ["Upload", "Pexels", "Unsplash"])
vid_file = None

# Handle video upload
if vid_mode == "Upload":
    vid_file = st.sidebar.file_uploader("Upload Video", type=["mp4"])
    if not vid_file:
        st.warning("Please upload a video.")
        st.stop()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
        tmp_vid.write(vid_file.read())
        vid_path = tmp_vid.name

# Handle Pexels API
elif vid_mode == "Pexels":
    query = st.sidebar.text_input("Search Pexels", "nature")
    if st.sidebar.button("Get Video"):
        headers = {"Authorization": PEXELS_KEY}
        res = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=1", headers=headers)
        data = res.json()
        if data.get("videos"):
            video_url = data["videos"][0]["video_files"][0]["link"]
            vid_path = tempfile.mktemp(suffix=".mp4")
            with open(vid_path, "wb") as f:
                f.write(requests.get(video_url).content)
        else:
            st.error("No video found.")
            st.stop()

# Handle Unsplash fallback (image only)
elif vid_mode == "Unsplash":
    query = st.sidebar.text_input("Search Unsplash", "landscape")
    if st.sidebar.button("Get Image"):
        res = requests.get(f"https://api.unsplash.com/photos/random?query={query}", headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"})
        data = res.json()
        if data.get("urls"):
            img_url = data["urls"]["regular"]
            image = Image.open(BytesIO(requests.get(img_url).content)).resize((W, H))
            img_clip = ImageClip(image).set_duration(5)
            vid_path = tempfile.mktemp(suffix=".mp4")
            img_clip.write_videofile(vid_path, fps=24)
        else:
            st.error("No image found.")
            st.stop()

# Process video and overlay text
try:
    clip = VideoFileClip(vid_path).without_audio()
    base_vid = clip.resize(height=H if clip.size[1] > clip.size[0] else W)

    # Create text image with PIL
    img = Image.new("RGBA", base_vid.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    text_w, text_h = draw.textsize(text_input, font=font)
    text_position = ((base_vid.size[0] - text_w) // 2, (base_vid.size[1] - text_h) // 2)
    draw.text(text_position, text_input, font=font, fill=(255, 255, 255, 255))

    text_clip = ImageClip(img).set_duration(base_vid.duration)
    final = CompositeVideoClip([base_vid, text_clip])

    # Save to temp file
    out_path = tempfile.mktemp(suffix=".mp4")
    final.write_videofile(out_path, fps=24)

    st.video(out_path)
    with open(out_path, "rb") as f:
        st.download_button("Download Video", f, file_name="final_video.mp4")

except Exception as e:
    st.error(f"Failed to generate video: {e}")
