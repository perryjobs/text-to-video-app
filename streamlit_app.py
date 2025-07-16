import streamlit as st
import os
import textwrap
import tempfile
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
import numpy as np

# Monkey patch for Pillow >=10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

st.set_page_config(layout="wide", page_title="Quote Video Maker")

# Utility: Convert hex color to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# Utility: Create a frame with text using PIL
def create_text_image(text, font_path, font_size, text_color, size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    wrapped = textwrap.fill(text, width=20)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pos = ((size[0] - text_w) // 2, (size[1] - text_h) // 2)
    draw.multiline_text(pos, wrapped, font=font, fill=text_color, align="center")
    return np.array(img)

# Animation functions
def static_clip(text, font_path, color_rgb, duration, size=(1080, 1920)):
    img = create_text_image(text, font_path, 90, color_rgb, size)
    return ImageClip(img).set_duration(duration)

def typewriter_clip(text, font_path, color_rgb, duration, size=(1080, 1920)):
    # Placeholder: Implement if needed
    pass

def fadein_clip(text, font_path, color_rgb, duration, size=(1080, 1920)):
    # Placeholder: Implement if needed
    pass

# UI
st.title("🎬 Quote Video Maker")
quote_text = st.text_area("✍️ Enter your quote:", "Believe in yourself. You're stronger than you think.")
font_size = 90
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_color = st.color_picker("🖌️ Choose font color", "#FFFFFF")
animation = st.selectbox("🎞️ Select text animation", ["static", "typewriter", "fade in"])
video_file = st.file_uploader("📹 Upload vertical video (1080x1920)", type=["mp4", "mov", "webm"])
generate = st.button("Generate Video")

# Processing
if generate and video_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        bg_path = os.path.join(tmpdir, "bg.mp4")
        with open(bg_path, "wb") as f:
            f.write(video_file.read())

        # Load and resize background video with aspect ratio preservation
        try:
            bg_clip = VideoFileClip(bg_path)

            # Resize based on height to maintain aspect ratio
            bg_clip = bg_clip.resize(height=1920)

            # Adjust width to 1080 via cropping or padding
            if bg_clip.w < 1080:
                pad_width = 1080 - bg_clip.w
                bg_clip = bg_clip.margin(left=pad_width//2, right=pad_width//2, color=(0, 0, 0))
            elif bg_clip.w > 1080:
                left_crop = (bg_clip.w - 1080) // 2
                right_crop = left_crop + 1080
                bg_clip = bg_clip.crop(x1=left_crop, x2=right_crop)

            bg_clip = bg_clip.without_audio()
        except Exception as e:
            st.error(f"Error processing background video: {e}")
            continue

        # Set duration for text overlay
        duration = min(bg_clip.duration, 6)
        color_rgb = hex_to_rgb(font_color)

        # Generate text clip based on selected animation
        if animation == "static":
            txt_clip = static_clip(quote_text, font_path, color_rgb, duration)
        elif animation == "typewriter":
            # Implement if needed
            txt_clip = static_clip(quote_text, font_path, color_rgb, duration)
        elif animation == "fade in":
            # Implement if needed
            txt_clip = static_clip(quote_text, font_path, color_rgb, duration)

        # Overlay text on background
        final = CompositeVideoClip([bg_clip, txt_clip.set_position("center")]).set_duration(duration)

        output_path = os.path.join(tmpdir, "output.mp4")
        final.write_videofile(output_path, fps=24, codec='libx264', preset="fast", audio=False)

        st.video(output_path)
        st.success("✅ Video created successfully!")
