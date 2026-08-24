import asyncio
import os
import re
import subprocess
import urllib.parse
from deep_translator import GoogleTranslator
import edge_tts
import requests
import streamlit as st

# Page Setup
st.set_page_config(
    page_title="Documentary Video Generator", layout="centered"
)
st.title("🎬 Professional YouTube Urdu Documentary Generator")

# Embedded Pexels API Key
PEXELS_API_KEY = (
    "3Z0S20rEAy3MB9A2IFJhG25UkJzFksRJBB4iAAN9g9sZ9ha0eqTcJslZ"
)

# Voice Selection
selected_voice = st.selectbox(
    "Select Voice", options=["ur-PK-AsadNeural (Urdu Male Voice)"]
)
voice_code = selected_voice.split(" ")[0]

# Script Input Box
text_input = st.text_area("Enter your full Urdu script here:", height=180)


# 1. Deep Dark Voice Generator (-8Hz Pitch)
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  CUSTOM_PITCH = "-8Hz"  # Deep voice
  CUSTOM_RATE = "+5%"  # Natural pacing
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


# 3. Fetch Media (AI Image Generation)
def fetch_media_for_scene(scene_prompt_urdu: str, index: int):
  english_prompt = translate_to_english(scene_prompt_urdu)
  query = urllib.parse.quote(english_prompt)
  
  headers_req = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  }

  quality_boost = (
      "cinematic documentary masterclass photography, highly detailed, 8k resolution, dramatic lighting, photorealistic"
  )
  final_prompt = urllib.parse.quote(f"{english_prompt}, {quality_boost}")
  url = f"https://image.pollinations.ai/prompt/{final_prompt}?width=1280&height=720&model=flux-realism&nologo=true&seed={index*15}"

  try:
    res = requests.get(url, headers=headers_req, timeout=25)
    if res.status_code == 200 and len(res.content) > 5000:
      img_path = f"media_{index:03d}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path, "image"
  except Exception:
    pass

  return None, None


# 4. Audio Duration Helper
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


# 5. FFmpeg Video Stitcher (Clean Cinematic Style without broken font boxes)
def create_mixed_documentary(media_items, audio_path, output_video_path):
  total_duration = get_audio_duration(audio_path)
  num_items = len(media_items)
  duration_per_item = total_duration / num_items

  temp_clips = []

  for i, (path, media_type) in enumerate(media_items):
    out_clip = f"clip_{i:03d}.mp4"
    
    # Clean and error-free filter chain (No broken text boxes, pure cinematic visuals)
    filter_chain = (
        "scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
        "fps=25,format=yuv420p"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        path,
        "-t",
        f"{duration_per_item:.2f}",
        "-vf",
        filter_chain,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        out_clip,
    ]
    
    subprocess.run(cmd, check=True)
    temp_clips.append(out_clip)

  # Concat File Creation
  with open("input_clips.txt", "w") as f:
    for clip in temp_clips:
      f.write(f"file '{clip}'\n")

  # Merge Visuals & Audio with standard encoding for Chromebook playback
  cmd = [
      "ffmpeg",
      "-y",
      "-f",
      "concat",
      "-safe",
      "0",
      "-i",
      "input_clips.txt",
      "-i",
      audio_path,
      "-c:v",
      "libx264",
      "-c:a",
      "aac",
      "-pix_fmt",
      "yuv420p",
      "-t",
      str(total_duration),
      output_video_path,
  ]
  subprocess.run(cmd, check=True)

  # Cleanup
  if os.path.exists("input_clips.txt"):
    os.remove("input_clips.txt")
  for clip in temp_clips:
    if os.path.exists(clip):
      os.remove(clip)


# Main Workflow
if st.button("Generate Complete Video"):
  if not text_input.strip():
    st.warning("Please enter your script first!")
  else:
    with st.spinner("Generating AI cinematic visuals, deep voice, and rendering video..."):
      try:
        # Step 1: Voice Generation
        audio_file = "temp_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split script (~14 words per scene)
        raw_words = text_input.strip().split()
        chunk_size = 14
        sentences = [
            " ".join(raw_words[i : i + chunk_size])
            for i in range(0, len(raw_words), chunk_size)
        ]

        media_list = []

        # Step 3: Fetch Media
        for i, sentence in enumerate(sentences):
          m_path, m_type = fetch_media_for_scene(sentence, i)
          if m_path:
            media_list.append((m_path, m_type))

        if not media_list:
          st.error("Failed to generate visuals. Please try again.")
        else:
          # Step 4: Final Rendering
          final_video = "final_documentary.mp4"
          create_mixed_documentary(media_list, audio_file, final_video)

          st.success("✅ Professional Cinematic Documentary Ready!")
          st.video(final_video)

          # Final Cleanup
          for path, _ in media_list:
            if os.path.exists(path):
              os.remove(path)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error generating video: {e}")
