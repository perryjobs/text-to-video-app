import streamlit as st
import os
import textwrap
import tempfile
from moviepy.editor import *
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
def create_text_frame(text, font_path, font_size, text_color, size=(1080, 1920)):
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    wrapped = textwrap.fill(text, width=20)
    # Use multiline_textbbox instead of multiline_textsize
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pos = ((size[0] - text_w) // 2, (size[1] - text_h) // 2)
    draw.multiline_text(pos, wrapped, font=font, fill=text_color, align="center")
    return np.array(img)

# Animation types
def static_clip(text, font, color_rgb, duration, size=(1080, 1920)):
    def make_frame(t):
        return create_text_frame(text, font, 90, color_rgb, size)
    return VideoClip(make_frame, duration=duration)

def typewriter_clip(text, font, color_rgb, duration, size=(1080, 1920)):
    def make_frame(t):
        chars = int(len(text) * (t / duration))
        return create_text_frame(text[:chars], font, 90, color_rgb, size)
    return VideoClip(make_frame, duration=duration)

def fadein_clip(text, font, color_rgb, duration, size=(1080, 1920)):
    def make_frame(t):
        alpha = min(t / 1.5, 1)
        rgba_color = tuple(int(c * alpha) for c in color_rgb) + (int(255 * alpha),)
        return create_text_frame(text, font, 90, rgba_color[:3], size)
    return VideoClip(make_frame, duration=duration)

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

        bg_clip = VideoFileClip(bg_path).resize((1080, 1920)).without_audio()
        duration = min(bg_clip.duration, 6)
        color_rgb = hex_to_rgb(font_color)

        if animation == "static":
            txt_clip = static_clip(quote_text, font_path, color_rgb, duration)
        elif animation == "typewriter":
            txt_clip = typewriter_clip(quote_text, font_path, color_rgb, duration)
        elif animation == "fade in":
            txt_clip = fadein_clip(quote_text, font_path, color_rgb, duration)

        final = CompositeVideoClip([bg_clip, txt_clip.set_position("center")]).set_duration(duration)

        output_path = os.path.join(tmpdir, "output.mp4")
        final.write_videofile(output_path, fps=24, codec='libx264', preset="fast", audio=False)

        st.video(output_path)
        st.success("✅ Video created successfully!")
