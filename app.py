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


# 3. Fetch YouTube Landscape (16:9) Media
def fetch_media_for_scene(scene_prompt_urdu: str, index: int):
  english_prompt = translate_to_english(scene_prompt_urdu)
  query = urllib.parse.quote(english_prompt)

  # Step A: Pexels Landscape Video
  try:
    headers = {"Authorization": PEXELS_API_KEY}
    video_url = f"https://api.pexels.com/videos/search?query={query}&orientation=landscape&per_page=1"
    res = requests.get(video_url, headers=headers, timeout=10).json()

    if res.get("videos") and len(res["videos"]) > 0:
      video_files = res["videos"][0]["video_files"]
      download_url = next(
          (
              v["link"]
              for v in video_files
              if v.get("width", 0) > v.get("height", 0)
          ),
          video_files[0]["link"],
      )
      vid_data = requests.get(download_url, timeout=20).content
      vid_path = f"media_{index:03d}.mp4"
      with open(vid_path, "wb") as f:
        f.write(vid_data)
      return vid_path, "video"
  except Exception:
    pass

  # Step B: Pexels Landscape Photo
  try:
    headers = {"Authorization": PEXELS_API_KEY}
    photo_url = f"https://api.pexels.com/v1/search?query={query}&orientation=landscape&per_page=1"
    res = requests.get(photo_url, headers=headers, timeout=10).json()

    if res.get("photos") and len(res["photos"]) > 0:
      img_url = res["photos"][0]["src"]["large2x"]
      img_data = requests.get(img_url, timeout=15).content
      img_path = f"media_{index:03d}.jpg"
      with open(img_path, "wb") as f:
        f.write(img_data)
      return img_path, "image"
  except Exception:
    pass

  # Step C: AI Photo Fallback
  quality_boost = (
      "national geographic cinematic documentary photograph, 8k, real life"
  )
  final_prompt = urllib.parse.quote(f"{english_prompt}, {quality_boost}")
  url = f"https://image.pollinations.ai/prompt/{final_prompt}?width=1280&height=720&model=flux-realism&nologo=true&seed={index*10}"

  try:
    res = requests.get(url, timeout=25)
    if res.status_code == 200:
      img_path = f"media_{index:03d}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path, "image"
  except Exception:
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


# 5. FFmpeg Video Stitcher (Strict 16:9 Format)
def create_mixed_documentary(media_items, audio_path, output_video_path):
  total_duration = get_audio_duration(audio_path)
  num_items = len(media_items)
  duration_per_item = total_duration / num_items

  temp_clips = []

  for i, (path, media_type) in enumerate(media_items):
    out_clip = f"clip_{i:03d}.mp4"
    if media_type == "image":
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
          "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
          out_clip,
      ]
    else:
      cmd = [
          "ffmpeg",
          "-y",
          "-stream_loop",
          "-1",
          "-i",
          path,
          "-t",
          f"{duration_per_item:.2f}",
          "-vf",
          "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
          "-an",
          out_clip,
      ]
    subprocess.run(cmd, check=True)
    temp_clips.append(out_clip)

  # Concat File Creation
  with open("input_clips.txt", "w") as f:
    for clip in temp_clips:
      f.write(f"file '{clip}'\n")

  # Merge Visuals & Audio
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
      "copy",
      "-c:a",
      "aac",
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
    with st.spinner("Processing 7-8 second scene transitions..."):
      try:
        # Step 1: Voice Generation
        audio_file = "temp_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split script (~14 words = approx 7 to 8 seconds per scene)
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
          st.error("Failed to fetch visuals. Please try again.")
        else:
          # Step 4: Final Rendering
          final_video = "final_documentary.mp4"
          create_mixed_documentary(media_list, audio_file, final_video)

          st.success("✅ YouTube Video with 7-8s Scenes Ready!")
          st.video(final_video)

          # Final Cleanup
          for path, _ in media_list:
            if os.path.exists(path):
              os.remove(path)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error generating video: {e}")
