# streamlit_app.py (v5 – Fix transitions & real typewriter)
import streamlit as st
from moviepy.editor import *
import requests, os, io, textwrap, tempfile, numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

def safe_imageclip(image, duration):
    """Convert image to RGB if needed and return ImageClip."""
    if image.mode == "RGBA":
        image = image.convert("RGB")
    return ImageClip(np.array(image)).set_duration(duration)

# ✅ Check Pillow version to avoid crashes
if int(PILLOW_VERSION.split('.')[0]) < 10:
    st.error("This app requires Pillow >= 10.0.0. Please upgrade Pillow by running:\n\n`pip install --upgrade Pillow`")
    st.stop()

# 🩹 Monkey patch to fix MoviePy incompatibility with Pillow >= 10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS


# --- Constants ---
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SAMPLE_MUSIC_DIR = "sample_music"
TEMP_DIR = tempfile.mkdtemp()
UNSPLASH_KEY = st.secrets.get("UNSPLASH_KEY", "")
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")

# ---------------- Helpers ----------------

def fetch_unsplash(keyword):
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    r = requests.get(f"https://api.unsplash.com/photos/random?query={keyword}", headers=headers)
    if r.status_code == 200:
        return requests.get(r.json()["urls"]["regular"]).content
    return None

def fetch_pexels_video(keyword):
    headers = {"Authorization": PEXELS_KEY}
    r = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1", headers=headers)
    if r.status_code == 200 and r.json()["videos"]:
        return r.json()["videos"][0]["video_files"][0]["link"]
    return None

def wrap_lines(text, draw, font, max_w):
    words, line, lines = text.split(), "", []
    for w in words:
        if draw.textlength(f"{line} {w}", font=font) <= max_w:
            line += f" {w}" if line else w
        else:
            lines.append(line); line = w
    if line: lines.append(line)
    return lines

def text_frame(size, text, font, color):
    W, H = size
    img = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(img)
    lines = wrap_lines(text, draw, font, W-80)
    y = (H - len(lines)*(font.size+10))//2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((W-w)//2, y), ln, font=font, fill=color)
        y += font.size+10
    return img.convert("RGB")

