import streamlit as st
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont, ImageColor
import numpy as np
import os, tempfile, textwrap

# Patch for Pillow >=10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Constants
W, H = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

st.title("Quote Video Maker")

# UI
uploaded_file = st.file_uploader("Upload a vertical MP4 video", type="mp4")
quote_text = st.text_area("Enter your quote:", "This is a sample quote.", height=100)
text_color = st.color_picker("Choose text color:", "#FFFFFF")
text_effect = st.selectbox("Select text animation:", ["Static", "Fade In", "Typewriter"])

if uploaded_file and st.button("Generate Video"):
    # Save uploaded video to temp
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "input_video.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_file.read())

    try:
        bg_clip = VideoFileClip(video_path).resize((W, H)).subclip(0, 8)

        # Load font
        font = ImageFont.truetype(FONT_PATH, 80)
        color_rgb = ImageColor.getrgb(text_color)

        def make_text_image(text):
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            lines = textwrap.wrap(text, width=25)
            total_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + 20 * len(lines)
            y = (H - total_height) // 2
            for line in lines:
                w = draw.textlength(line, font=font)
                draw.text(((W - w) // 2, y), line, font=font, fill=color_rgb)
                y += font.size + 20
            return np.array(img)

        if text_effect == "Static":
            txt_img = make_text_image(quote_text)
            txt_clip = ImageClip(txt_img).set_duration(bg_clip.duration)

        elif text_effect == "Fade In":
            txt_img = make_text_image(quote_text)
            txt_clip = ImageClip(txt_img).set_duration(bg_clip.duration).fadein(1)

        elif text_effect == "Typewriter":
            clips = []
            for i in range(1, len(quote_text) + 1):
                img_array = make_text_image(quote_text[:i])
                c = ImageClip(img_array).set_duration(0.1)
                clips.append(c)
            txt_clip = CompositeVideoClip(clips).set_duration(bg_clip.duration)

        txt_clip = txt_clip.set_position("center")

        final = CompositeVideoClip([bg_clip, txt_clip])

        output_path = os.path.join(temp_dir, "output.mp4")
        final.write_videofile(output_path, fps=24, codec="libx264")

        st.video(output_path)
        with open(output_path, "rb") as f:
            st.download_button("Download Video", f, file_name="quote_video.mp4")

    except Exception as e:
        st.error(f"Error: {e}")
