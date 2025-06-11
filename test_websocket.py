import asyncio
import websockets

async def test_socket(url):
    # Accept ws://, wss://, http://, or https://
    if url.startswith("https://"):
        websocket_url = url.replace("https://", "wss://")
    elif url.startswith("http://"):
        websocket_url = url.replace("http://", "ws://")
    elif url.startswith("ws://") or url.startswith("wss://"):
        websocket_url = url  # Use as-is
    else:
        raise ValueError(f"Unsupported URL scheme in {url}")

    print(f"Connecting to WebSocket at: {websocket_url}")

    async with websockets.connect(websocket_url) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    session_id = None

    session_id = "66065756-8d2e-4a79-807d-8a662b5d9f6b"

    # === Option 1: Use a WebSocket URL directly (default) ===
    if session_id is None:
        websocket_url = "ws://localhost:8000/ws/ai"
    else:
        websocket_url = f"ws://localhost:8000/ws/ai?session_id={session_id}"

    # === Option 2: (Uncomment to use HTTP/HTTPS and auto-convert to WS/WSS) ===
    # base_http_url = "http://localhost:8000"  # or "https://yourdomain.com"
    # path = "/ws/ai"
    # if session_id:
    #     path += f"?session_id={session_id}"
    # websocket_url = base_http_url + path

    print(f"Connecting to WebSocket at: {websocket_url}")
    asyncio.run(test_socket(url=websocket_url))