import asyncio
import os
import re
import urllib.parse
import edge_tts
import requests
import streamlit as st

st.set_page_config(
    page_title="Documentary Video Generator", layout="centered"
)
st.title("🎬 Documentary Audio & Auto-Slide Video Generator")

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

  # Using Flux Model for Realistic Output
  url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true"

  try:
    res = requests.get(url, timeout=30)
    if res.status_code == 200:
      img_path = f"scene_{index}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path
  except Exception:
    return None


# Action Button
if st.button("Generate Video Content"):
  if not text_input.strip():
    st.warning("Please enter your script first!")
  else:
    with st.spinner("Generating deep audio and 8K documentary scenes..."):
      try:
        # Step 1: Generate Audio
        audio_file = "output_voice.mp3"
        asyncio.run(generate_audio(text_input, audio_file, voice_code))

        # Step 2: Split Text into Scenes
        sentences = [
            s.strip()
            for s in re.split(r"[।!?,\n]+", text_input)
            if len(s.strip()) > 5
        ]
        image_files = []

        for i, sentence in enumerate(sentences):
          img = generate_realistic_image(sentence, i)
          if img:
            image_files.append((img, sentence))

        st.success("✅ Content Generated Successfully!")

        # Display Audio First
        st.subheader("🔊 Documentary Voice")
        st.audio(audio_file)

        # Display Realistic Scenes Sequence
        st.subheader("🖼️ Realistic 8K Scenes (Changes per line)")
        cols = st.columns(2)
        for idx, (img_path, caption_text) in enumerate(image_files):
          with cols[idx % 2]:
            st.image(
                img_path,
                caption=f"Scene {idx+1}: {caption_text[:40]}...",
                use_container_width=True,
            )

      except Exception as e:
        st.error(f"Error: {e}")
