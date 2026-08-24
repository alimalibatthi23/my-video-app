import os
import subprocess
import requests
import streamlit as st
from gtts import gTTS

st.title("Purely Peak - Automated Documentary Generator")

# User Inputs
script_text = st.text_area("Enter your script here:", "The snow never stays silent — it only waits for time.")
pexels_api_key = st.text_input("Pexels API Key:", type="password")

if st.button("Generate Complete Video"):
    if not script_text.strip():
        st.warning("Please enter some script text first.")
    else:
        with st.spinner("Processing audio, videos, and effects. Please wait..."):
            
            # 1. Generate Audio via gTTS
            audio_path = "temp_voice.mp3"
            tts = gTTS(text=script_text, lang='en')
            tts.save(audio_path)
            
            # 2. Fetch Video Clip via Pexels API
            video_output = "final_output.mp4"
            temp_clip = "temp_pexels_clip.mp4"
            
            downloaded = False
            if pexels_api_key:
                headers = {"Authorization": pexels_api_key}
                search_query = script_text.split()[:2]
                query_str = " ".join(search_query) if search_query else "nature"
                
                api_url = f"https://api.pexels.com/videos/search?query={query_str}&per_page=1"
                try:
                    response = requests.get(api_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("videos"):
                            video_files = data["videos"][0]["video_files"]
                            best_file = max(video_files, key=lambda x: x.get("width", 0))
                            video_url = best_file["link"]
                            
                            v_data = requests.get(video_url)
                            with open(temp_clip, "wb") as f:
                                f.write(v_data.content)
                            downloaded = True
                except Exception as e:
                    pass
            
            # Fallback if Pexels download fails
            if not downloaded:
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1280x720:d=10', 
                    '-c:v', 'libx264', '-t', '10', temp_clip
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # 3. Main FFmpeg Command with Zoom and Text Overlays
            ffmpeg_command = [
                'ffmpeg', '-y',
                '-i', temp_clip,
                '-i', audio_path,
                '-filter_complex',
                # Applies scaling, zoompan effect, and text overlay
                "[0:v]scale=1280:720,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1280x720[vzoom];"
                "[vzoom]drawtext=text='Purely Peak':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=40[v]",
                '-map', '[v]',
                '-map', '1:a',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                video_output
            ]
            
            result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode == 0 and os.path.exists(video_output):
                st.success("Video generated successfully with zoom and text effects!")
                st.video(video_output)
            else:
                st.error(f"Error: {result.stderr.decode('utf-8')[-300:]}")
