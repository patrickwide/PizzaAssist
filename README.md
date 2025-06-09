# 🍕 Pizza Restaurant AI Assistant

This is an AI-powered assistant for a pizza restaurant that supports:
- Conversational interaction via the command line
- A web server with a FastAPI backend
- Tool usage like placing pizza orders and querying documents

## 🚀 Features

- 🔧 Tool-based interactions with LLM agents
- 🍕 Place pizza orders by providing pizza type, size, quantity, and delivery address
- 📄 Query indexed documents (e.g., reviews, orders) using semantic search
- 🧠 Persistent conversation history
- 💾 Vector store support with ChromaDB and Ollama embeddings
- 🌐 REST API and WebSocket support via FastAPI

---

## ⚙️ Installation

1. **Install and Setup Ollama**

   First, install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

   Start the Ollama server in the background:
   ```bash
   nohup ollama serve &
   ```

   Download the required models:
   ```bash
   ollama pull llama3.2
   ollama pull mxbai-embed-large
   ollama pull llama3.2-vision
   ```

   > **Note**: The Ollama server must be running for the assistant to function properly.

2. **Clone the repo**
   ```bash
   git clone https://github.com/patrickwide/PizzaAssist.git
   cd PizzaAssist
   ```

3. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # For Linux/macOS
   .\venv\Scripts\activate   # For Windows
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## 🎮 Test in Google Colab

You can easily test the Pizza Restaurant AI Assistant using Google Colab without any local setup:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/patrickwide/PizzaAssist/blob/main/main.ipynb)

The notebook provides an interactive environment to:
- Test the assistant's capabilities
- Place pizza orders
- Query documents
- Experiment with different prompts

Simply click the "Open in Colab" button above to get started!

---

## 🧠 Run in CLI Mode

This launches the assistant in the terminal with natural language support.

```bash
python cli.py
```

You'll see:

```
Welcome to the Pizza Restaurant Assistant!
Ask about reviews or place an order.
(e.g., 'How is the pepperoni pizza?', 'Tell me about the service',
       'I want to order 1 large veggie pizza to 456 Oak Avenue', 'exit' to quit)
```

---

## 🌐 Run as a Web Server

This launches the FastAPI backend on port `8000`.

```bash
python main.py
```

You'll see logs like:

```
🚀 Server starting on http://127.0.0.1:8000
🔌 WebSocket endpoint: ws://127.0.0.1:8000/ws/ai
❤️  Health check: http://127.0.0.1:8000/health
```

### API Endpoints

| Method | Endpoint  | Description           |
| ------ | --------- | --------------------- |
| GET    | `/health` | Health check          |
| WS     | `/ws/ai`  | WebSocket for AI chat |

---

## 📦 Run and Distribute as a Python Package

### How to Install and Run Locally as a Package

1. **Install the package in development mode**
   ```bash
   pip install -e .
   ```

2. **Run the web server**
   ```bash
   pizza-assist-server
   ```

### How to Build the Package

1. **Build the distribution packages**
   ```bash
   python -m build
   ```
   This will create both wheel (`.whl`) and source distribution (`.tar.gz`) files in the `dist/` directory.

### How to Distribute and Run in Production

1. **Install from a distribution file**
   ```bash
   pip install dist/pizza_assist-0.1.0-py3-none-any.whl
   ```

2. **Run in production**
   ```bash
   
   # Start the web server
   pizza-assist-server --host 0.0.0.0 --port 8000
   ```
---

## 🧪 Tooling

### Available Tools

* **`tool_place_order`**

  * Required: `pizza_type`, `size`, `quantity`, `delivery_address`
  * Description: Places a pizza order and saves it

* **`query_documents`**

  * Required: `query`
  * Description: Searches and retrieves content from indexed documents

---

## 📝 Logs

Logs are written to the `logs/` directory for debugging and tracing interactions.

---

## 🧠 Memory & Vector Store

* **Conversation History**: stored in `core/data/history/conversation_history.jsonl`
* **Vector Store**: ChromaDB-powered local vector DB with Ollama embeddings

---

## 📄 License

MIT License

---

## 👨‍💻 Author

Made by [patrickwide](https://github.com/patrickwide/)