import streamlit as st
from moviepy.editor import *
from PIL import ImageFont, ImageDraw, Image
import tempfile, numpy as np, os
from gtts import gTTS

st.set_page_config("🎬 Clean Quote Video Maker", layout="wide")
st.title("🎬 Quote Video Maker (Clean Start)")

# Temp directory for files
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Upload video
video_file = st.file_uploader("🎥 Upload background video", type=["mp4"])
quote_text = st.text_area("📝 Enter quote text")

font_size = st.slider("Font size", 20, 100, 60)
font_color = st.color_picker("Font color", "#FFFFFF")
text_anim = st.selectbox("Text animation", ["None", "Typewriter"])
duration = st.slider("Duration (seconds)", 3, 20, 6)

if st.button("Generate Video") and video_file and quote_text:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_file.read())
        tmp_path = tmp.name

    # Load background video
    bg_clip = VideoFileClip(tmp_path).subclip(0, duration).resize((720, 1280))

    # Prepare font
    font = ImageFont.truetype(FONT_PATH, font_size)

    # Prepare animated text
    def make_frame(t):
        chars = int(len(quote_text) * t / duration)
        partial = quote_text[:chars] if text_anim == "Typewriter" else quote_text
        img = Image.new("RGBA", (720, 1280), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), partial, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        draw.text(((720 - w) // 2, (1280 - h) // 2), partial, font=font, fill=font_color)
        return np.array(img.convert("RGB"))

    txt_clip = VideoClip(make_frame, duration=duration)

    final = CompositeVideoClip([bg_clip, txt_clip.set_position("center")], size=(720, 1280)).set_duration(duration)

    # Export
    out_path = os.path.join(TEMP_DIR, "out.mp4")
    final.write_videofile(out_path, fps=24, preset="ultrafast")

    st.success("✅ Done!")
    st.video(out_path)
    st.download_button("⬇️ Download Video", open(out_path, "rb"), file_name="quote_video.mp4")
