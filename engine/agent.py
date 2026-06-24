import os
import base64
import tempfile
import edge_tts
from openai import OpenAI

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

ws_callback = None

def send_state_update(state: str, text: str, subtitle: str = ""):
    if ws_callback:
        ws_callback({"type": "state_change", "state": state, "text": text, "subtitle": subtitle})

def send_audio_response(audio_b64: str, text: str):
    if ws_callback:
        ws_callback({"type": "play_audio", "audio_data": audio_b64, "text": text})

conversation_history = []

async def process_command(text: str, is_wake=False, is_standby=False, custom_reply=None):
    global conversation_history
    if is_wake:
        reply = "Yes Boss, how can I assist you?"
    elif is_standby:
        reply = "Going back to standby mode, Boss."
    elif custom_reply:
        reply = custom_reply
    else:
        # Get LLM response
        try:
            import datetime
            import platform
            import urllib.request
            
            weather_info = "Not requested"
            if "weather" in text.lower() or "temperature" in text.lower():
                try:
                    req = urllib.request.Request("https://wttr.in/?format=3", headers={'User-Agent': 'Mozilla/5.0'})
                    weather_info = urllib.request.urlopen(req, timeout=1.5).read().decode('utf-8').strip()
                except:
                    weather_info = "Unavailable"
                
            now = datetime.datetime.now()
            current_time = now.strftime("%I:%M %p")
            current_date = now.strftime("%A, %B %d, %Y")
            os_info = f"{platform.system()} {platform.release()}"
            
            memory_context = "No saved memories."
            if os.path.exists("memory.json"):
                try:
                    with open("memory.json", "r") as f:
                        memory_data = json.load(f)
                        if memory_data:
                            memory_context = "\n".join([f"- {m}" for m in memory_data])
                except: pass
            
            base_prompt = "You are JARVIS, an advanced AI assistant. Speak fluently, naturally, and with impeccable grammar. Be concise, highly intelligent, and always refer to the user as 'Boss'.\nCRITICAL DECISION MAKING LOGIC:\n1. If the user asks a general question, wants to know the time/date, tasks, system info, or wants an explanation: Provide a DIRECT text answer. Do NOT use any tools.\n2. You have a long-term memory system. Use the 'manage_memory' tool to add tasks, reminders, and user preferences when explicitly asked to remember something. Do NOT use manage_memory to read data, as it is already provided in your [USER MEMORY] context.\n3. ONLY launch/open applications or search the web if the user EXPLICITLY commands you to.\n4. Your default browser is Brave. If asked to open a browser or search the web, always assume Brave unless specified otherwise.\n5. Response Priority: Direct Answer > Local Knowledge > Tools. Always try to answer directly first.\n\nYou have access to system tools. Use them ONLY when explicitly instructed."
            
            dynamic_context = f"\n\n[REAL-TIME CONTEXT]\nCurrent Time: {current_time}\nCurrent Date: {current_date}\nCurrent Weather: {weather_info}\nSystem OS: {os_info}\n\n[USER MEMORY & TASKS]\n{memory_context}"
            
            from tools import get_system_tools, execute_tool
            messages = [
                {"role": "system", "content": base_prompt + dynamic_context}
            ]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": text})
            
            MODELS = [
                "meta-llama/llama-3.1-8b-instruct",
                "meta-llama/llama-3.3-70b-instruct",
                "google/gemma-2-9b-it",
                "qwen/qwen-2.5-7b-instruct"
            ]
            
            response_message = None
            last_error = None
            
            for model_id in MODELS:
                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=messages,
                        tools=get_system_tools(),
                        tool_choice="auto",
                        timeout=8.0
                    )
                    response_message = response.choices[0].message
                    break # Success!
                except Exception as e:
                    print(f"Model {model_id} failed: {e}")
                    last_error = e
                    continue
                    
            if not response_message:
                raise Exception(f"All models failed. Last error: {last_error}")
            
            if response_message.tool_calls:
                tool_names = [tc.function.name for tc in response_message.tool_calls]
                if "analyze_screen" in tool_names:
                    reply = "Analyzing your screen now, Boss."
                elif "search_web" in tool_names:
                    reply = "Searching the web, Boss."
                else:
                    reply = "Consider it done, Boss."
                
                import threading
                import asyncio
                current_loop = asyncio.get_running_loop()
                
                def run_tools():
                    for tool_call in response_message.tool_calls:
                        try:
                            res = execute_tool(tool_call)
                            if tool_call.function.name in ["analyze_screen", "search_web"]:
                                asyncio.run_coroutine_threadsafe(process_command("", custom_reply=str(res)), current_loop)
                        except Exception as e:
                            print(f"Tool error: {e}")
                
                t = threading.Thread(target=run_tools)
                t.start()
            else:
                reply = (response_message.content or "").strip()
                if not reply:
                    reply = "I'm sorry Boss, I didn't quite catch that."
                
        except Exception as e:
            print(f"LLM Error: {e}")
            reply = "I'm sorry Boss, I encountered an error connecting to my core."

    print(f"JARVIS: {reply}")
    
    if text and not is_wake and not is_standby:
        conversation_history.append({"role": "user", "content": text})
        conversation_history.append({"role": "assistant", "content": reply})
        if len(conversation_history) > 10:
            conversation_history[:] = conversation_history[-10:]
    
    try:
        # Generate TTS
        voice = "en-US-AriaNeural"
        temp_dir = tempfile.gettempdir()
        
        if is_wake:
            audio_file = os.path.join(temp_dir, "jarvis_wake.mp3")
        elif is_standby:
            audio_file = os.path.join(temp_dir, "jarvis_standby.mp3")
        else:
            audio_file = os.path.join(temp_dir, "jarvis_response.mp3")
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
        if not os.path.exists(audio_file):
            communicate = edge_tts.Communicate(reply, voice)
            await communicate.save(audio_file)
        
        # Read to base64
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        
        # Send to UI
        send_audio_response(b64_audio, reply)
    except Exception as e:
        print(f"TTS/Audio Error: {e}")
        send_state_update("idle", "ERROR", "Failed to process audio")
