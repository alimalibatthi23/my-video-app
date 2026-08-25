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
st.title("🎬 Professional YouTube Documentary Generator")

# Embedded Pexels API Key
PEXELS_API_KEY = (
    "3Z0S20rEAy3MB9A2IFJhG25UkJzFksRJBB4iAAN9g9sZ9ha0eqTcJslZ"
)

# --- NEW: Language Selection Buttons/Radio ---
language_option = st.radio(
    "Select Output Language for Voiceover & Subtitles:",
    options=["Urdu (اردو)", "English (انگریزی)"],
    horizontal=True
)

# Voice Configuration based on Selection (US Documentary Heavy/Dark Style)
if "Urdu" in language_option:
  voice_code = "ur-PK-AsadNeural"  # Urdu Male Voice
else:
  # US English deep/documentary style male voice
  voice_code = "en-US-ChristopherNeural" 

# Script/Prompt Input Box (English Input for Best Media Fetching)
text_input = st.text_area(
    "Enter your detailed English script or prompt here (App will fetch 4K/HD visuals based on this):", 
    height=180
)


# 1. Deep Dark Voice Generator (-8Hz Pitch for Heavy Documentary Vibe)
async def generate_audio(text: str, output_filename: str, preferred_voice: str, target_lang: str):
  # Agar user ne Urdu select kiya hai aur input English hai, toh usay Urdu mein translate kar ke bolیں گے
  text_to_speak = text
  if "Urdu" in target_lang:
    try:
      text_to_speak = GoogleTranslator(source="en", target="ur").translate(text)
    except Exception:
      pass

  CUSTOM_PITCH = "-8Hz"  # Bhari aur dark documentary voice ke liye
  CUSTOM_RATE = "+0%"
  
  communicate = edge_tts.Communicate(
      text_to_speak, preferred_voice, pitch=CUSTOM_PITCH, rate=CUSTOM_RATE
  )
  await communicate.save(output_filename)
  return True, text_to_speak


# 2. Smart Pexels Stock Video Fetcher & Ultra HD Fallback Image
def fetch_media_for_scene(scene_prompt: str, index: int):
  # English prompt seedha Pexels ko jaye ga taake behtareen 4K/HD video aaye
  query = urllib.parse.quote(scene_prompt[:100])
  
  headers = {
      "Authorization": PEXELS_API_KEY
  }
  url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"

  try:
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
      data = res.json()
      videos = data.get("videos", [])
      if videos:
        best_file = None
        max_width = 0
        
        for video in videos:
          video_files = video.get("video_files", [])
          for v in video_files:
            width = v.get("width", 0)
            if width >= max_width and "link" in v:
              max_width = width
              best_file = v
        
        if best_file and "link" in best_file:
          vid_url = best_file["link"]
          vid_res = requests.get(vid_url, timeout=25)
          if vid_res.status_code == 200 and len(vid_res.content) > 10000:
            vid_path = f"media_{index:03d}.mp4"
            with open(vid_path, "wb") as f:
              f.write(vid_res.content)
            return vid_path, "video"
  except Exception:
    pass

  # Fallback to Pollinations AI with cinematic 8K parameters
  quality_boost = "cinematic documentary masterclass photography, 8k resolution, photorealistic, sharp focus, highly detailed"
  final_prompt = urllib.parse.quote(f"{scene_prompt}, {quality_boost}")
  img_url = f"https://image.pollinations.ai/prompt/{final_prompt}?width=1280&height=720&model=flux&nologo=true&seed={index*55}"

  try:
    img_res = requests.get(img_url, timeout=25)
    if img_res.status_code == 200 and len(img_res.content) > 8000:
      img_path = f"media_{index:03d}.jpg"
      with open(img_path, "wb") as f:
        f.write(img_res.content)
      return img_path, "image"
  except Exception:
    pass

  return None, None


# 3. Audio Duration Helper
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
      cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
  )
  return float(result.stdout.strip())


# 4. FFmpeg Stitcher with Dynamic Subtitles
def create_mixed_documentary(media_items_with_text, audio_path, output_video_path, target_lang):
  total_duration = get_audio_duration(audio_path)
  num_items = len(media_items_with_text)
  
  ideal_duration_per_item = total_duration / num_items
  duration_per_item = min(ideal_duration_per_item, 7.0)

  temp_clips = []

  for i, (path, media_type, scene_text) in enumerate(media_items_with_text):
    out_clip = f"clip_{i:03d}.mp4"
    
    # Subtitle ki zuban tay karna
    sub_text = scene_text
    if "Urdu" in target_lang:
      try:
        sub_text = GoogleTranslator(source="en", target="ur").translate(scene_text)
      except Exception:
        pass

    clean_text = sub_text.replace("'", "").replace('"', "").replace(":", "-")
    if len(clean_text) > 55:
      clean_text = clean_text[:52] + "..."

    filter_chain = (
        "scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
        f"drawtext=text='{clean_text}':fontcolor=white:fontsize=26:box=1:boxcolor=black@0.6:boxborderw=5:x=(w-text_w)/2:y=630,"
        "fps=25,format=yuv420p"
    )

    if media_type == "video":
      cmd = [
          "ffmpeg",
          "-y",
          "-i",
          path,
          "-t",
          f"{duration_per_item:.2f}",
          "-vf",
          filter_chain,
          "-c:v", "libx264",
          "-pix_fmt", "yuv420p",
          "-an",
          out_clip,
      ]
    else:
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
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    temp_clips.append(out_clip)

  with open("input_clips.txt", "w") as f:
    for clip in temp_clips:
      f.write(f"file '{clip}'\n")

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
  subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

  if os.path.exists("input_clips.txt"):
    os.remove("input_clips.txt")
  for clip in temp_clips:
    if os.path.exists(clip):
      os.remove(clip)


# Main Workflow
if st.button("Generate Complete Video"):
  if not text_input.strip():
    st.warning("Please enter your English script/prompt first!")
  else:
    with st.spinner("Generating professional US-style documentary with high-res visuals..."):
      try:
        audio_file = "temp_voice.mp3"
        success_audio, spoken_text = asyncio.run(generate_audio(text_input, audio_file, voice_code, language_option))

        raw_words = text_input.strip().split()
        chunk_size = 12
        sentences = [
            " ".join(raw_words[i : i + chunk_size])
            for i in range(0, len(raw_words), chunk_size)
        ]

        media_list_with_text = []

        for i, sentence in enumerate(sentences):
          m_path, m_type = fetch_media_for_scene(sentence, i)
          if m_path:
            media_list_with_text.append((m_path, m_type, sentence))

        if not media_list_with_text:
          st.error("Failed to generate visuals. Please try again.")
        else:
          final_video = "final_documentary.mp4"
          create_mixed_documentary(media_list_with_text, audio_file, final_video, language_option)

          st.success("✅ Professional Documentary Ready!")
          st.video(final_video)

          for path, _, _ in media_list_with_text:
            if os.path.exists(path):
              os.remove(path)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error generating video: {e}")
