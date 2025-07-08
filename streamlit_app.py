import streamlit as st
import subprocess
import tempfile
import os

# App Title
st.title("Quote Video Generator with FFmpeg")

# Upload background video
bg_video = st.file_uploader("Upload a background video (MP4, vertical format)", type=["mp4"])
quote = st.text_input("Enter a short quote")

generate = st.button("Generate Video")

if bg_video and quote and generate:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded video
        bg_path = os.path.join(tmpdir, "background.mp4")
        with open(bg_path, "wb") as f:
            f.write(bg_video.read())

        # Create transparent text video
        text_path = os.path.join(tmpdir, "text.mp4")
        text_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=color=black@0.0:s=1080x1920:d=6",
            "-vf",
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{quote}':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuva420p", "-t", "6",
            text_path
        ]

        st.info("Generating transparent text video...")
        result = subprocess.run(text_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"FFmpeg text video generation failed:\n{result.stderr}")
            st.stop()

        # Overlay text video onto background
        final_path = os.path.join(tmpdir, "final.mp4")
        overlay_cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", text_path,
            "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto",
            "-c:v", "libx264", "-c:a", "copy",
            final_path
        ]

        st.info("Overlaying text onto background video...")
        result = subprocess.run(overlay_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"FFmpeg overlay failed:\n{result.stderr}")
            st.stop()

        # Show result
        st.success("Here is your final video:")
        st.video(final_path)
