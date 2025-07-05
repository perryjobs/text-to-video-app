import streamlit as st
from moviepy.editor import *
from PIL import Image
import os

st.set_page_config(page_title="Motivational Video Maker", layout="centered")
st.title("📽️ Motivational Video Maker")
st.markdown("Create simple quote/reel videos with text, background image, and music.")

# Inputs
text_input = st.text_area("✍️ Enter Your Quote or Message", height=150)
image = st.file_uploader("🖼️ Upload Background Image", type=["png", "jpg", "jpeg"])
music = st.file_uploader("🎵 Upload Background Music", type=["mp3"])

font_size = st.slider("Font Size", 30, 100, 60)
text_color = st.color_picker("Text Color", "#FFFFFF")
video_duration = st.slider("Video Duration (seconds)", 5, 30, 10)

if st.button("🎬 Generate Video"):
    if not text_input or not image or not music:
        st.error("Please provide all required inputs.")
    else:
        with st.spinner("Creating your video..."):
            try:
                # Save uploaded files
                image_path = "resized_bg_image.png"
                music_path = "bg_music.mp3"

                # Resize image using Pillow before passing to moviepy
                pil_img = Image.open(image)
                pil_img = pil_img.resize((720, 1280), resample=Image.Resampling.LANCZOS)
                pil_img.save(image_path)

                with open(music_path, "wb") as f:
                    f.write(music.read())

                # Create video
                clip = ImageClip(image_path).set_duration(video_duration)
                txt_clip = (TextClip(text_input, fontsize=font_size, color=text_color, size=clip.size, method='caption')
                            .set_duration(video_duration)
                            .set_position('center'))

                audio = AudioFileClip(music_path).subclip(0, video_duration)
                final = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
                final.write_videofile("output.mp4", fps=24, codec='libx264', audio_codec='aac')

                st.success("Video created successfully!")
                st.video("output.mp4")

            except Exception as e:
                st.error(f"❌ Error: {e}")
