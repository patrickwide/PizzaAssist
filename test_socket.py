import asyncio
import websockets

async def test_socket():
    uri = "ws://localhost:8000/ws/status"
    async with websockets.connect(uri) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_socket())

# https://c494-34-124-139-14.ngrok-free.app/