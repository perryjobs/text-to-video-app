# streamlit_app.py (v4 – transitions & animated text)
import streamlit as st
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests, os, io, textwrap, tempfile, numpy as np
from gtts import gTTS

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
    return img

# Animated text overlay clip

def animated_text_clip(size, text, font, color, mode, duration):
    base_img = text_frame(size, text, font, color)
    # Convert PIL image to NumPy array for MoviePy
    base_clip = ImageClip(np.array(base_img)).set_duration(duration)
    if mode == "Typewriter":
        return base_clip.crop(x1=lambda t: 0, x2=lambda t: base_img.width*(t/duration))
    elif mode == "Ascend":
        return base_clip.set_position(lambda t: ("center", size[1]*(1-t/duration)-base_img.height/2))
    elif mode == "Shift":
        return base_clip.set_position(lambda t: (size[0]*(1-t/duration)-base_img.width/2, "center"))
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
    quotes=[q.strip() for q in quotes_raw.split("\n\n") if q.strip()]
    if not quotes:
        st.error("Provide at least one quote."); st.stop()
    font=ImageFont.truetype(FONT_PATH,font_size)
    bg_clips=[]

    if media_type=="Image":
        imgs_bytes=[]
        if img_src=="Upload":
            if not img_files:
                st.error("Upload images."); st.stop()
            imgs_bytes=[f.read() for f in img_files]
        else:
            for _ in range(num_imgs):
                img=fetch_unsplash(kw)
                if img: imgs_bytes.append(img)
        if not imgs_bytes: st.error("No images fetched."); st.stop()
        for b in imgs_bytes:
            img=Image.open(io.BytesIO(b)).convert("RGB").resize((W,H),Image.Resampling.LANCZOS)
            path=os.path.join(TEMP_DIR,f"bg_{hash(b)}.png"); img.save(path)
            bg_clips.append(ImageClip(path).set_duration(quote_dur))
    else:
        vids=[]
        if vid_src=="Upload":
            if not vid_files: st.error("Upload videos."); st.stop()
            vids=[f for f in vid_files]
        else:
            for _ in range(num_vids):
                url=fetch_pexels_video(kw)
                if url:
                    fname=os.path.join(TEMP_DIR,f"pex_{hash(url)}.mp4")
                    with open(fname,"wb") as fp: fp.write(requests.get(url).content)
                    vids.append(fname)
        if not vids: st.error("No videos found."); st.stop()
        for v in vids:
            path=v if isinstance(v,str) else os.path.join(TEMP_DIR,v.name)
            if not isinstance(v,str):
                with open(path,"wb") as fp: fp.write(v.read())
            bg_clips.append(VideoFileClip(path).subclip(0,quote_dur).without_audio())

    # build quote clips with animation
    clips=[]
    for i,q in enumerate(quotes):
        bg=bg_clips[i % len(bg_clips)].copy()
        txt_clip=animated_text_clip((W,H),q,font,text_color,text_anim,quote_dur)
        comp=CompositeVideoClip([bg,txt_clip.set_position("center")])
        clips.append(comp)

    # add dissolve transition
    if len(clips) == 1:
        video = clips[0]
    else:
        video = concatenate_videoclips(
            clips,
            method="compose",
            padding=-trans_dur,
            transition=clips[0].crossfadein(trans_dur)
        )))

    # handle audio
    if music_mode=="Upload" and music_file:
        mp3_path=os.path.join(TEMP_DIR,"music.mp3"); open(mp3_path,"wb").write(music_file.read())
        bg_audio=AudioFileClip(mp3_path).volumex(0.3).audio_loop(duration=video.duration)
    elif music_mode=="Sample" and sample_choice:
        bg_audio=AudioFileClip(os.path.join(SAMPLE_MUSIC_DIR,sample_choice)).volumex(0.3).audio_loop(duration=video.duration)
    else:
        bg_audio=None

    if voiceover:
        tts_path=os.path.join(TEMP_DIR,"voice.mp3"); gTTS(" ".join(quotes),lang=voice_lang).save(tts_path)
        voice_clip=AudioFileClip(tts_path)
        if voice_clip.duration < video.duration:
            voice_clip=voice_clip.audio_loop(duration=video.duration)
        final_audio=CompositeAudioClip([voice_clip, bg_audio]) if bg_audio else voice_clip
    else:
        final_audio=bg_audio

    if final_audio:
        video=video.set_audio(final_audio)

    out=os.path.join(TEMP_DIR,"final.mp4")
    video.write_videofile(out,fps=24,preset="ultrafast")
    st.success("Done!")
    st.video(out)
    st.download_button("Download",open(out,"rb"),"video.mp4")
