import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile, os, io, uuid
import ffmpeg
import threading

# Constants
W, H = 1080, 1920
PREVIEW_W, PREVIEW_H = 360, 640
FPS = 24
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

st.set_page_config(layout="centered")
st.title("🎬 Quote Video Maker – Animated Text Overlay (ffmpeg-python)")

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

def generate_frame(text, font, color_rgba, alpha=255):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = wrap_text(text, font, max_width=W-100)

    line_heights = [font.getbbox(line)[3] for line in lines]
    total_height = sum(line_heights) + (len(lines)-1)*10
    y = (H - total_height)//2

    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w)//2, y), line, font=font, fill=color_rgba[:3] + (alpha,))
        y += font.getbbox(line)[3] + 10
    return np.array(img)

def frame_generator(text, font, color_rgba, duration, fps, animation_type):
    total_frames = int(duration * fps)
    total_chars = len(text)
    for i in range(total_frames):
        if animation_type == "Typewriter":
            chars_to_show = int(total_chars * i / total_frames)
            partial_text = text[:chars_to_show]
            frame = generate_frame(partial_text, font, color_rgba, alpha=255)
        elif animation_type == "Fade In":
            alpha = int(255 * i / total_frames)
            frame = generate_frame(text, font, color_rgba, alpha=alpha)
        else:  # Static
            frame = generate_frame(text, font, color_rgba, alpha=255)
        yield frame

def save_text_video(frames, path, fps):
    process = (
        ffmpeg
        .input('pipe:', format='rawvideo', pix_fmt='rgba', s=f'{W}x{H}', framerate=fps)
        .output(path, pix_fmt='yuva420p', vcodec='libx264', crf=18)
        .overwrite_output()
        .run_async(pipe_stdin=True)
    )
    for frame in frames:
        process.stdin.write(frame.astype(np.uint8).tobytes())
    process.stdin.close()
    process.wait()

def overlay_text_on_video(bg_path, txt_path, out_path):
    (
        ffmpeg
        .input(bg_path)
        .input(txt_path)
        .filter_complex('[0:v][1:v] overlay=0:0:format=auto')
        .output(out_path, vcodec='libx264', crf=18, preset='medium', acodec='copy')
        .overwrite_output()
        .run()
    )

if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(uploaded_video.read())
        bg_path = f.name

    font = ImageFont.truetype(FONT_PATH, font_size)
    rgb = tuple(int(text_color[i:i+2],16) for i in (1,3,5))
    color_rgba = rgb + (255,)

    frames = frame_generator(quote_text, font, color_rgba, duration, FPS, animation)
    txt_video_path = os.path.join(tempfile.gettempdir(), f"text_{uuid.uuid4().hex}.mp4")
    st.info("Generating text video...")
    save_text_video(frames, txt_video_path, FPS)

    final_path = os.path.join(tempfile.gettempdir(), f"final_{uuid.uuid4().hex}.mp4")
    st.info("Overlaying text on background video...")
    overlay_text_on_video(bg_path, txt_video_path, final_path)

    st.success("✅ Done! Here's your video:")
    st.video(final_path, start_time=0, width=PREVIEW_W)

    with open(final_path, "rb") as f:
        st.download_button("📥 Download Video", f.read(), file_name="quote_video.mp4")
