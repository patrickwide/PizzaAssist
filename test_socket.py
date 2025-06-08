import asyncio
import websockets

async def test_socket():
    uri = "wss://9135-34-125-23-187.ngrok-free.app/ws/ai"
    async with websockets.connect(uri) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_socket())
