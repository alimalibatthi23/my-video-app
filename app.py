import asyncio
import os
import re
import subprocess
import urllib.parse
from deep_translator import GoogleTranslator
import edge_tts
import requests
import streamlit as st

st.set_page_config(
    page_title="Documentary Video Generator", layout="centered"
)
st.title("🎬 Professional Urdu Documentary Video Generator")

selected_voice = st.selectbox(
    "Select Voice", options=["ur-PK-AsadNeural (Urdu Male Voice)"]
)
voice_code = selected_voice.split(" ")[0]

text_input = st.text_area("Enter your full Urdu script here:", height=180)


# 1. Clear, Fast & Natural Urdu Voice Generator
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  # Normal speed & clear voice (no pitch lag)
  CUSTOM_PITCH = "+0Hz"
  CUSTOM_RATE = "+5%"  # आवाज़ की स्पीड थोड़ी बढ़ा दी है ताकि स्लो न लगे
  communicate = edge_tts.Communicate(
      text, preferred_voice, pitch=CUSTOM_PITCH, rate=CUSTOM_RATE
  )
  await communicate.save(output_filename)
  return True


# 2. Urdu to English Translation
def translate_to_english(urdu_text: str):
  try:
    return GoogleTranslator(source="auto", target="en").translate(urdu_text)
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
      img_path = f"scene_{index:03d}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path
  except Exception:
    return None


# 4. Get Audio Duration
def get_audio_duration(audio_path):
  cmd = [
      "ffprobe",
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "default=noprint_wrappers=1:nokey=1",
      audio_path,
  ]
  result = subprocess.run(
      cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
  )
  return float(result.stdout.strip())


# 5. FFmpeg Video Creator with Exact Image Timing
def create_ffmpeg_video(image_paths, audio_path, output_video_path):
  total_duration = get_audio_duration(audio_path)
  num_images = len(image_paths)
  duration_per_image = total_duration / num_images

  # Create FFmpeg concat file with exact timing per scene
  with open("input.txt", "w") as f:
    for img in image_paths:
      f.write(f"file '{img}'\n")
      f.write(f"duration {duration_per_image:.2f}\n")
    f.write(f"file '{image_paths[-1]}'\n")

  # Run FFmpeg command
  cmd = [
      "ffmpeg",
      "-y",
      "-f",
      "concat",
      "-safe",
      "0",
      "-i",
      "input.txt",
      "-i",
      audio_path,
      "-c:v",
      "libx264",
      "-vf",
      "fps=24,format=yuv420p",
      "-c:a",
      "aac",
      "-shortest",
      output_video_path,
  ]
  subprocess.run(cmd, check=True)

  if os.path.exists("input.txt"):
    os.remove("input.txt")


# Main Workflow
if st.button("Generate Complete Video"):
  if not text_input.strip():
    st.warning("Please enter your script first!")
  else:
    with st.spinner("Generating clear voice & matched visuals..."):
      try:
        # Step 1: Audio Generation
        audio_file = "temp_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split Script Line by Line
        raw_lines = re.split(r"[\n।!?,\.-]+", text_input)
        sentences = [l.strip() for l in raw_lines if len(l.strip()) > 3]

        if not sentences:
          sentences = [text_input.strip()]

        image_files = []

        # Step 3: Images Generation
        for i, sentence in enumerate(sentences):
          img = generate_realistic_image(sentence, i)
          if img:
            image_files.append(img)

        if not image_files:
          st.error("Failed to generate visuals. Please try again.")
        else:
          # Step 4: Render Synchronized MP4
          final_video = "final_documentary.mp4"
          create_ffmpeg_video(image_files, audio_file, final_video)

          st.success("✅ Complete Video Generated Successfully!")
          st.video(final_video)

          # Cleanup
          for img in image_files:
            if os.path.exists(img):
              os.remove(img)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error: {e}")
