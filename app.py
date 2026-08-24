import asyncio
import os
import time
import edge_tts
from gtts import gTTS


# Robust Audio Generator with Edge-TTS Retries and gTTS Fallback
async def generate_audio(
    text: str, output_filename: str, preferred_voice: str = "en-US-ChristopherNeural"
):
  fallback_voices = [
      preferred_voice,
      "en-US-ChristopherNeural",
      "en-US-JennyNeural",
      "ur-PK-AsadNeural",
      "hi-IN-MadhurNeural",
  ]

  voices_to_try = list(dict.fromkeys(fallback_voices))

  # 1. Try Microsoft Edge TTS with Auto-Retry
  for voice in voices_to_try:
    for attempt in range(2):
      try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_filename)

        if (
            os.path.exists(output_filename)
            and os.path.getsize(output_filename) > 0
        ):
          print(f"Edge-TTS success with voice: {voice}")
          return True
      except Exception as e:
        print(f"Edge-TTS failed for {voice}. Retrying... Error: {e}")
        await asyncio.sleep(2)

  # 2. Hard Fallback to gTTS if all Edge-TTS attempts fail
  try:
    print("Edge-TTS failed completely. Falling back to Google TTS...")
    tts = gTTS(text=text, lang="en")
    tts.save(output_filename)
    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
      return True
  except Exception as e:
    print(f"gTTS also failed: {e}")

  raise Exception(
      "Audio generation failed completely. Please try again in a moment."
  )
