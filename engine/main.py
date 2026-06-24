import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from agent import process_command, send_state_update

app = FastAPI()

clients = []
main_loop = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    from listener import start_listener
    start_listener(main_loop)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print("UI Connected to JARVIS Engine.")
    
    # Register the websocket for state updates
    def send_update_sync(payload):
        for client in clients:
            try:
                # Need to run async send in the running event loop
                asyncio.run_coroutine_threadsafe(client.send_json(payload), main_loop)
            except Exception as e:
                print(f"Error sending update: {e}")
                
    import agent
    agent.ws_callback = send_update_sync

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"Received from UI: {message}")
            await handle_ui_message(message, websocket)
    except WebSocketDisconnect:
        clients.remove(websocket)
        print("UI Disconnected.")

async def handle_ui_message(message: dict, websocket: WebSocket):
    action = message.get("action")
    
    if action == "ui_ready":
        await websocket.send_json({"type": "state_change", "state": "idle", "text": "ONLINE"})
        
    elif action == "wake_word":
        # Let JARVIS say yes boss
        asyncio.create_task(process_command("yes boss mode only", is_wake=True))
        
    elif action == "start_listening":
        import listener
        listener.set_listening(True)
        await websocket.send_json({"type": "state_change", "state": "listening", "text": "LISTENING..."})
        
    elif action == "standby":
        import listener
        listener.set_listening(False)
        asyncio.create_task(process_command("", is_standby=True))
        
    elif action == "command":
        text = message.get("text", "")
        # Process in background task
        asyncio.create_task(process_command(text))

def start_server():
    import socket
    import sys
    # Check if port 8000 is already bound
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8000))
    if result == 0:
        print("Another instance of JARVIS Engine is already running. Exiting.")
        sys.exit(0)
    sock.close()
    
    print("Starting JARVIS Engine on ws://localhost:8000/ws")
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    start_server()
