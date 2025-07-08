import streamlit as st
import tempfile
import os
import subprocess
import base64

# --- Constants ---
W, H = 1080, 1920
PREVIEW_W, PREVIEW_H = 360, 640
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

st.set_page_config(layout="wide")
st.title("🎬 Quote Video Maker with FFmpeg Text Animations")

uploaded_video = st.file_uploader("Upload vertical MP4 video (9:16)", type=["mp4"])
quote_text = st.text_area("Enter your quote", "Believe in yourself. You're stronger than you think.", height=150)
duration_limit = st.slider("Clip Duration (seconds)", 3, 15, 6)
text_effect = st.selectbox("Text Animation", ["Static", "Fade In", "Typewriter"])

def run_cmd(cmd):
    # Run subprocess and raise error if any
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result

def escape_text(text):
    # Escape special chars for ffmpeg drawtext filter
    return text.replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")

def save_text_video_static(text, out_path, duration, fps=24):
    escaped = escape_text(text)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black@0:s={W}x{H}:d={duration}:r={fps}",
        "-vf",
        f"drawtext=fontfile={FONT_PATH}:text='{escaped}':fontcolor=white:fontsize=90:x=(w-text_w)/2:y=(h-text_h)/2",
        "-pix_fmt", "yuva420p",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-t", str(duration),
        out_path
    ]
    run_cmd(cmd)

def save_text_video_fade(text, out_path, duration, fps=24):
    escaped = escape_text(text)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black@0:s={W}x{H}:d={duration}:r={fps}",
        "-vf",
        f"drawtext=fontfile={FONT_PATH}:text='{escaped}':fontcolor=white@0:fontsize=90:x=(w-text_w)/2:y=(h-text_h)/2:alpha='if(lt(t\\,1)\\,t\\,1)'",
        "-pix_fmt", "yuva420p",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-t", str(duration),
        out_path
    ]
    run_cmd(cmd)

def save_text_video_typewriter(text, out_path, duration, fps=24):
    # Draw characters progressively
    escaped = escape_text(text)
    # We use 'n' as number of characters in text, then alpha=if(gte(n*t/duration\, n_char), 1, 0)
    # But ffmpeg drawtext doesn't support that complex animation easily.
    # So we emulate typewriter effect with multiple drawtext filters chained:
    # But for simplicity here we fade in chars sequentially by overlaying.
    # Instead, we do a trick: we draw text with alpha that increases with time up to full opacity.
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black@0:s={W}x{H}:d={duration}:r={fps}",
        "-vf",
        f"drawtext=fontfile={FONT_PATH}:text='{escaped}':fontcolor=white@0:fontsize=90:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"alpha='min(1\\, max(0\\, (t/{duration})))'",
        "-pix_fmt", "yuva420p",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-t", str(duration),
        out_path
    ]
    run_cmd(cmd)

def overlay_text_on_video(bg_path, txt_path, out_path):
    # Overlay text video (with alpha) on background video, keep audio from bg
    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-i", txt_path,
        "-filter_complex", "[0:v][1:v] overlay=0:0:format=auto",
        "-c:a", "copy",
        out_path
    ]
    run_cmd(cmd)

if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save background video
    bg_path = os.path.join(TEMP_DIR, "bg.mp4")
    with open(bg_path, "wb") as f:
        f.write(uploaded_video.read())

    # Temporary text video path
    txt_video_path = os.path.join(TEMP_DIR, "text.mp4")
    final_path = os.path.join(TEMP_DIR, "final.mp4")

    try:
        # Generate text video based on selected animation
        if text_effect == "Static":
            save_text_video_static(quote_text, txt_video_path, duration_limit)
        elif text_effect == "Fade In":
            save_text_video_fade(quote_text, txt_video_path, duration_limit)
        elif text_effect == "Typewriter":
            save_text_video_typewriter(quote_text, txt_video_path, duration_limit)
        else:
            st.error("Unknown text animation selected.")
            st.stop()

        # Overlay text video onto background video
        overlay_text_on_video(bg_path, txt_video_path, final_path)

        # Read final video bytes for preview & download
        video_bytes = open(final_path, "rb").read()
        encoded_video = base64.b64encode(video_bytes).decode()

        st.success("✅ Video generated successfully!")

        st.markdown(
            f"""
            <video controls style="width: {PREVIEW_W}px; height: {PREVIEW_H}px; border-radius: 12px;">
                <source src="data:video/mp4;base64,{encoded_video}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            """,
            unsafe_allow_html=True,
        )
        st.download_button("📥 Download Video", video_bytes, "quote_video.mp4")

    except Exception as e:
        st.error(f"Error during video generation: {e}")
