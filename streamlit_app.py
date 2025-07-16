import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import tempfile
import os

st.title("Video Combination App")

# User inputs for videos
video_path = st.file_uploader("Upload the main video", type=["mp4", "mov", "avi"])
bg_path = st.file_uploader("Upload the background video", type=["mp4", "mov", "avi"])

# Check if files are uploaded
if video_path and bg_path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_bg:
        # Save uploaded files to temp files
        temp_video.write(video_path.read())
        temp_bg.write(bg_path.read())
        temp_video_path = temp_video.name
        temp_bg_path = temp_bg.name

    try:
        # Load main video
        main_clip = VideoFileClip(temp_video_path)
        st.info("Loaded main video.")

        # Load background video
        bg_clip = VideoFileClip(temp_bg_path)
        st.info("Processing background video...")

        # Resize background video height to 1920
        bg_clip = bg_clip.resize(height=1920)

        # Adjust width to 1080 by cropping or padding
        target_width = 1080

        if bg_clip.w < target_width:
            # Pad width to target with black bars
            pad_width = target_width - bg_clip.w
            left_pad = pad_width // 2
            right_pad = pad_width - left_pad
            bg_clip = bg_clip.margin(left=left_pad, right=right_pad, color=(0, 0, 0))
        elif bg_clip.w > target_width:
            # Crop width to target
            left_crop = (bg_clip.w - target_width) // 2
            right_crop = left_crop + target_width
            bg_clip = bg_clip.crop(x1=left_crop, x2=right_crop)

        # Remove audio if any
        bg_clip = bg_clip.without_audio()

        # Resize main video if needed (optional)
        # main_clip = main_clip.resize(height=1920)

        # For demonstration, overlay main video on background or concatenate
        # Here, just display info
        st.success("Background video processed successfully.")

        # Example: overlay main clip on background (if desired), or just show background
        # final_clip = concatenate_videoclips([bg_clip, main_clip])  # or other processing

        # Save or preview the final clip as needed
        # For example, to preview:
        # st.video(final_clip.ipython_display(width=600))

        # Cleanup temp files
        os.remove(temp_video_path)
        os.remove(temp_bg_path)

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
else:
    st.info("Please upload both videos to proceed.")
