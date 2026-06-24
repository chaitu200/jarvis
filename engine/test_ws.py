import asyncio
import websockets
import json

async def main():
    async with websockets.connect('ws://127.0.0.1:8000/ws') as ws:
        await ws.send(json.dumps({'action': 'ui_ready'}))
        print("Received:", await ws.recv())
        await ws.send(json.dumps({'action': 'wake_word'}))
        print("Received:", await ws.recv())

asyncio.run(main())
