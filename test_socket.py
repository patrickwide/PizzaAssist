import asyncio
import sys
import websockets
from urllib.parse import urlparse

async def test_socket(uri: str):
    parsed_uri = urlparse(uri)
    host = parsed_uri.netloc
    print(f"Connecting to WebSocket at host: {host}")
    print(f"Full WebSocket URI: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connection established.\nListening for messages...\n")
            try:
                while True:
                    message = await websocket.recv()
                    print(f"Message: {message}")
            except websockets.exceptions.ConnectionClosed as e:
                print(f"Connection closed: {e.code} - {e.reason}")
    except Exception as e:
        print(f"Failed to connect to WebSocket: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_socket.py <websocket_url>")
        sys.exit(1)

    ws_url = sys.argv[1]
    asyncio.run(test_socket(ws_url))
