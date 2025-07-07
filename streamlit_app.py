import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import requests
from io import BytesIO
from gtts import gTTS
import tempfile
import os

# Monkey patch for Pillow >=10 compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

st.set_page_config(page_title="Quote Video Maker", layout="wide")
st.title("🎬 Quote Video Maker")

# App state
background_source = st.radio("Choose a background type:", ["Image", "Video"])
text = st.text_area("Enter your quote:", height=150)

voiceover_enabled = st.checkbox("Add voiceover with gTTS")
voice_lang = st.selectbox("Voiceover language", ["en", "es", "fr"], index=0) if voiceover_enabled else None

submit = st.button("Generate Video")

font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_size = 60
font_color = (255, 255, 255)
video_size = (1280, 720)
duration = 8

def download_image(url):
    response = requests.get(url)
    return Image.open(BytesIO(response.content)).convert("RGB")

def create_text_clip(text, size, duration):
    def make_frame(t):
        img = Image.new("RGB", size, (0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        text_size = draw.textbbox((0,0), text, font=font)
        text_width = text_size[2] - text_size[0]
        text_height = text_size[3] - text_size[1]
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        draw.text((x, y), text, font=font, fill=font_color)
        return np.array(img)
    return VideoClip(make_frame, duration=duration)

if submit and text:
    with st.spinner("Generating video..."):
        # Prepare background
        if background_source == "Image":
            bg_url = f"https://api.pexels.com/v1/search?query=nature&per_page=1"
            headers = {"Authorization": st.secrets["PEXELS_KEY"]}
            res = requests.get(bg_url, headers=headers)
            img_url = res.json()["photos"][0]["src"]["landscape"]
            img = download_image(img_url).resize(video_size)
            bg_clip = ImageClip(np.array(img)).set_duration(duration)
        else:
            video_url = f"https://api.pexels.com/videos/search?query=nature&per_page=1"
            headers = {"Authorization": st.secrets["PEXELS_KEY"]}
            res = requests.get(video_url, headers=headers)
            video_link = res.json()["videos"][0]["video_files"][0]["link"]
            vid_res = requests.get(video_link)
            temp_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            temp_vid.write(vid_res.content)
            temp_vid.close()
            bg_clip = VideoFileClip(temp_vid.name).resize(video_size).subclip(0, duration)

        # Prepare text
        txt_clip = create_text_clip(text, video_size, duration)

        # Compose video
        final = CompositeVideoClip([bg_clip, txt_clip.set_position('center')])

        # Add voiceover if selected
        if voiceover_enabled:
            tts = gTTS(text, lang=voice_lang)
            tts_fp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tts_fp.name)
            tts_fp.close()
            final = final.set_audio(AudioFileClip(tts_fp.name))

        # Output
        out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        final.write_videofile(out.name, fps=24, preset="ultrafast")

        st.success("✅ Video generated successfully!")
        st.video(out.name)

        # Clean up
        if background_source == "Video":
            os.remove(temp_vid.name)
        if voiceover_enabled:
            os.remove(tts_fp.name)
        os.remove(out.name)
