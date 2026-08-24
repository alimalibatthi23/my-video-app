import asyncio
import os
import re
import urllib.parse
from deep_translator import GoogleTranslator
import edge_tts
import requests
import streamlit as st

# Safe Imports for MoviePy Compatibility (v1 & v2)
try:
  from moviepy.editor import (
      AudioFileClip,
      ConcatenateVideoClips,
      ImageClip,
  )
except ImportError:
  from moviepy.audio.io.AudioFileClip import AudioFileClip
  from moviepy.video.compositing.concatenate import (
      concatenate_videoclips as ConcatenateVideoClips,
  )
  from moviepy.video.VideoClip import ImageClip

st.set_page_config(
    page_title="Documentary Video Generator", layout="centered"
)
st.title("🎬 Professional Urdu Documentary Video Generator")

selected_voice = st.selectbox(
    "Select Voice", options=["ur-PK-AsadNeural (Urdu Male Deep Voice)"]
)
voice_code = selected_voice.split(" ")[0]

text_input = st.text_area(
    "Enter your full Urdu script here:", height=180
)


# 1. Clear & Deep Urdu Voice Generator
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  CUSTOM_PITCH = "-10Hz"  # भारी डॉक्यूमेंट्री आवाज़
  CUSTOM_RATE = "-5%"  # नेचुरल स्पीड
  communicate = edge_tts.Communicate(
      text, preferred_voice, pitch=CUSTOM_PITCH, rate=CUSTOM_RATE
  )
  await communicate.save(output_filename)
  return True


# 2. Urdu to English Translation for Accurate Visuals
def translate_to_english(urdu_text: str):
  try:
    translated = GoogleTranslator(source="auto", target="en").translate(
        urdu_text
    )
    return translated
  except Exception:
    return urdu_text


# 3. 8K Realistic Image Generator
def generate_realistic_image(scene_prompt_urdu: str, index: int):
  english_prompt = translate_to_english(scene_prompt_urdu)
  quality_boost = (
      ", 8k resolution, photorealistic cinematic documentary shot, highly"
      " detailed, national geographic photography, real life, 35mm lens, NO"
      " anime, NO cartoon"
  )
  final_prompt = english_prompt + quality_boost
  encoded_prompt = urllib.parse.quote(final_prompt)

  url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true"

  try:
    res = requests.get(url, timeout=35)
    if res.status_code == 200:
      img_path = f"scene_{index}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path
  except Exception:
    return None


# 4. Multi-Image Frame-by-Frame Sync Video Rendering
def create_synchronized_video(image_paths, audio_path, output_video_path):
  audio_clip = AudioFileClip(audio_path)
  total_duration = audio_clip.duration

  num_images = len(image_paths)
  duration_per_image = total_duration / num_images

  clips = []
  for img_path in image_paths:
    img_clip = ImageClip(img_path).set_duration(duration_per_image)
    clips.append(img_clip)

  video_clip = ConcatenateVideoClips(clips, method="compose")
  video_clip = video_clip.set_audio(audio_clip)

  video_clip.write_videofile(
      output_video_path, fps=24, codec="libx264", audio_codec="aac"
  )

  audio_clip.close()
  video_clip.close()


# Main Workflow
if st.button("Generate Complete Video"):
  if not text_input.strip():
    st.warning("Please enter your script first!")
  else:
    with st.spinner(
        "Generating deep voice, matching visuals & rendering MP4..."
    ):
      try:
        # Step 1: Generate Clear Audio
        audio_file = "temp_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Clean Split Script Line by Line
        raw_lines = re.split(r"[\n।!?\.]+", text_input)
        sentences = [l.strip() for l in raw_lines if len(l.strip()) > 3]

        if not sentences:
          sentences = [text_input.strip()]

        image_files = []

        # Step 3: Generate Matched Images for Each Line
        for i, sentence in enumerate(sentences):
          img = generate_realistic_image(sentence, i)
          if img:
            image_files.append(img)

        if not image_files:
          st.error("Failed to generate visuals. Please try again.")
        else:
          # Step 4: Render Multi-Image Synchronized MP4
          final_video = "final_documentary.mp4"
          create_synchronized_video(image_files, audio_file, final_video)

          st.success("✅ Synchronized Multi-Image Video Created!")
          st.video(final_video)

          # Cleanup
          for img in image_files:
            if os.path.exists(img):
              os.remove(img)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error: {e}")
