import streamlit as st
import os
import tempfile
from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, TextClip
from gtts import gTTS
import numpy as np
import textwrap
from PIL import Image, ImageDraw, ImageFont

# Compatibility for PIL resampling filter
try:
    from PIL import Resampling
    RESAMPLE_MODE = Resampling.LANCZOS
except ImportError:
    RESAMPLE_MODE = Image.LANCZOS

# Utility functions
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_text_image(text, font_path, font_size, color, max_width=800):
    lines = textwrap.wrap(text, width=25)
    font = ImageFont.truetype(font_path, font_size)
    # Determine size
    width, height = 0, 0
    line_heights = []
    for line in lines:
        size = font.getsize(line)
        width = max(width, size[0])
        line_heights.append(size[1])
        height += size[1]
    img = Image.new('RGBA', (width + 20, height + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 10
    for i, line in enumerate(lines):
        draw.text((10, y), line, font=font, fill=color)
        y += line_heights[i]
    return img

def static_clip(text, font_path, color, duration, font_size=90):
    img = create_text_image(text, font_path, font_size, color)
    image_path = "/tmp/text.png"
    img.save(image_path)
    return ImageClip(image_path).set_duration(duration)

def fadein_clip(text, font_path, color, duration, font_size=90):
    clip = static_clip(text, font_path, color, duration, font_size)
    return clip.fadein(2)

def typewriter_clip(text, font_path, color, duration, font_size=90):
    # Using TextClip for simplicity; note that font path must be valid
    txt_clip = TextClip(text, fontsize=font_size, font=os.path.basename(font_path), color='white').set_duration(duration)
    return txt_clip

def generate_voice_over(text):
    tts = gTTS(text)
    tmpfile = "/tmp/voice.mp3"
    tts.save(tmpfile)
    return tmpfile

st.set_page_config(layout="wide", page_title="Quote Video Maker")

st.title("🎬 Quote Video Maker")
quote_text = st.text_area("✍️ Enter your quote:", "Believe in yourself. You're stronger than you think.")
font_size = 90
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Adjust if necessary
animation = st.selectbox("🎞️ Select text animation", ["static", "typewriter", "fade in"])
font_color = st.color_picker("🖌️ Choose font color", "#FFFFFF")
video_file = st.file_uploader("📹 Upload vertical video (1080x1920)", type=["mp4", "mov", "webm"])
generate = st.button("Generate Video")

if generate:
    if not video_file:
        st.error("Please upload a background video.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save uploaded video
            bg_path = os.path.join(tmpdir, "bg_input.mp4")
            with open(bg_path, "wb") as f:
                f.write(video_file.read())

            # Step 1: Process background video
            try:
                bg_clip = VideoFileClip(bg_path)
                st.info("Processing background video...")
                # Resize height to 1920 with high-quality resampling
                bg_clip = bg_clip.resize(height=1920, method='lanczos')

                # Crop or pad width to 1080
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

            # Limit duration to 6 seconds
            duration = min(bg_clip.duration, 6)

            # Convert hex color to RGB
            try:
                color_rgb = hex_to_rgb(font_color)
            except Exception as e:
                st.error(f"Invalid color format: {e}")
                st.stop()

            # Step 2: Generate text overlay
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

            # Step 3: Generate voice-over
            st.info("Generating voice-over...")
            try:
                voice_path = generate_voice_over(quote_text)
                voice_audio = AudioFileClip(voice_path).set_duration(duration)
                st.success("Voice-over generated.")
            except Exception as e:
                st.error(f"Error generating voice-over: {e}")
                st.stop()

            # Step 4: Combine all elements
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
