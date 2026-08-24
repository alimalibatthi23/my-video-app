import asyncio
import os
import re
import urllib.parse
import edge_tts
from moviepy.editor import AudioFileClip, ImageSequenceClip
import requests
import streamlit as st

st.set_page_config(
    page_title="Documentary Video Generator", layout="centered"
)
st.title("🎬 Complete Documentary Video Generator")

selected_voice = st.selectbox(
    "Select Voice", options=["ur-PK-AsadNeural (Urdu Male Deep Voice)"]
)
voice_code = selected_voice.split(" ")[0]

text_input = st.text_area(
    "Enter your full documentary script here:", height=180
)


# 1. Deep Voice Generator
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  CUSTOM_PITCH = "-15Hz"
  CUSTOM_RATE = "-12%"
  communicate = edge_tts.Communicate(
      text, preferred_voice, pitch=CUSTOM_PITCH, rate=CUSTOM_RATE
  )
  await communicate.save(output_filename)
  return True


# 2. 8K Realistic Image Generator
def generate_realistic_image(scene_prompt: str, index: int):
  quality_boost = (
      ", 8k resolution, photorealistic, cinematic lighting, documentary"
      " scene, highly detailed, real life photography"
  )
  final_prompt = scene_prompt + quality_boost
  encoded_prompt = urllib.parse.quote(final_prompt)

  url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true"

  try:
    res = requests.get(url, timeout=30)
    if res.status_code == 200:
      img_path = f"temp_scene_{index}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path
  except Exception:
    return None


# 3. Combine Audio + Images into MP4 Video
def create_video(image_paths, audio_path, output_video_path):
  audio_clip = AudioFileClip(audio_path)
  audio_duration = audio_clip.duration

  # Calculate duration per image so all images cover full audio length
  num_images = len(image_paths)
  duration_per_image = max(3.0, audio_duration / num_images)

  # Create Video Clip
  video_clip = ImageSequenceClip(image_paths, durations=[duration_per_image] * num_images)
  video_clip = video_clip.set_audio(audio_clip)

  # Save Final MP4 Video
  video_clip.write_videofile(
      output_video_path, fps=24, codec="libx264", audio_codec="aac"
  )

  # Close clips to free memory
  audio_clip.close()
  video_clip.close()


# Main Action
if st.button("Generate Complete Video"):
  if not text_input.strip():
    st.warning("Please enter your script first!")
  else:
    with st.spinner("Generating voice, scenes, and rendering final MP4 video..."):
      try:
        # Step 1: Generate Audio
        audio_file = "temp_audio.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split Script and Generate Images
        sentences = [
            s.strip()
            for s in re.split(r"[।!?,\n]+", text_input)
            if len(s.strip()) > 5
        ]
        image_files = []

        for i, sentence in enumerate(sentences):
          img = generate_realistic_image(sentence, i)
          if img:
            image_files.append(img)

        # Fallback if no images were generated
        if not image_files:
          st.error("Could not generate images for the video.")
        else:
          # Step 3: Render MP4 Video
          final_video = "final_documentary.mp4"
          create_video(image_files, audio_file, final_video)

          # Step 4: Show Final Combined Video Output
          st.success("✅ Final Documentary Video Ready!")
          st.video(final_video)

          # Clean up temporary images
          for img in image_files:
            if os.path.exists(img):
              os.remove(img)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error generating video: {e}")
