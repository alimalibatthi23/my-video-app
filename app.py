import asyncio
import os
import time
import edge_tts
import streamlit as st


# Safe audio generator function supporting English, Urdu, and Hindi
async def generate_audio_safe(
    text: str, output_filename: str, preferred_voice: str = "en-US-ChristopherNeural"
):
  fallback_voices = [
      preferred_voice,
      # English Voices
      "en-US-ChristopherNeural",
      "en-US-JennyNeural",
      # Urdu Voices
      "ur-PK-AsadNeural",  # Urdu Male
      "ur-PK-UzmaNeural",  # Urdu Female
      # Hindi Voices
      "hi-IN-MadhurNeural",  # Hindi Male
      "hi-IN-SwaraNeural",  # Hindi Female
  ]

  voices_to_try = list(dict.fromkeys(fallback_voices))

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
        time.sleep(2)

  raise Exception("Audio generation failed. Please try again.")


# Execution block to trigger the audio generation
try:
  asyncio.run(generate_audio_safe(line, audio_file, selected_voice))
except Exception as e:
  st.error(f"Audio Error: {e}")
