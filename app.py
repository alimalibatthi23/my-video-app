import asyncio
import os
import re
import urllib.parse
from deep_translator import GoogleTranslator
import edge_tts
from moviepy.editor import AudioFileClip, ImageSequenceClip
import requests
import streamlit as st

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


# 1. Deep Urdu Voice Generator
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  CUSTOM_PITCH = "-15Hz"
  CUSTOM_RATE = "-12%"
  communicate = edge_tts.Communicate(
      text, preferred_voice, pitch=CUSTOM_PITCH, rate=CUSTOM_RATE
  )
  await communicate.save(output_filename)
  return True


# 2. Translate Urdu to English for Accurate AI Prompting
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
  # Urdu to English translation for perfect image match
  english_prompt = translate_to_english(scene_prompt_urdu)

  quality_boost = (
      ", 8k resolution, photorealistic cinematic documentary shot, highly"
      " detailed, national geographic style photography, 35mm photograph,"
      " real life, NO anime, NO cartoon, NO illustration"
  )
  final_prompt = english_prompt + quality_boost
  encoded_prompt = urllib.parse.quote(final_prompt)

  # Flux Engine for High Realism
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


# 4. Merge Audio and Images into MP4 Video
def create_video(image_paths, audio_path, output_video_path):
  audio_clip = AudioFileClip(audio_path)
  audio_duration = audio_clip.duration

  num_images = len(image_paths)
  duration_per_image = max(3.0, audio_duration / num_images)

  video_clip = ImageSequenceClip(
      image_paths, durations=[duration_per_image] * num_images
  )
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
        "Translating scenes, generating 8K realism & rendering MP4 video..."
    ):
      try:
        # Step 1: Generate Deep Urdu Voice
        audio_file = "temp_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split Script into Sentences
        sentences = [
            s.strip()
            for s in re.split(r"[।!?,\n]+", text_input)
            if len(s.strip()) > 5
        ]
        image_files = []

        # Step 3: Generate Matched Realistic Images
        for i, sentence in enumerate(sentences):
          img = generate_realistic_image(sentence, i)
          if img:
            image_files.append(img)

        if not image_files:
          st.error("Failed to generate visuals. Please try again.")
        else:
          # Step 4: Combine into One Single MP4 Video
          final_video = "final_documentary.mp4"
          create_video(image_files, audio_file, final_video)

          st.success("✅ Complete Documentary Video Created!")
          st.video(final_video)

          # Clean up temporary files
          for img in image_files:
            if os.path.exists(img):
              os.remove(img)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error: {e}")
