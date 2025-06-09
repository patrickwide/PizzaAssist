import asyncio
import websockets

async def test_socket(url):
    # Determine WebSocket protocol based on public_url scheme
    if url.startswith("https://"):
        websocket_url = url.replace("https://", "wss://")
    elif url.startswith("http://"):
        websocket_url = url.replace("http://", "ws://")
    else:
        raise ValueError(f"Unsupported URL scheme in {url}")

    # Append the WebSocket path
    websocket_url += "/ws/ai"
    print(f"Connecting to WebSocket at: {websocket_url}")

    async with websockets.connect(websocket_url) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_socket(url="http://127.0.0.1:8000"))