def typewriter_frames(size, text, font, color, duration):
    chars = list(text)
    total_frames = int(duration * 24)
    def make_frame(t):
        i = min(int(len(chars) * t / duration), len(chars))
        partial = ''.join(chars[:i])
        img = Image.new("RGBA", size, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        lines = wrap_lines(partial, draw, font, size[0]-80)
        y = size[1] - len(lines)*(font.size+10) - 40
        for ln in lines:
            w = draw.textlength(ln, font=font)
            draw.text(((size[0]-w)//2, y), ln, font=font, fill=color)
            y += font.size+10
        return np.array(img.convert("RGB"))
    return VideoClip(make_frame=make_frame, duration=duration).set_position(("center","bottom"))

def animated_text_clip(size, text, font, color, mode, duration):
    if mode == "Typewriter":
        return typewriter_frames(size, text, font, color, duration).set_position("center")
    base_img = text_frame(size, text, font, color)
    base_clip = ImageClip(np.array(base_img)).set_duration(duration)
    if mode == "Ascend":
        return base_clip.set_position(lambda t: ("center", size[1] * (1 - t / duration) - base_img.height / 2))
    elif mode == "Shift":
        return base_clip.set_position(lambda t: (size[0] * (1 - t / duration) - base_img.width / 2, "center"))
    else:
        return base_clip.set_position("center")

# ---------------- Streamlit UI -----------------

st.set_page_config("Quote Video Maker", layout="wide")
st.title("🎞️ Quote Video Maker – Animated & Merged")

st.sidebar.header("Settings")
media_type = st.sidebar.selectbox("Background Media", ["Image", "Video"])
fmt = st.sidebar.selectbox("Format", ["Vertical", "Square"])
W,H = (720,1280) if fmt=="Vertical" else (720,720)

if media_type=="Image":
    img_src = st.sidebar.radio("Image Source", ["Upload","Unsplash"], horizontal=True)
    if img_src=="Upload":
        img_files = st.sidebar.file_uploader("Upload one or more images", accept_multiple_files=True, type=["jpg","jpeg","png"])
    else:
        kw = st.sidebar.text_input("Unsplash keyword", "nature")
        num_imgs = st.sidebar.slider("# random images",1,5,3)
else:
    vid_src = st.sidebar.radio("Video Source", ["Upload","Pexels"], horizontal=True)
    if vid_src=="Upload":
        vid_files = st.sidebar.file_uploader("Upload one or more videos", accept_multiple_files=True, type=["mp4"])
    else:
        kw = st.sidebar.text_input("Pexels keyword", "nature")
        num_vids = st.sidebar.slider("# random videos",1,3,1)

music_mode = st.sidebar.radio("Music", ["Upload","Sample"], horizontal=True)
if music_mode=="Upload":
    music_file = st.sidebar.file_uploader("Upload mp3", type=["mp3"])
else:
    samples=[f for f in os.listdir(SAMPLE_MUSIC_DIR) if f.endswith(".mp3")] if os.path.isdir(SAMPLE_MUSIC_DIR) else []
    sample_choice= st.sidebar.selectbox("Sample track", samples) if samples else None

font_size = st.sidebar.slider("Font size",30,100,60)
text_color = st.sidebar.color_picker("Text color","#FFFFFF")
quote_dur = st.sidebar.slider("Seconds per quote",3,15,6)
text_anim = st.sidebar.selectbox("Text animation",["None","Typewriter","Ascend","Shift"])
trans_dur = st.sidebar.slider("Transition (sec)",0.5,2.0,1.0,0.1)
voiceover = st.sidebar.checkbox("AI narration (gTTS)")
voice_lang = st.sidebar.selectbox("Voice language",["en","es","fr"],disabled=not voiceover)

quotes_raw = st.text_area("Quotes – separate each by blank line",height=250)

if st.button("Generate Video"):
    quotes = [q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Provide at least one quote.")
        st.stop()

    font = ImageFont.truetype(FONT_PATH, font_size)
    clips = []

    # --- Load Background Clips ---
    bg_clips = []

    if media_type == "Image":
        if img_src == "Upload":
            if not img_files:
                st.error("Please upload at least one image.")
                st.stop()
            for file in img_files:
                img = Image.open(file).resize((W, H))
            if img.mode == "RGBA":
                img = img.convert("RGB")
                bg_clips.append(ImageClip(np.array(img)).set_duration(quote_dur).resize((W, H)))
        else:  # Unsplash
            for _ in range(num_imgs):
                content = fetch_unsplash(kw)
                if content:
                    img = Image.open(io.BytesIO(content)).resize((W, H))
            if img.mode == "RGBA":
                img = img.convert("RGB")
                bg_clips.append(ImageClip(np.array(img)).set_duration(quote_dur).resize((W, H)))

    else:  # Video
        if vid_src == "Upload":
            if not vid_files:
                st.error("Please upload at least one video.")
                st.stop()
            for file in vid_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(file.read())
                    tmp.flush()
                    bg_clips.append(VideoFileClip(tmp.name).resize((W, H)).subclip(0, quote_dur))
        else:  # Pexels
            for i in range(num_vids):
                url = fetch_pexels_video(kw)
                if url:
                    vid_path = os.path.join(TEMP_DIR, f"pexels_{i}.mp4")
                    with open(vid_path, "wb") as f:
                        f.write(requests.get(url).content)
                    bg_clips.append(VideoFileClip(vid_path).resize((W, H)).subclip(0, quote_dur))

    if not bg_clips:
        st.error("Could not load any background media.")
        st.stop()

    # --- Generate Quote Clips ---
    for i, q in enumerate(quotes):
        bg = bg_clips[i % len(bg_clips)].copy()
        txt_clip = animated_text_clip((W, H), q, font, text_color, text_anim, quote_dur)
        comp = CompositeVideoClip(
    [bg.set_duration(quote_dur).resize((W, H)), txt_clip.set_duration(quote_dur)],
    size=(W, H)
)
        clips.append(comp)

    # --- Combine Clips with Transitions ---
    if len(clips) == 1:
        video = clips[0]
    else:
        timeline = []
        current_start = 0
        for idx, c in enumerate(clips):
            if idx == 0:
                timeline.append(c.set_start(current_start))
            else:
                timeline.append(c.set_start(current_start).crossfadein(trans_dur))
            current_start += quote_dur - trans_dur
        video = CompositeVideoClip(timeline, size=(W, H)).set_duration(current_start + trans_dur)

    # --- Add Music ---
    bg_audio = None
    if music_mode == "Upload" and music_file:
        mp3_path = os.path.join(TEMP_DIR, "music.mp3")
        with open(mp3_path, "wb") as f:
            f.write(music_file.read())
        bg_audio = AudioFileClip(mp3_path).volumex(0.3).audio_loop(duration=video.duration)
    elif music_mode == "Sample" and sample_choice:
        sample_path = os.path.join(SAMPLE_MUSIC_DIR, sample_choice)
        bg_audio = AudioFileClip(sample_path).volumex(0.3).audio_loop(duration=video.duration)

    # --- Add Voiceover ---
    final_audio = bg_audio
    if voiceover:
        tts_path = os.path.join(TEMP_DIR, "voice.mp3")
        gTTS(" ".join(quotes), lang=voice_lang).save(tts_path)
        voice_clip = AudioFileClip(tts_path)
        if voice_clip.duration < video.duration:
            voice_clip = voice_clip.audio_loop(duration=video.duration)
        final_audio = CompositeAudioClip([voice_clip, bg_audio]) if bg_audio else voice_clip

    if final_audio:
        video = video.set_audio(final_audio)

    # --- Export Final Video ---
    out = os.path.join(TEMP_DIR, "final.mp4")
    video.write_videofile(out, fps=24, preset="ultrafast")
    st.success("Done!")
    st.video(out)
    st.download_button("Download", open(out, "rb"), "video.mp4")
