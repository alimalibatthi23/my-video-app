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
st.title("🎬 Documentary Audio & Realistic Multi-Image Generator")

selected_voice = st.selectbox(
    "Select Voice", options=["ur-PK-AsadNeural (Urdu Male Documentary Voice)"]
)
voice_code = selected_voice.split(" ")[0]

text_input = st.text_area(
    "Enter your full documentary script here:", height=180
)


# Voice Generator
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  CUSTOM_PITCH = "-15Hz"
  CUSTOM_RATE = "-12%"
  communicate = edge_tts.Communicate(
      text, preferred_voice, pitch=CUSTOM_PITCH, rate=CUSTOM_RATE
  )
  await communicate.save(output_filename)
  return True


# Realistic 8K Image Generator
def generate_realistic_image(scene_prompt: str, index: int):
  # Strict Documentary Prompts (No Cartoon Guarantee)
  quality_boost = (
      ", 8k resolution, photorealistic, cinematic lighting, documentary"
      " scene, highly detailed, real life photography, shot on 35mm lens"
  )
  final_prompt = scene_prompt + quality_boost
  encoded_prompt = urllib.parse.quote(final_prompt)

  # Using Flux / Realistic Engine via Pollinations
  url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true"

  try:
    res = requests.get(url, timeout=30)
    if res.status_code == 200:
      img_path = f"scene_{index}.jpg"
      with open(img_path, "wb") as f:
        f.write(res.content)
      return img_path
  except Exception as e:
    return None


if st.button("Generate Documentary Assets"):
  if not text_input.strip():
    st.warning("Please enter your script first!")
  else:
    with st.spinner("Generating deep audio & 8K realistic scenes..."):
      # 1. Audio Generation
      audio_path = "output_voice.mp3"
      asyncio.run(generate_audio(text_input, audio_path, voice_code))
      st.success("✅ Deep Documentary Voice Generated!")
      st.audio(audio_path)

      # 2. Split Script into Scenes (Every Sentence = 1 Image)
      sentences = [
          s.strip() for s in re.split(r"[।!?,\n]+", text_input) if len(s.strip()) > 5
      ]

      st.subheader("🖼️ Realistic 8K Documentary Visuals Generated:")
      cols = st.columns(2)

      for i, sentence in enumerate(sentences):
        # Translate or pass prompt directly
        img_file = generate_realistic_image(sentence, i + 1)
        if img_file:
          with cols[i % 2]:
            st.image(
                img_file,
                caption=f"Scene {i+1} (4-5 sec): {sentence[:30]}...",
                use_container_width=True,
            )
