import os
import sys
import time
import threading
import io
import pystray
from PIL import Image, ImageDraw
import pyaudio
import numpy as np
import speech_recognition as sr
import openwakeword
from openwakeword.model import Model
import sounddevice as sd
from dotenv import load_dotenv

import openai
from google import genai
from google.genai import types

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# LOCAL TOOLS (Copied from F.R.I.D.A.Y)
# ==========================================
def open_world_monitor() -> str:
    """
    Opens the World Monitor dashboard (worldmonitor.app) in the system's web browser.
    Use this when the user wants a visual overview of global events or a real-time map.
    """
    import webbrowser
    webbrowser.open("https://worldmonitor.app/")
    return "Displaying the World Monitor on your primary screen now, sir."

def get_current_time() -> str:
    """Returns the current local time."""
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%I:%M %p')}."

# ==========================================
# AI PIPELINE
# ==========================================
SYSTEM_PROMPT = """
You are F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You — Tony Stark's AI.
You are calm, composed, and always informed. You speak like a trusted aide.
Keep all responses extremely short, 1-3 sentences max. You are a voice. Speak naturally. 
Do not use markdown, asterisks, or bullet points.
If you use the world monitor tool, just say "Let me pull that up for you." and call it silently.
"""

chat = gemini_client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[open_world_monitor, get_current_time],
        temperature=0.7,
    )
)

def play_audio(text):
    """Generate TTS and play it via sounddevice"""
    try:
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
            response_format="pcm"
        )
        audio_np = np.frombuffer(response.content, dtype=np.int16)
        sd.play(audio_np, samplerate=24000)
        sd.wait()
    except Exception as e:
        print("TTS Error:", e)

def listen_and_transcribe():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for command...")
        # Beep to indicate ready
        sd.play(np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, int(24000 * 0.1))) * 0.5, samplerate=24000)
        sd.wait()
        
        # Listen until silence
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            return None
            
    try:
        wav_data = io.BytesIO(audio.get_wav_data())
        wav_data.name = "audio.wav"
        
        print("Transcribing...")
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1", 
            file=wav_data
        )
        return transcript.text
    except Exception as e:
        print("Transcription error:", e)
        return None

def process_command(command):
    print("User:", command)
    try:
        response = chat.send_message(command)
        
        if response.function_calls:
            for fc in response.function_calls:
                if fc.name == "open_world_monitor":
                    res = open_world_monitor()
                    response = chat.send_message(res)
                elif fc.name == "get_current_time":
                    res = get_current_time()
                    response = chat.send_message(res)
                    
        if response.text:
            print("FRIDAY:", response.text)
            play_audio(response.text)
            
    except Exception as e:
        print("LLM Error:", e)

# ==========================================
# WAKE WORD ENGINE
# ==========================================
def wake_word_loop():
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280

    audio = pyaudio.PyAudio()
    mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    # Load hey_jarvis model
    owwModel = Model(wakeword_models=["hey_jarvis"], inference_framework="tflite")
    
    print("JARVIS Native Service Started. Listening for 'Hey Jarvis'...")
    
    while True:
        try:
            audio_data = np.frombuffer(mic_stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            prediction = owwModel.predict(audio_data)
            
            # Check models
            for mdl in prediction:
                if prediction[mdl] > 0.5:
                    print("\nWake word detected!")
                    mic_stream.stop_stream()
                    
                    command = listen_and_transcribe()
                    if command and len(command.strip()) > 2:
                        process_command(command)
                    
                    print("\nResuming wake word detection...")
                    # Clear buffer
                    owwModel.reset()
                    mic_stream.start_stream()
        except Exception as e:
            print("Audio stream error:", e)
            time.sleep(1)

# ==========================================
# SYSTEM TRAY
# ==========================================
def create_tray_icon():
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color=(20, 20, 20))
    dc = ImageDraw.Draw(image)
    dc.ellipse((10, 10, 54, 54), fill=(0, 255, 255))
    
    def quit_action(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(pystray.MenuItem('Quit JARVIS', quit_action))
    icon = pystray.Icon("JARVIS", image, "JARVIS Native", menu)
    return icon

if __name__ == "__main__":
    # Start wake word in background thread
    threading.Thread(target=wake_word_loop, daemon=True).start()
    
    # Run system tray (must be main thread)
    icon = create_tray_icon()
    icon.run()
