import streamlit as st
import os
import textwrap
import tempfile
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, AudioFileClip
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Monkey patch for Pillow >=10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

st.set_page_config(layout="wide", page_title="Quote Video Maker")

# Utility functions (same as before)
# ... [include all utility functions from previous code: hex_to_rgb, create_text_image, static_clip, fadein_clip, typewriter_clip, generate_voice_over] ...

# Main UI
st.title("🎬 Quote Video Maker")
quote_text = st.text_area("✍️ Enter your quote:", "Believe in yourself. You're stronger than you think.")
font_size = 90
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_color = st.color_picker("🖌️ Choose font color", "#FFFFFF")
animation = st.selectbox("🎞️ Select text animation", ["static", "typewriter", "fade in"])
video_file = st.file_uploader("📹 Upload vertical video (1080x1920)", type=["mp4", "mov", "webm"])
generate = st.button("Generate Video")

if generate:
    # Step 1: Upload & process background video
    if not video_file:
        st.error("Please upload a background video.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save uploaded video
            bg_path = os.path.join(tmpdir, "bg_input.mp4")
            with open(bg_path, "wb") as f:
                f.write(video_file.read())

            # Load and resize background video
            try:
                bg_clip = VideoFileClip(bg_path)
                st.info("Processing background video...")
                bg_clip = bg_clip.resize(height=1920)

                if bg_clip.w < 1080:
                    pad_width = 1080 - bg_clip.w
                    bg_clip = bg_clip.margin(left=pad_width//2, right=pad_width//2, color=(0, 0, 0))
                elif bg_clip.w > 1080:
                    left_crop = (bg_clip.w - 1080) // 2
                    right_crop = left_crop + 1080
                    bg_clip = bg_clip.crop(x1=left_crop, x2=right_crop)

                bg_clip = bg_clip.without_audio()
                st.success("Background video processed.")
            except Exception as e:
                st.error(f"Error processing background video: {e}")
                st.stop()

            duration = min(bg_clip.duration, 6)
            color_rgb = hex_to_rgb(font_color)

            # Step 2: Generate text overlay clip based on selected animation
            st.info("Generating text overlay...")
            try:
                if animation == "static":
                    txt_clip = static_clip(quote_text, font_path, color_rgb, duration)
                elif animation == "typewriter":
                    txt_clip = typewriter_clip(quote_text, font_path, color_rgb, duration)
                elif animation == "fade in":
                    txt_clip = fadein_clip(quote_text, font_path, color_rgb, duration)
                else:
                    txt_clip = static_clip(quote_text, font_path, color_rgb, duration)
                st.success("Text overlay created.")
            except Exception as e:
                st.error(f"Error creating text overlay: {e}")
                st.stop()

            # Step 3: Generate voice-over audio
            st.info("Generating voice-over...")
            try:
                voice_path = generate_voice_over(quote_text)
                voice_audio = AudioFileClip(voice_path).set_duration(duration)
                st.success("Voice-over generated.")
            except Exception as e:
                st.error(f"Error generating voice-over: {e}")
                st.stop()

            # Step 4: Combine everything
            st.info("Combining elements into final video...")
            try:
                final = CompositeVideoClip([bg_clip, txt_clip.set_position("center")]).set_duration(duration)
                final = final.set_audio(voice_audio)

                output_path = os.path.join(tmpdir, "final_output.mp4")
                final.write_videofile(output_path, fps=24, codec='libx264', preset="fast", audio_codec='aac')
                st.video(output_path)
                st.success("🎉 Video created successfully!")
            except Exception as e:
                st.error(f"Error creating final video: {e}")
