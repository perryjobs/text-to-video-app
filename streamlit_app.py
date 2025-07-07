import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import os

st.set_page_config(page_title="Motivational Video Maker", layout="centered")
st.title("📽️ Motivational Video Maker")
st.markdown("Create motivational videos with quotes, images, and music — no ImageMagick required!")

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
                # Step 1: Prepare background image
                img = Image.open(image).convert("RGB").resize((720, 1280))
                draw = ImageDraw.Draw(img)

                # Load font (Streamlit Cloud doesn't support custom fonts easily)
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)

                # Wrap and center text
                lines = []
                words = text_input.split()
                while words:
                    line = ''
                    while words and draw.textlength(line + words[0], font=font) < 680:
                        line += words.pop(0) + ' '
                    lines.append(line)
                y_text = (1280 - len(lines) * font_size) // 2
                for line in lines:
                    width = draw.textlength(line, font=font)
                    draw.text(((720 - width) / 2, y_text), line.strip(), font=font, fill=text_color)
                    y_text += font_size + 10

                # Save image
                img.save("frame.png")

                # Step 2: Create video from image
                clip = ImageClip("frame.png").set_duration(video_duration)

                # Step 3: Add music
                with open("bg_music.mp3", "wb") as f:
                    f.write(music.read())
                audio = AudioFileClip("bg_music.mp3").subclip(0, video_duration)
                final = clip.set_audio(audio)
                final.write_videofile("output.mp4", fps=24, codec='libx264', audio_codec='aac')

                st.success("✅ Video created successfully!")
                st.video("output.mp4")

            except Exception as e:
                st.error(f"❌ Error: {e}")
