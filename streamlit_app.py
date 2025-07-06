import streamlit as st
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
from gtts import gTTS
import os
from PIL import Image
import tempfile
import requests
from io import BytesIO

# Pillow compatibility for newer versions
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Constants
W, H = 720, 1280

# API keys from Streamlit secrets
PEXELS_API_KEY = st.secrets["PEXELS_KEY"]
UNSPLASH_API_KEY = st.secrets["UNSPLASH_KEY"]

# Streamlit UI
st.title("Text-to-Video Generator")

text_input = st.text_area("Enter script/text for video:")

bg_choice = st.radio("Background type", ["Upload", "Pexels", "Unsplash"], horizontal=True)
voiceover = st.checkbox("Add voiceover from text")

vid_file = None

if bg_choice == "Upload":
    vid_file = st.file_uploader("Upload a video file", type=["mp4"])

elif bg_choice == "Pexels":
    query = st.text_input("Search video on Pexels")
    if query:
        headers = {"Authorization": PEXELS_API_KEY}
        res = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=1", headers=headers)
        if res.ok and res.json().get("videos"):
            url = res.json()["videos"][0]["video_files"][0]["link"]
            vid_file = BytesIO(requests.get(url).content)
        else:
            st.warning("No video found on Pexels.")

elif bg_choice == "Unsplash":
    query = st.text_input("Search image on Unsplash")
    if query:
        headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
        res = requests.get(f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait", headers=headers)
        if res.ok:
            url = res.json()["urls"]["regular"]
            img = Image.open(BytesIO(requests.get(url).content)).resize((W, H))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(tmp.name)
            vid_file = tmp.name
        else:
            st.warning("No image found on Unsplash.")

if st.button("Generate Video") and text_input and vid_file:
    try:
        tmp_dir = tempfile.mkdtemp()

        if isinstance(vid_file, BytesIO):
            temp_vid_path = os.path.join(tmp_dir, "temp.mp4")
            with open(temp_vid_path, "wb") as f:
                f.write(vid_file.read())
            vid_path = temp_vid_path
        elif isinstance(vid_file, str):
            vid_path = vid_file
        else:
            vid_path = os.path.join(tmp_dir, vid_file.name)
            with open(vid_path, "wb") as f:
                f.write(vid_file.read())

        # Load video and resize based on orientation
        clip = VideoFileClip(vid_path).without_audio()
        base_vid = clip.resize(height=H if clip.size[1] > clip.size[0] else W)

        # Add text overlay
        text_clip = TextClip(text_input, fontsize=40, color='white', size=base_vid.size, method='caption', align='center', font='Arial')
        text_clip = text_clip.set_duration(base_vid.duration).set_position('center')

        # Voiceover (optional)
        if voiceover:
            tts = gTTS(text=text_input)
            audio_path = os.path.join(tmp_dir, "voice.mp3")
            tts.save(audio_path)
            base_vid = base_vid.set_audio(audio_path)

        # Combine clips
        final = CompositeVideoClip([base_vid, text_clip])
        output_path = os.path.join(tmp_dir, "final.mp4")
        final.write_videofile(output_path, fps=24, codec="libx264")

        st.video(output_path)

    except Exception as e:
        st.error(f"Failed to generate video: {e}")
