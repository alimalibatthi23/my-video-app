import streamlit as st
import asyncio
import edge_tts
from gtts import gTTS
import os
import requests
import io
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
import numpy as np

st.set_page_config(page_title="Deep Voice AI Video Generator", layout="wide")

st.title("🎬 Documentary-Style AI Video Generator")
st.write("Generate high-impact, realistic documentary videos with deep authoritative voices and cinematic visuals.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Settings")

# Language / Deep Voice Selection
language = st.sidebar.selectbox("Select Voice (Documentary Deep Voices)", [
    "Urdu Deep Male (Asad)",
    "Hindi Deep Male (Madhur)",
    "English US Deep Male (Christopher)",
    "English UK Deep Male (Ryan)"
])

voice_mapping = {
    "Urdu Deep Male (Asad)": "ur-PK-AsadNeural",
    "Hindi Deep Male (Madhur)": "hi-IN-MadhurNeural",
    "English US Deep Male (Christopher)": "en-US-ChristopherNeural",
    "English UK Deep Male (Ryan)": "en-GB-RyanNeural"
}

aspect_ratio = st.sidebar.selectbox("Aspect Ratio", ["16:9 (YouTube Long)", "9:16 (Shorts/Reels)"])

# --- INPUT SECTION ---
script_input = st.text_area("✍️ Enter Your Script / Story Here", height=200, placeholder="Paste your video script paragraph by paragraph...")

# Function to generate Deep Authoritative Voice (-10Hz pitch makes it deep & serious)
async def generate_voice(text, voice_name, output_path):
    communicate = edge_tts.Communicate(
        text, 
        voice_name, 
        pitch="-10Hz", 
        rate="-5%"
    )
    await communicate.save(output_path)

def generate_photorealistic_image(prompt, index):
    # Enforce serious, powerful, photorealistic visual style
    enhanced_prompt = f"{prompt}, photorealistic, 8k resolution, cinematic lighting, dramatic atmosphere, realistic photography, highly detailed, non-cartoon, serious mood"
    
    # Pollinations AI Endpoint (Free & High Quality)
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(enhanced_prompt)}?width=1280&height=720&nologo=true&seed={index+100}"
    
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(io.BytesIO(response.content))
        image_path = f"scene_{index}.png"
        image.save(image_path)
        return image_path
    else:
        return None

if st.button("🚀 Generate Video"):
    if not script_input.strip():
        st.error("Please enter a script first!")
    else:
        status = st.empty()
        status.info("⏳ Processing your script and generating deep voiceover...")

        # Split script into scenes
        scenes = [s.strip() for s in script_input.split('\n') if s.strip()]
        
        selected_voice = voice_mapping[language]
        video_clips = []

        for idx, scene_text in enumerate(scenes):
            status.info(f"🎨 Generating Scene {idx+1}/{len(scenes)}: Creating photorealistic image and deep voice...")
            
            # 1. Voiceover Generation
            audio_path = f"audio_{idx}.mp3"
            try:
                asyncio.run(generate_voice(scene_text, selected_voice, audio_path))
            except Exception as e:
                # Fallback to gTTS if edge_tts fails
                tts = gTTS(text=scene_text, lang='en')
                tts.save(audio_path)

            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration

            # 2. Photorealistic Image Generation
            img_path = generate_photorealistic_image(scene_text, idx)

            if img_path and os.path.exists(img_path):
                img_clip = ImageClip(img_path).set_duration(duration)
                
                # Apply Ken Burns Zoom Effect for dynamic motion
                img_clip = img_clip.resize(lambda t: 1 + 0.04 * t)  # Gentle slow zoom
                img_clip = img_clip.set_position(('center', 'center'))

                # Combine Audio and Visual
                clip = img_clip.set_audio(audio_clip)
                video_clips.append(clip)

        if video_clips:
            status.info("🎬 Rendering final video (this may take a couple of minutes)...")
            final_clip = concatenate_videoclips(video_clips, method="compose")
            output_filename = "final_output_video.mp4"
            final_clip.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac")

            status.success("✅ Video successfully generated!")
            st.video(output_filename)

            with open(output_filename, "rb") as file:
                st.download_button(
                    label="📥 Download Video",
                    data=file,
                    file_name="generated_video.mp4",
                    mime="video/mp4"
                )
