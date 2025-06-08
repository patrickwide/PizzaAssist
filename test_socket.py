import asyncio
import websockets

async def test_socket():
    uri = "wss://d176-34-125-43-15.ngrok-free.app/ws/ai"
    async with websockets.connect(uri) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_socket())
