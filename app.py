import asyncio
import os
import time
import edge_tts


# Safe audio generator replacing the old generate_audio function
async def generate_audio(
    text: str, output_filename: str, preferred_voice: str = "en-US-ChristopherNeural"
):
  fallback_voices = [
      preferred_voice,
      "en-US-ChristopherNeural",  # English Male
      "en-US-JennyNeural",  # English Female
      "ur-PK-AsadNeural",  # Urdu Male
      "ur-PK-UzmaNeural",  # Urdu Female
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

  raise Exception(
      "Audio generation failed after retries. Please try again."
  )
