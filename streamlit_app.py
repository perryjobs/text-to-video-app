import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import textwrap
import numpy as np
import subprocess
import shutil
import uuid

# --- Constants ---
W, H = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# --- Setup ---
st.set_page_config(layout="centered")
st.title("🎬 Quote Video Maker (No MoviePy!)")

# --- Inputs ---
uploaded_video = st.file_uploader("📤 Upload Vertical MP4 Video (9:16)", type=["mp4"])
quote_text = st.text_area("✍️ Enter your quote", "Believe in yourself.\nYou're stronger than you think.", height=150)
font_size = st.slider("🔠 Font Size", 30, 120, 90)
text_color = st.color_picker("🎨 Text Color", "#FFFFFF")
duration = st.slider("🎞️ Clip Duration", 3, 15, 6)
effect = st.selectbox("🌀 Text Animation", ["Static", "Fade In", "Typewriter"])

# --- Helpers ---
def wrap_text(text, font, max_width=W - 100):
    draw = ImageDraw.Draw(Image.new("RGB", (W, H)))
    lines = []
    for line in text.split("\n"):
        words = line.split()
        if not words:
            lines.append("")
            continue
        wrapped = ""
        for word in words:
            test = wrapped + word + " "
            w = draw.textlength(test, font=font)
            if w <= max_width:
                wrapped = test
            else:
                lines.append(wrapped.strip())
                wrapped = word + " "
        lines.append(wrapped.strip())
    return lines

def generate_frames(effect_type, text, font, color, frame_count, fps):
    frames = []
    lines = wrap_text(text, font)
    line_heights = [font.getbbox(line)[3] for line in lines]
    total_height = sum(line_heights) + (len(lines) - 1) * 10
    y_start = (H - total_height) // 2

    for i in range(frame_count):
        img = Image.new("RGB", (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        if effect_type == "Typewriter":
            n_chars = int(len(text) * (i / frame_count))
            partial = text[:n_chars]
            show_lines = wrap_text(partial, font)
        else:
            show_lines = lines

        y = y_start
        for line in show_lines:
            alpha = 255
            if effect_type == "Fade In":
                alpha = int(255 * (i / frame_count))
            text_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_img)
            w = draw.textlength(line, font=font)
            text_draw.text(((W - w) // 2, y), line, font=font, fill=color + (alpha,))
            img = Image.alpha_composite(img.convert("RGBA"), text_img).convert("RGB")
            y += font.getbbox(line)[3] + 10

        frames.append(np.array(img))
    return frames

def render_text_video(frames, output_path, fps):
    temp_dir = tempfile.mkdtemp()
    for i, frame in enumerate(frames):
        Image.fromarray(frame).save(os.path.join(temp_dir, f"frame_{i:04d}.png"))

    frame_pattern = os.path.join(temp_dir, "frame_%04d.png")
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-i", frame_pattern,
        "-vf", f"scale={W}:{H}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    shutil.rmtree(temp_dir)

def overlay_text_on_video(bg_video_path, text_video_path, output_path):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", bg_video_path,
        "-i", text_video_path,
        "-filter_complex", "[0:v][1:v] overlay=0:0:enable='between(t,0,20)'",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

# --- Generate ---
if st.button("🚀 Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as vid_file:
        vid_file.write(uploaded_video.read())
        bg_video_path = vid_file.name

    font = ImageFont.truetype(FONT_PATH, font_size)
    color_rgb = tuple(int(text_color[i:i+2], 16) for i in (1, 3, 5))

    fps = 24
    total_frames = duration * fps

    st.info("Rendering text frames...")
    frames = generate_frames(effect, quote_text, font, color_rgb, total_frames, fps)

    st.info("Creating text video...")
    text_video_path = os.path.join(tempfile.gettempdir(), f"text_{uuid.uuid4().hex}.mp4")
    render_text_video(frames, text_video_path, fps)

    st.info("Merging with original video...")
    final_path = os.path.join(tempfile.gettempdir(), f"final_{uuid.uuid4().hex}.mp4")
    overlay_text_on_video(bg_video_path, text_video_path, final_path)

    st.success("✅ Done!")
    st.video(final_path)
    with open(final_path, "rb") as f:
        st.download_button("📥 Download Final Video", f.read(), file_name="quote_video.mp4")
