import asyncio
import websockets
import json
from datetime import datetime
import aioconsole  # for async input

def format_timestamp(timestamp_str):
    """Format timestamp string to a readable format"""
    if not timestamp_str:
        return "No previous messages"
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

async def test_socket():
    # The session ID from your file
    session_id = "66065756-8d2e-4a79-807d-8a662b5d9f6b"
    
    # Construct the WebSocket URL with the session ID as a query parameter
    websocket_url = f"ws://localhost:8000/ws/ai?session_id={session_id}"
    print(f"Connecting to WebSocket at: {websocket_url}")

    try:
        async with websockets.connect(websocket_url) as websocket:
            # Start a task to receive messages
            async def receive_messages():
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if data.get("type") == "welcome":
                            # Display session information
                            session_info = data.get("session_info", {})
                            print("\n=== Session Information ===")
                            print(f"Total Messages: {session_info.get('total_messages', 0)}")
                            print(f"User Messages: {session_info.get('user_messages', 0)}")
                            print(f"Assistant Messages: {session_info.get('assistant_messages', 0)}")
                            print(f"Approximate Tokens: {session_info.get('approx_tokens', 0)}")
                            print(f"Last Message: {format_timestamp(session_info.get('last_message_time'))}")
                            print("========================\n")
                        
                        # Print the actual message content
                        if "message" in data:
                            if isinstance(data["message"], str):
                                print(f"\nAssistant: {data['message']}")
                            else:
                                print(f"\nAssistant: {json.dumps(data['message'], indent=2)}")
                        elif "content" in data:
                            print(f"\nAssistant: {data['content']}")
                        
                        # Print any errors
                        if data.get("status") == "error":
                            print(f"\nError: {data.get('error', 'Unknown error')}")
                    except websockets.exceptions.ConnectionClosed:
                        print("\nConnection closed")
                        break
                    except Exception as e:
                        print(f"\nError receiving message: {e}")

            # Start the receive task
            receive_task = asyncio.create_task(receive_messages())

            # Main loop for sending messages
            print("\nType your messages (press Ctrl+C to exit):")
            while True:
                try:
                    message = await aioconsole.ainput("\nYou: ")
                    if message.lower() in ['exit', 'quit']:
                        break
                    await websocket.send(message)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error sending message: {e}")
                    break

            # Clean up
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")
    except Exception as e:
        print(f"Error: {e}")

# Run the async function
if __name__ == "__main__":
    try:
        asyncio.run(test_socket())
    except KeyboardInterrupt:
        print("\nGoodbye!") 