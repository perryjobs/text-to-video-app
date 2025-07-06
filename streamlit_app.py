import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests, os, io, textwrap, tempfile
from gtts import gTTS

# Monkey patch for Pillow >=10 compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

st.title("📽️ Text to Video App")
st.sidebar.header("Video Settings")

# Aspect Ratio
fmt = st.sidebar.selectbox("Video Format", ["Square (1:1)", "Vertical (9:16)", "Horizontal (16:9)"])
W, H = 720, 720
if fmt.startswith("Vertical"): W, H = 720, 1280
elif fmt.startswith("Horizontal"): W, H = 1280, 720

# Background Source
media_type = st.sidebar.radio("Background Type", ["Image", "Video"], horizontal=True)

bg_file, vid_file, unsplash_kw, pexels_kw = None, None, None, None
if media_type == "Image":
    bg_mode = st.sidebar.radio("Image Source", ["Upload", "Unsplash"], horizontal=True)
    if bg_mode == "Upload":
        bg_file = st.sidebar.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    else:
        unsplash_kw = st.sidebar.text_input("Unsplash keyword", "sunrise")
else:
    vid_mode = st.sidebar.radio("Video Source", ["Upload", "Pexels"], horizontal=True)
    if vid_mode == "Upload":
        vid_file = st.sidebar.file_uploader("Upload Video", type=["mp4"])
    else:
        pexels_kw = st.sidebar.text_input("Pexels keyword", "nature")

# Text input and voiceover
text_input = st.text_area("Enter the text for your video")
voiceover = st.checkbox("Generate voiceover using AI (gTTS)")

if st.button("Generate Video"):
    with st.spinner("Creating video..."):
        clips = []

        try:
            if media_type == "Image":
                if bg_file is not None:
                    img = Image.open(bg_file).convert("RGB").resize((W, H))
                elif unsplash_kw:
                    res = requests.get(f"https://source.unsplash.com/{W}x{H}/?{unsplash_kw}")
                    img = Image.open(io.BytesIO(res.content)).convert("RGB").resize((W, H))
                else:
                    st.error("No background image source provided.")
                    img = None

                if img:
                    img_path = os.path.join(tempfile.gettempdir(), "bg.jpg")
                    img.save(img_path)
                    bg_clip = ImageClip(img_path).set_duration(10)
                    clips.append(bg_clip)

            else:
                if vid_file is not None:
                    vid_path = os.path.join(tempfile.gettempdir(), "bg.mp4")
                    with open(vid_path, "wb") as f:
                        f.write(vid_file.read())
                elif pexels_kw:
                    res = requests.get(
                        f"https://api.pexels.com/videos/search?query={pexels_kw}&per_page=1",
                        headers={"Authorization": st.secrets["PEXELS_API_KEY"]},
                    )
                    data = res.json()
                    video_url = data["videos"][0]["video_files"][0]["link"]
                    vid_data = requests.get(video_url).content
                    vid_path = os.path.join(tempfile.gettempdir(), "bg.mp4")
                    with open(vid_path, "wb") as f:
                        f.write(vid_data)
                else:
                    st.error("No background video source provided.")
                    vid_path = None

                if vid_path:
                    base_vid = VideoFileClip(vid_path).resize(height=H if fmt.startswith("Vertical") else W).without_audio()
                    bg_clip = base_vid.set_duration(10)
                    clips.append(bg_clip)

            # Text clip
            if text_input:
                wrapped = "\n".join(textwrap.wrap(text_input, width=40))
                txt_clip = TextClip(wrapped, fontsize=40, color='white', font="Arial", method="caption", size=(W - 100, None)).set_position("center").set_duration(10)
                clips.append(txt_clip)

            # Composite video
            valid_clips = [c for c in clips if c is not None]
            if not valid_clips:
                st.error("No valid video components to render.")
            else:
                final = CompositeVideoClip(valid_clips, size=(W, H))

                # Voiceover
                if voiceover and text_input:
                    try:
                        tts = gTTS(text_input)
                        audio_path = os.path.join(tempfile.gettempdir(), "voice.mp3")
                        tts.save(audio_path)
                        audio_clip = AudioFileClip(audio_path)
                        final = final.set_audio(audio_clip)
                    except Exception as e:
                        st.warning(f"Voiceover generation failed: {e}")

                # Output video
                out_path = os.path.join(tempfile.gettempdir(), "final.mp4")
                final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac")
                st.video(out_path)

        except Exception as e:
            st.error(f"❌ Failed to generate video: {e}")
