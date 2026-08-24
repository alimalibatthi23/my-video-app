import asyncio
import os
import time
import edge_tts
from gtts import gTTS
import streamlit as st

# Streamlit UI Configuration
st.set_page_config(
    page_title="Text to Video & Audio Generator", layout="centered"
)
st.title("Text to Video & Audio Generator")

# Selection for Voice Languages
selected_voice = st.selectbox(
    "Select Voice/Language",
    options=[
        "en-US-ChristopherNeural (English Male)",
        "en-US-JennyNeural (English Female)",
        "ur-PK-AsadNeural (Urdu Male)",
        "ur-PK-UzmaNeural (Urdu Female)",
        "hi-IN-MadhurNeural (Hindi Male)",
        "hi-IN-SwaraNeural (Hindi Female)",
    ],
)

# Extract technical voice code
voice_code = selected_voice.split(" ")[0]

# User Text Input Box
text_input = st.text_area("Enter your script / text here:", height=150)


# Robust Audio Generator Function
async def generate_audio(text: str, output_filename: str, preferred_voice: str):
  fallback_voices = [
      preferred_voice,
      "en-US-ChristopherNeural",
      "en-US-JennyNeural",
      "ur-PK-AsadNeural",
      "hi-IN-MadhurNeural",
  ]

  voices_to_try = list(dict.fromkeys(fallback_voices))

  # 1. Edge-TTS Retries
  for voice in voices_to_try:
    for attempt in range(2):
      try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_filename)

        if (
            os.path.exists(output_filename)
            and os.path.getsize(output_filename) > 0
        ):
          return True
      except Exception:
        await asyncio.sleep(2)

  # 2. Google TTS Fallback
  try:
    tts = gTTS(text=text, lang="en")
    tts.save(output_filename)
    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
      return True
  except Exception:
    pass

  raise Exception("Audio generation failed. Please try again.")


# Action Button to Produce Audio
if st.button("Generate Audio"):
  if not text_input.strip():
    st.warning("Please write some text before generating!")
  else:
    with st.spinner("Generating high quality audio..."):
      output_file = "output.mp3"
      try:
        asyncio.run(generate_audio(text_input, output_file, voice_code))
        st.success("Audio generated successfully!")
        st.audio(output_file)
      except Exception as e:
        st.error(f"Error: {e}")
