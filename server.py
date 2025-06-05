from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# App modules
from core.agent import run_agent
from core.memory import AgentMemory
from core.constants import CONVERSATION_HISTORY_FILE_PATH, OLLAMA_MODEL

app = FastAPI()

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a shared memory instance for the conversation
memory = AgentMemory(max_history=15, history_file=CONVERSATION_HISTORY_FILE_PATH)

@app.websocket("/ws/ai")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_text("🤖 Connected to Pizza AI Assistant!")
        while True:
            data = await websocket.receive_text()

            if data.strip().lower() == "exit":
                await websocket.send_text("👋 Session ended. Bye!")
                break

            # Pass the user message to your AI agent
            try:
                response = await run_agent(OLLAMA_MODEL, data, memory)
                await websocket.send_text(response or "🤖 (No response from agent)")
            except Exception as e:
                await websocket.send_text(f"⚠️ Error: {e}")

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")

if __name__ == "__main__":
    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())
