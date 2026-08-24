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


# 3. Smart Pexels Stock Video Fetcher & Ultra HD Fallback Image
def fetch_media_for_scene(scene_prompt_urdu: str, index: int):
  english_context = translate_to_english(scene_prompt_urdu)
  query = urllib.parse.quote(english_context[:40])
  
  headers = {
      "Authorization": PEXELS_API_KEY
  }
  url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"

  try:
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
      data = res.json()
      videos = data.get("videos", [])
      if videos:
        video_files = videos[0].get("video_files", [])
        hd_file = next((v for v in video_files if v.get("quality") == "hd" or v.get("width", 0) >= 1280), None)
        if not hd_file and video_files:
          hd_file = video_files[0]
        
        if hd_file and "link" in hd_file:
          vid_url = hd_file["link"]
          vid_res = requests.get(vid_url, timeout=25)
          if vid_res.status_code == 200 and len(vid_res.content) > 10000:
            vid_path = f"media_{index:03d}.mp4"
            with open(vid_path, "wb") as f:
              f.write(vid_res.content)
            return vid_path, "video"
  except Exception:
    pass

  # Fallback to Ultra HD AI Image with crisp English text capability if video fails
  quality_boost = "cinematic documentary masterclass photography, 8k resolution, photorealistic, sharp focus"
  final_prompt = urllib.parse.quote(f"{english_context}, {quality_boost}")
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


# 5. FFmpeg Stitcher with Clean Translated Subtitles (No broken boxes)
def create_mixed_documentary(media_items_with_text, audio_path, output_video_path):
  total_duration = get_audio_duration(audio_path)
  num_items = len(media_items_with_text)
  
  ideal_duration_per_item = total_duration / num_items
  duration_per_item = min(ideal_duration_per_item, 7.0)

  temp_clips = []

  for i, (path, media_type, scene_text) in enumerate(media_items_with_text):
    out_clip = f"clip_{i:03d}.mp4"
    
    # Translate script chunk to English for clean, professional subtitles without font glitching
    english_subtitle = translate_to_english(scene_text)
    clean_text = english_subtitle.replace("'", "").replace('"', "").replace(":", "-")
    if len(clean_text) > 50:
      clean_text = clean_text[:47] + "..."

    # Crisp text filter using standard English font to ensure zero broken boxes
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
    
    subprocess.run(cmd, check=True)
    temp_clips.append(out_clip)

  # Concat File Creation
  with open("input_clips.txt", "w") as f:
    for clip in temp_clips:
      f.write(f"file '{clip}'\n")

  # Merge Visuals & Audio for seamless Chromebook playback
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
    with st.spinner("Generating professional documentary with mixed media & clean subtitles..."):
      try:
        # Step 1: Voice Generation
        audio_file = "temp_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split script into perfect context chunks
        raw_words = text_input.strip().split()
        chunk_size = 7
        sentences = [
            " ".join(raw_words[i : i + chunk_size])
            for i in range(0, len(raw_words), chunk_size)
        ]

        media_list_with_text = []

        # Step 3: Fetch Media matching context
        for i, sentence in enumerate(sentences):
          m_path, m_type = fetch_media_for_scene(sentence, i)
          if m_path:
            media_list_with_text.append((m_path, m_type, sentence))

        if not media_list_with_text:
          st.error("Failed to generate visuals. Please try again.")
        else:
          # Step 4: Final Rendering
          final_video = "final_documentary.mp4"
          create_mixed_documentary(media_list_with_text, audio_file, final_video)

          st.success("✅ Professional High-Quality Documentary Ready!")
          st.video(final_video)

          # Final Cleanup
          for path, _, _ in media_list_with_text:
            if os.path.exists(path):
              os.remove(path)
          if os.path.exists(audio_file):
            os.remove(audio_file)

      except Exception as e:
        st.error(f"Error generating video: {e}")
