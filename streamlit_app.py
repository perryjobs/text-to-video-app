from PIL import Image, ImageDraw, ImageFont, ImageColor
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import streamlit as st
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
import numpy as np, tempfile, os, base64, textwrap

W, H = 1080, 1920
TMP = tempfile.mkdtemp()
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

st.title("Debugging Quote Maker")

vid = st.file_uploader("Upload MP4", type="mp4")
txt = st.text_area("Quote", "HELLO WORLD", height=100)
clr = st.color_picker("Color", "#FFFFFF")
dur = st.slider("Duration", 3, 10, 5)
fx = st.selectbox("Effect", ["Static", "Fade In", "Typewriter"])

if st.button("Run"):
    if not vid:
        st.error("Upload a video"); st.stop()

    # Save and load video
    path = os.path.join(TMP, "in.mp4")
    open(path, "wb").write(vid.read())
    clip = VideoFileClip(path).subclip(0, dur).resize((W, H))
    st.write("✅ Video load OK:", clip.duration, clip.size)

    font = ImageFont.truetype(FONT, 80)
    rgb = ImageColor.getrgb(clr)

    def wrap(t): return textwrap.wrap(t, width=25)

    def render_img(lines):
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)
        lh = font.getbbox("A")[3] + 10
        y = (H - len(lines)*lh)//2
        for l in lines:
            w = d.textlength(l, font=font)
            d.text(((W-w)//2, y), l, fill=rgb, font=font)
            y += lh
        return np.array(img)

    if fx == "Typewriter":
        # Only test first frame
        arr0 = render_img(wrap(txt[:1]))
        st.image(arr0)
        txt_clip = ImageClip(arr0).set_duration(1).set_position("center")
    else:
        arr = render_img(wrap(txt))
        st.image(arr)
        txt_clip = ImageClip(arr).set_duration(dur).set_position("center")
        if fx == "Fade In":
            txt_clip = txt_clip.fadein(1)

    st.write("✅ Text creation OK")

    final = CompositeVideoClip([clip, txt_clip])
    out = os.path.join(TMP, "out.mp4")
    final.write_videofile(out, fps=24, codec="libx264")
    st.success("Done")
    data = open(out, "rb").read()
    st.video(data)
    st.download_button("Download", data, "v.mp4")
