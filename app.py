import streamlit as st
import asyncio
import edge_tts
import requests
import io
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import numpy as np

st.set_page_config(page_title="Documentary AI Video Generator", page_icon="🎬", layout="wide")

st.title("🎬 Documentary-Style AI Video Generator")
st.write("Generate high-quality documentary videos with deep voiceovers!")

# Reliable Deep Voices
VOICES = {
    "Urdu Deep Male (Asad)": "ur-PK-AsadNeural",
    "Hindi Deep Male (Madhur)": "hi-IN-MadhurNeural",
    "English US Deep Male (Christopher)": "en-US-ChristopherNeural",
    "English UK Deep Male (Ryan)": "en-GB-RyanNeural"
}

voice_option = st.sidebar.selectbox("Select Voice", list(VOICES.keys()))
selected_voice = VOICES[voice_option]

script_input = st.text_area("Enter your script / topic:", height=150, placeholder="Enter script here...")

async def generate_audio(text, voice, output_filename):
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_filename)
    except Exception:
        # Fallback to English US voice if selected voice fails
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(output_filename)

def get_pollinations_image(prompt):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1280&height=720&nologo=true"
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        return Image.new('RGB', (1280, 720), color=(0, 0, 0))

if st.button("Generate Video"):
    if not script_input.strip():
        st.warning("Please enter a script or topic first.")
    else:
        st.info("Processing video generation...")
        # Clean text lines
        lines = [line.strip() for line in script_input.replace('\n', ' ').split('.') if line.strip()]
        if not lines:
            lines = [script_input.strip()]
            
        clips = []
        progress_bar = st.progress(0)
        
        for idx, line in enumerate(lines):
            st.write(f"Generating Scene {idx+1}/{len(lines)}...")
            
            # 1. Generate Voice
            audio_file = f"temp_audio_{idx}.mp3"
            asyncio.run(generate_audio(line, selected_voice, audio_file))
            audio_clip = AudioFileClip(audio_file)
            duration = audio_clip.duration
            
            # 2. Generate Image
            image = get_pollinations_image(f"cinematic documentary style, {line}")
            image_np = np.array(image)
            
            # 3. Create Video Clip
            img_clip = ImageClip(image_np).set_duration(duration)
            img_clip = img_clip.resize(width=1280, height=720)
            img_clip = img_clip.set_audio(audio_clip)
            
            clips.append(img_clip)
            progress_bar.progress((idx + 1) / len(lines))
            
        st.write("Finalizing video...")
        final_clip = concatenate_videoclips(clips, method="compose")
        output_video = "output_video.mp4"
        final_clip.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")
        
        st.success("Video generated successfully!")
        st.video(output_video)
