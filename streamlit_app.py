import streamlit as st
import os
import tempfile
import subprocess
import base64

# Constants
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n{result.stderr}")
    return result

def save_text_video(text, out_path, duration, fps=24):
    # Use ffmpeg drawtext filter with typewriter effect (characters appear one by one)
    # Escape text properly for ffmpeg
    escaped_text = text.replace(":", "\\:").replace("'", "\\'")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={W}x{H}:d={duration}:r={fps}",
        "-vf",
        (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{escaped_text}':"
            f"fontcolor=white:fontsize=90:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"enable='between(t,0,{duration})':"
            f"alpha='if(lt(t,n*{duration}/len(text)),0,1)'"
        ),
        "-pix_fmt", "yuva420p",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-t", str(duration),
        out_path
    ]
    run_cmd(cmd)

def save_text_video_fade(text, out_path, duration, fps=24):
    escaped_text = text.replace(":", "\\:").replace("'", "\\'")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={W}x{H}:d={duration}:r={fps}",
        "-vf",
        (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{escaped_text}':"
            f"fontcolor=white@0:fontsize=90:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"alpha='if(lt(t,1),t,1)'"
        ),
        "-pix_fmt", "yuva420p",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-t", str(duration),
        out_path
    ]
    run_cmd(cmd)

def overlay_text_on_video(bg_path, txt_path, out_path):
    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Background video missing: {bg_path}")
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"Text video missing: {txt_path}")

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-i", txt_path,
        "-filter_complex", "[0:v][1:v] overlay=0:0:format=auto",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        out_path
    ]
    run_cmd(cmd)

st.title("🎬 Quote Video Maker – Text Animation Overlay with FFmpeg")

uploaded_video = st.file_uploader("Upload vertical MP4 video (9:16)", type=["mp4"])
quote_text = st.text_area("Enter your quote", "Believe in yourself. You're stronger than you think.")
duration_limit = st.slider("Clip Duration (seconds)", 3, 15, 6)
text_effect = st.selectbox("Text Animation", ["Static", "Fade In", "Typewriter"])

if st.button("Generate Video"):
    if not uploaded_video:
        st.error("Please upload a video.")
        st.stop()

    # Save uploaded video
    bg_path = os.path.join(TEMP_DIR, "background.mp4")
    with open(bg_path, "wb") as f:
        f.write(uploaded_video.read())

    txt_path = os.path.join(TEMP_DIR, "text.mp4")
    final_path = os.path.join(TEMP_DIR, "final.mp4")

    try:
        # Generate text video with chosen animation
        if text_effect == "Typewriter":
            save_text_video(quote_text, txt_path, duration_limit)
        elif text_effect == "Fade In":
            save_text_video_fade(quote_text, txt_path, duration_limit)
        else:  # Static
            # Static text - just a still image video
            save_text_video_fade(quote_text, txt_path, duration_limit)  # reuse fade for static (alpha=1 after 1s)

        # Overlay text video onto background video
        overlay_text_on_video(bg_path, txt_path, final_path)

        st.success("✅ Done!")

        # Preview video
        video_bytes = open(final_path, "rb").read()
        encoded_video = base64.b64encode(video_bytes).decode()
        st.markdown(
            f"""
            <video controls style="width: 360px; height: 640px; border-radius: 12px;">
                <source src="data:video/mp4;base64,{encoded_video}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            """,
            unsafe_allow_html=True,
        )
        st.download_button("📥 Download Video", video_bytes, "quote_video.mp4")
    except Exception as e:
        st.error(f"Error: {e}")
