from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# App modules
from core.agent import run_agent
from core.memory import AgentMemory
from core.constants import CONVERSATION_HISTORY_FILE_PATH, OLLAMA_MODEL

# Logging setup
from logging_config import setup_logger

# Ensure the logging configuration is set up
logger = setup_logger(__name__)

# Create FastAPI app instance
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
    logger.info("🔌 WebSocket connection established")
    try:
        await websocket.send_text("🤖 Connected to Pizza AI Assistant!")
        logger.info("🤖 Sent initial connection message")
        while True:
            logger.info("Waiting for user input...")
            data = await websocket.receive_text()

            if data.strip().lower() == "exit":
                await websocket.send_text("👋 Session ended. Bye!")
                logger.info("👋 User requested to exit the session")
                break

            # Pass the user message to your AI agent
            try:
                async for chunk in run_agent(OLLAMA_MODEL, data, memory):
                    logger.info(f"🤖 Agent chunk: {chunk}")
                    if isinstance(chunk, dict):
                        # For success messages, just send the content
                        if chunk.get("status") == "success" and "content" in chunk:
                            await websocket.send_text(chunk["content"])
                        # For error messages, format them appropriately
                        elif chunk.get("status") == "error":
                            error_msg = f"⚠️ Error: {chunk.get('error', 'Unknown error')}"
                            await websocket.send_text(error_msg)
                    else:
                        await websocket.send_text(str(chunk) or "🤖 (No chunk from agent)")
            except Exception as e:
                logger.error(f"⚠️ Error processing message: {e}")
                await websocket.send_text(f"⚠️ Error: {e}")

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"⚠️ Unexpected error: {e}")
        await websocket.send_text(f"⚠️ Unexpected error: {e}")

if __name__ == "__main__":
    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())

