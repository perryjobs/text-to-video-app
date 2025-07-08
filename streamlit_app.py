import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile, os, subprocess, shutil, uuid
import numpy as np

# Constants
W, H = 1080, 1920
PREVIEW_W, PREVIEW_H = 360, 640
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FPS = 24

st.set_page_config(layout="centered")
st.title("🎬 Quote Video Maker with Transparent Text Overlay")

# Check ffmpeg
ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    st.error("FFmpeg not found! Please add FFmpeg to your PATH or install it.")
    st.stop()

# Inputs
uploaded_video = st.file_uploader("Upload vertical MP4 video (9:16)", type=["mp4"])
quote_text = st.text_area("Enter your quote", "Believe in yourself.\nYou are stronger than you think.", height=150)
font_size = st.slider("Font size", 30, 120, 90)
text_color = st.color_picker("Text color", "#FFFFFF")
duration = st.slider("Clip duration (seconds)", 3, 15, 6)
animation = st.selectbox("Text Animation", ["Static", "Fade In", "Typewriter"])

def wrap_text(text, font, max_width):
    dummy_img = Image.new("RGBA", (1,1))
    draw = ImageDraw.Draw(dummy_img)
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if draw.textlength(test_line, font=font) <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines

def generate_frames(text, font, color_rgba, duration, fps, animation_type):
    total_frames = int(duration * fps)
    frames = []

    lines = wrap_text(text, font, max_width=W-100)
    line_heights = [font.getbbox(line)[3] for line in lines]
    total_text_height = sum(line_heights) + (len(lines) -1)*10
    y_start = (H - total_text_height) // 2

    for frame_idx in range(total_frames):
        img = Image.new("RGBA", (W,H), (0,0,0,0))
        draw = ImageDraw.Draw(img)

        # Determine how many chars or alpha based on animation
        if animation_type == "Typewriter":
            total_chars = len(text)
            chars_to_show = int(total_chars * frame_idx / total_frames)
            partial_text = text[:chars_to_show]
            show_lines = wrap_text(partial_text, font, max_width=W-100)
        else:
            show_lines = lines

        # Alpha for fade in
        alpha = 255
        if animation_type == "Fade In":
            alpha = int(255 * frame_idx / total_frames)

        y = y_start
        for line in show_lines:
            w = draw.textlength(line, font=font)
            # Draw line with alpha
            draw.text(((W - w)//2, y), line, font=font, fill=color_rgba[:3] + (alpha,))
            y += font.getbbox(line)[3] + 10

        frames.append(np.array(img))
    return frames

def save_frames_as_video(frames, path, fps):
    tmpdir = tempfile.mkdtemp()
    for i, frame in enumerate(frames):
        Image.fromarray(frame).save(os.path.join(tmpdir, f"frame_{i:04d}.png"))

    cmd = [
        ffmpeg_path,
        "-y",
        "-framerate", str(fps),
        "-i", os.path.join(tmpdir, "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuva420p",  # preserve alpha channel
        "-vf", f"scale={W}:{H}",
        "-r", str(fps),
        path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    shutil.rmtree(tmpdir)

def overlay_text_on_video(bg_path, txt_path, out_path):
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", bg_path,
        "-i", txt_path,
        "-filter_complex", "[0:v][1:v] overlay=0:0:format=auto",
        "-c:a", "copy",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save uploaded video
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(uploaded_video.read())
        bg_path = f.name

    font = ImageFont.truetype(FONT_PATH, font_size)
    rgb = tuple(int(text_color[i:i+2], 16) for i in (1,3,5))
    color_rgba = rgb + (255,)

    st.info("Generating text frames...")
    frames = generate_frames(quote_text, font, color_rgba, duration, FPS, animation)

    st.info("Encoding text video...")
    txt_video_path = os.path.join(tempfile.gettempdir(), f"text_{uuid.uuid4().hex}.mp4")
    save_frames_as_video(frames, txt_video_path, FPS)

    st.info("Overlaying text on video...")
    final_path = os.path.join(tempfile.gettempdir(), f"final_{uuid.uuid4().hex}.mp4")
    overlay_text_on_video(bg_path, txt_video_path, final_path)

    st.success("Done! Here's your video:")
    st.video(final_path, format="video/mp4", start_time=0, width=PREVIEW_W)

    with open(final_path, "rb") as f:
        st.download_button("Download Video", f.read(), file_name="quote_video.mp4")
