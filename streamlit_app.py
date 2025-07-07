# streamlit_app.py (fixed Unsplash and Pexels issues)
import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests, os, io, textwrap, tempfile
from gtts import gTTS

DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SAMPLE_MUSIC_DIR = "sample_music"
TEMP_DIR = tempfile.mkdtemp()

UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

def fetch_unsplash_image(keyword, w, h):
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    r = requests.get(f"https://api.unsplash.com/photos/random?query={keyword}&orientation=portrait", headers=headers)
    if r.status_code == 200:
        url = r.json()["urls"]["regular"]
        return requests.get(url).content
    return None

def fetch_pexels_video(keyword):
    headers = {"Authorization": PEXELS_KEY}
    r = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1", headers=headers)
    if r.status_code == 200 and r.json()["videos"]:
        return r.json()["videos"][0]["video_files"][0]["link"]
    return None

def wrap_text(text, width, draw, font):
    words = text.split()
    lines, line = [], ""
    for w in words:
        if draw.textlength(line + " " + w, font=font) <= width:
            line += " " + w
        else:
            lines.append(line.strip())
            line = w
    if line:
        lines.append(line.strip())
    return lines

def render_text_image(size, text, font, color):
    W, H = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = wrap_text(text, W - 80, draw, font)
    y = (H - len(lines) * (font.size + 10)) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=color)
        y += font.size + 10
    path = os.path.join(TEMP_DIR, f"text_{hash(text)}.png")
    img.save(path)
    return path

def apply_watermark(image, wm_img, scale):
    W, H = image.size
    wm_w = int(W * scale / 100)
    wm_h = int(wm_w * wm_img.height / wm_img.width)
    wm = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)
    image.paste(wm, (W - wm_w - 20, H - wm_h - 20), wm)
    return image

st.set_page_config("Motivational Video Maker", layout="wide")
st.title("🎬 Motivational/Quote Video Maker")

st.sidebar.header("Settings")
media_type = st.sidebar.selectbox("Media Type", ["Image", "Video"])
fmt = st.sidebar.selectbox("Format", ["Vertical (720x1280)", "Square (720x720)"])
W, H = (720, 1280) if fmt.startswith("Vertical") else (720, 720)

# Background Input
bg_file = None
if media_type == "Image":
    bg_mode = st.sidebar.radio("Image Source", ["Upload", "Unsplash"], horizontal=True)
    if bg_mode == "Upload":
        bg_file = st.sidebar.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    else:
        unsplash_kw = st.sidebar.text_input("Unsplash keyword", "sunrise")

if media_type == "Video":
    vid_mode = st.sidebar.radio("Video Source", ["Upload", "Pexels"], horizontal=True)
    if vid_mode == "Upload":
        vid_file = st.sidebar.file_uploader("Upload Video", type=["mp4"])
    else:
        pexels_kw = st.sidebar.text_input("Pexels keyword", "nature")

music_mode = st.sidebar.radio("Music", ["Upload", "Sample"], horizontal=True)
music_file = st.sidebar.file_uploader("Upload MP3" if music_mode == "Upload" else None, type=["mp3"])
sample_tracks = [f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
music_choice = st.sidebar.selectbox("Sample Track", sample_tracks) if music_mode == "Sample" and sample_tracks else None

wm_file = st.sidebar.file_uploader("Watermark (PNG)", type=["png"])
wm_scale = st.sidebar.slider("Watermark Size %", 5, 30, 10)

font_size = st.sidebar.slider("Font Size", 30, 100, 60)
text_color = st.sidebar.color_picker("Text Color", "#FFFFFF")
duration = st.sidebar.slider("Duration per quote", 3, 12, 6)
voiceover = st.sidebar.checkbox("Use AI Narration")
voice_lang = st.sidebar.selectbox("Voice language", ["en", "es", "fr"], disabled=not voiceover)

quotes_raw = st.text_area("Enter one or more quotes (separated by blank lines):")
if st.button("Generate Video"):
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Please enter at least one quote.")
        st.stop()

    wm_img = Image.open(wm_file).convert("RGBA") if wm_file else None
    font = ImageFont.truetype(DEFAULT_FONT, font_size)
    clips = []

    if media_type == "Image":
        bg_bytes = None
        if bg_mode == "Upload" and bg_file:
            bg_bytes = bg_file.read()
        elif bg_mode == "Unsplash":
            bg_bytes = fetch_unsplash_image(unsplash_kw, W, H)
        if not bg_bytes:
            st.error("Image could not be loaded."); st.stop()
        base_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

        for quote in quotes:
            img = base_img.copy()
            if wm_img:
                img = apply_watermark(img, wm_img, wm_scale)
            txt_path = render_text_image((W, H), quote, font, text_color)
            overlay = Image.open(txt_path).convert("RGBA")
            img = Image.alpha_composite(img.convert("RGBA"), overlay)
            final_path = os.path.join(TEMP_DIR, f"final_{hash(quote)}.png")
            img.convert("RGB").save(final_path)
            clips.append(ImageClip(final_path).set_duration(duration))

    else:
        vid_path = os.path.join(TEMP_DIR, "bg_video.mp4")
        if vid_mode == "Upload" and vid_file:
            with open(vid_path, "wb") as f:
                f.write(vid_file.read())
        elif vid_mode == "Pexels":
            vid_url = fetch_pexels_video(pexels_kw)
            if not vid_url:
                st.error("Video fetch failed."); st.stop()
            with open(vid_path, "wb") as f:
                f.write(requests.get(vid_url).content)

        base_vid = VideoFileClip(vid_path).without_audio()
            base_vid_w, base_vid_h = base_vid.size  # keep original dimensions; avoids Pillow ANTIALIAS bug
        for quote in quotes:
            overlay_path = render_text_image((int(base_vid_w), int(base_vid_h)), quote, font, text_color)
            txt_clip = ImageClip(overlay_path).set_duration(duration).set_position("center")
            comp = CompositeVideoClip([base_vid.subclip(0, duration), txt_clip])
            clips.append(comp)

    final_video = concatenate_videoclips(clips, method="compose")

    if music_mode == "Upload" and music_file:
        music_path = os.path.join(TEMP_DIR, "music.mp3")
        with open(music_path, "wb") as f:
            f.write(music_file.read())
    elif music_mode == "Sample" and music_choice:
        music_path = os.path.join(SAMPLE_MUSIC_DIR, music_choice)
    else:
        music_path = None

    bg_audio = AudioFileClip(music_path).volumex(0.3).set_duration(final_video.duration) if music_path else None

    if voiceover:
        full_text = " ".join(quotes)
        tts_path = os.path.join(TEMP_DIR, "voice.mp3")
        gTTS(full_text, lang=voice_lang).save(tts_path)
        voice = AudioFileClip(tts_path).set_duration(final_video.duration)
        audio = CompositeAudioClip([voice, bg_audio]) if bg_audio else voice
    else:
        audio = bg_audio

    final_video = final_video.set_audio(audio)
    output_path = os.path.join(TEMP_DIR, "final.mp4")
    final_video.write_videofile(output_path, fps=24)
    st.video(output_path)
    with open(output_path, "rb") as f:
        st.download_button("Download Video", f, "video.mp4")
