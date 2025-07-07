import streamlit as st
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from PIL import ImageFont
import tempfile, os
from gtts import gTTS
import numpy as np

# Constants
W, H = 1080, 1920
TEMP_DIR = tempfile.mkdtemp()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

st.set_page_config(layout="wide")
st.title("📽️ Vertical Quote Video Maker (1080x1920)")

# Sidebar options
font_size = st.sidebar.slider("Font Size", 30, 150, 80)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote", 3, 15, 6)
voiceover = st.sidebar.checkbox("Add AI narration (gTTS)")
voice_lang = st.sidebar.selectbox("Voice Language", ["en", "es", "fr"], disabled=not voiceover)

video_file = st.sidebar.file_uploader("Upload a vertical background video (.mp4)", type=["mp4"])
music_file = st.sidebar.file_uploader("Optional: Upload background music (.mp3)", type=["mp3"])
quotes_input = st.text_area("Enter each quote separated by a blank line", height=300)

if st.button("Generate Video"):
    quotes = [q.strip() for q in quotes_input.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Please enter at least one quote.")
        st.stop()
    if not video_file:
        st.error("Please upload a background video.")
        st.stop()

    # Save uploaded video to disk
    bg_path = os.path.join(TEMP_DIR, "bg.mp4")
    with open(bg_path, "wb") as f:
        f.write(video_file.read())

    bg_clip = VideoFileClip(bg_path).resize((W, H)).without_audio()

    clips = []
    for quote in quotes:
        text = TextClip(
            quote, fontsize=font_size, font="DejaVu-Sans-Bold",
            color=text_color.replace("#", ""), size=(W-100, None), method='caption'
        ).set_duration(quote_dur).set_position('center')

        subclip = bg_clip.subclip(0, min(quote_dur, bg_clip.duration)).set_duration(quote_dur)
        final = CompositeVideoClip([subclip, text], size=(W, H)).set_duration(quote_dur)
        clips.append(final)

    video = concatenate_videoclips(clips, method="compose")

    # Background music
    if music_file:
        music_path = os.path.join(TEMP_DIR, "music.mp3")
        with open(music_path, "wb") as f:
            f.write(music_file.read())
        music = AudioFileClip(music_path).volumex(0.3).audio_loop(duration=video.duration)
    else:
        music = None

    # Voiceover
    if voiceover:
        tts_path = os.path.join(TEMP_DIR, "voice.mp3")
        gTTS(" ".join(quotes), lang=voice_lang).save(tts_path)
        voice = AudioFileClip(tts_path)
        if voice.duration < video.duration:
            voice = voice.audio_loop(duration=video.duration)
        audio = voice.set_duration(video.duration)
        if music:
            audio = CompositeVideoClip([]).set_audio(audio).audio.set_audio(music)
    else:
        audio = music

    if audio:
        video = video.set_audio(audio)

    # Export
    out_path = os.path.join(TEMP_DIR, "final.mp4")
    video.write_videofile(out_path, fps=24, preset="ultrafast")
    st.success("✅ Video generated successfully!")
    st.video(out_path)
    st.download_button("📥 Download Video", open(out_path, "rb"), "final.mp4")
