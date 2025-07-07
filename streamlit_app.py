import streamlit as st
from moviepy.editor import VideoFileClip
import tempfile, os

video_file = st.file_uploader("Upload a test video", type=["mp4"])

if video_file:
    path = os.path.join(tempfile.gettempdir(), "test_video.mp4")
    with open(path, "wb") as f:
        f.write(video_file.read())

    try:
        clip = VideoFileClip(path)
        frame = clip.get_frame(0)  # Try to get the first frame
        st.image(frame, caption="First frame of uploaded video")
        st.success("✅ Video is readable and has visible frames.")
    except Exception as e:
        st.error(f"❌ MoviePy could not read your video file: {e}")
