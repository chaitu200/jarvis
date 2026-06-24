import os
import sys
import json
import asyncio
import threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from agent import process_command, send_state_update
import speech_recognition as sr

is_listening_for_command = False
needs_reset = False
WAKE_WORDS = ["hey jarvis"]
grammar_str = json.dumps(WAKE_WORDS + ["[unk]"])

def set_listening(value: bool):
    global is_listening_for_command, needs_reset
    is_listening_for_command = value
    if value:
        needs_reset = True

def listen_loop(loop):
    global is_listening_for_command, needs_reset
    print("JARVIS Audio Listener Started (Vosk Wake Word + Google Commands).")
    
    model_path = "model"
    if not os.path.exists(model_path):
        print(f"Please download the model from https://alphacephei.com/vosk/models and unpack as {model_path} in the current folder.")
        sys.exit(1)

    model = Model(model_path)
    samplerate = 16000
    recognizer_wake = KaldiRecognizer(model, samplerate, grammar_str)
    
    while True:
        if not is_listening_for_command:
            print("Listening for wake word (Vosk)...")
            recognizer_wake.Reset()
            try:
                with sd.RawInputStream(samplerate=samplerate, blocksize=4000, device=None, dtype='int16',
                                       channels=1, callback=None) as stream:
                    while not is_listening_for_command:
                        data, overflowed = stream.read(2000)
                        if overflowed:
                            recognizer_wake.Reset()
                            continue
                            
                        if recognizer_wake.AcceptWaveform(bytes(data)):
                            result_dict = json.loads(recognizer_wake.Result())
                            text = result_dict.get("text", "")
                            if "hey jarvis" in text:
                                print("WAKE WORD DETECTED (Full)")
                                send_state_update("processing", "WAKING...", "")
                                asyncio.run_coroutine_threadsafe(process_command("", is_wake=True), loop)
                                break
                        else:
                            partial_dict = json.loads(recognizer_wake.PartialResult())
                            partial = partial_dict.get("partial", "").strip().lower()
                            if partial == "hey jarvis":
                                print("WAKE WORD DETECTED (Partial Exact)")
                                send_state_update("processing", "WAKING...", "")
                                asyncio.run_coroutine_threadsafe(process_command("", is_wake=True), loop)
                                break
            except Exception as e:
                print(f"Audio Stream Error: {e}")
                import time
                time.sleep(1)
        else:
            print("Switched to Command Listening Mode (Google).")
            with sr.Microphone(sample_rate=16000) as source:
                r = sr.Recognizer()
                r.pause_threshold = 2.0  # Wait a full 2 seconds of silence before cutting off
                r.energy_threshold = 400
                r.dynamic_energy_threshold = True
                
                # Adjust for ambient noise briefly
                r.adjust_for_ambient_noise(source, duration=0.5)
                
                while is_listening_for_command:
                    try:
                        audio_data = r.listen(source, timeout=1.0, phrase_time_limit=30)
                        
                        send_state_update("processing", "PROCESSING...", "Analyzing speech...")
                        try:
                            text = r.recognize_google(audio_data)
                            print(f"Command Captured (Google): {text}")
                            send_state_update("processing", "PROCESSING...", f"\"{text}\"")
                            asyncio.run_coroutine_threadsafe(process_command(text), loop)
                            
                            # Stop listening while processing and speaking
                            is_listening_for_command = False
                            break
                        except sr.UnknownValueError:
                            print("Google could not understand (noise/silence). Ignoring.")
                            send_state_update("listening", "LISTENING...", "")
                        except Exception as e:
                            print(f"Google error: {e}")
                            send_state_update("listening", "LISTENING...", "")
                            
                    except sr.WaitTimeoutError:
                        # Timeout every 1s, just continue to check if we should still be listening
                        continue

def start_listener(asyncio_loop):
    t = threading.Thread(target=listen_loop, args=(asyncio_loop,), daemon=True)
    t.start()
