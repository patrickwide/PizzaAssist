from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Dict, Any
import asyncio, json

MYSECRET = "MYSECRET"

app = FastAPI(
    title="Agentic Framework",
    description="""
    An API framework for managing AI agents and tools.
    
    ## Features
    * Register and manage tools
    * Create and configure agents  
    * Chat with agents using tools
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    }
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tools = {}
agents = {}
tool_lock = asyncio.Lock()
agent_lock = asyncio.Lock()

# Auth
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="API key for authentication")

async def get_api_key(x_api_key: str = Depends(api_key_header)):
    """Validate the API key provided in X-API-Key header."""
    if x_api_key != MYSECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key provided",
            headers={"WWW-Authenticate": "APIKey"}
        )
    return x_api_key

# Tool registration
@app.post(
    "/tools/register", 
    dependencies=[Depends(get_api_key)],
    summary="Register a new tool",
    description="Register a new tool by providing its implementation code and metadata",
    response_description="Status of tool registration"
)
async def register_tool(
    name: str = Form(..., description="Unique name for the tool"),
    description: str = Form(..., description="Description of what the tool does"),
    parameters: str = Form(..., description="JSON schema of tool parameters"), 
    code: UploadFile = File(..., description="Python file containing tool implementation")
):
    """
    Register a new tool that can be used by agents.
    
    - Tool names must be unique
    - Code must contain a function matching the tool name
    - Parameters must be valid JSON schema
    """
    async with tool_lock:
        if name in tools:
            raise HTTPException(400, "Tool already exists")

        content = await code.read()
        namespace = {}
        try:
            exec(content, namespace)
        except Exception as e:
            raise HTTPException(400, f"Error in tool code: {e}")
        if name not in namespace or not callable(namespace[name]):
            raise HTTPException(400, "Function name not found in code")
        func = namespace[name]

        try:
            params = json.loads(parameters)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON for parameters")

        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": list(params.keys())
                }
            }
        }
        tools[name] = {"func": func, "schema": schema, "description": description}
    return {"status": "tool registered", "tool": name}

@app.get("/tools", 
    summary="List all tools",
    description="Get a list of all registered tools with their descriptions and parameters",
    response_description="Dictionary of tools with their metadata"
)
async def list_tools():
    """
    List all registered tools and their metadata.
    Returns a dictionary with tool names as keys and their descriptions/parameters as values.
    """
    return {
        name: {
            "description": info["description"],
            "parameters": info["schema"]["function"]["parameters"]
        } for name, info in tools.items()
    }

class AgentCreate(BaseModel):
    """
    Parameters for creating a new agent
    """
    name: str = Field(..., description="Unique identifier for the agent")
    tool_names: list[str] = Field(default=[], description="List of tool names that this agent can use")
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="System prompt that defines the agent's behavior"
    )

@app.post("/agents", 
    dependencies=[Depends(get_api_key)],
    summary="Create a new agent",
    description="Create a new agent with specified tools and system prompt",
    response_description="Status of agent creation"
)
async def create_agent(info: AgentCreate):
    """
    Create a new agent with the specified configuration.
    
    - Agent names must be unique
    - All specified tools must be registered
    - System prompt defines the agent's behavior
    """
    async with agent_lock:
        if info.name in agents:
            raise HTTPException(400, "Agent already exists")
        for t in info.tool_names:
            if t not in tools:
                raise HTTPException(400, f"Tool '{t}' not registered")
        agents[info.name] = {
            "tools": info.tool_names,
            "system_prompt": info.system_prompt,
            "history": []
        }
    return {"status": "agent created", "agent_id": info.name}

@app.get("/agents",
    summary="List all agents",
    description="Get a list of all registered agents",
    response_description="List of agent names"
)
async def list_agents():
    """List all registered agents."""
    return {"agents": list(agents.keys())}

@app.get("/agents/{agent_id}/tools",
    summary="List agent's tools",
    description="Get information about the tools available to a specific agent",
    response_description="Dictionary of tools with their configurations"
)
async def agent_tools(agent_id: str):
    """
    Get details about the tools available to a specific agent.
    Raises 404 if agent is not found.
    """
    if agent_id not in agents:
        raise HTTPException(404, "Agent not found")
    return {
        "tools": {
            name: tools[name]["schema"]["function"]
            for name in agents[agent_id]["tools"]
        }
    }

class ChatInput(BaseModel):
    """
    Parameters for agent chat interaction
    """
    message: str = Field(..., description="Message to send to the agent")
    tool_call: str = Field(None, description="Optional name of tool to call")
    tool_params: Dict[str, Any] = Field(None, description="Parameters for tool call if tool_call is specified")

@app.post("/agents/{agent_id}/chat",
    summary="Chat with an agent",
    description="Send a message to an agent and optionally trigger a tool call",
    response_description="Agent's response and chat history"
)
async def chat_with_agent(agent_id: str, input: ChatInput):
    """
    Chat with a specific agent and optionally trigger tool usage.
    
    - Agent must exist
    - If tool_call is specified, it must be available to the agent
    - Tool parameters must match the tool's schema
    """
    if agent_id not in agents:
        raise HTTPException(404, "Agent not found")
    agent = agents[agent_id]

    # Log message
    agent["history"].append({"role": "user", "content": input.message})

    response = f"Echo: {input.message}"

    if input.tool_call:
        if input.tool_call not in agent["tools"]:
            raise HTTPException(400, f"Tool '{input.tool_call}' not available to agent")
        tool = tools[input.tool_call]
        try:
            result = tool["func"](**input.tool_params)
            response += f"\nTool `{input.tool_call}` result: {result}"
        except Exception as e:
            response += f"\nTool call failed: {str(e)}"

    agent["history"].append({"role": "assistant", "content": response})
    return {"response": response, "history": agent["history"]}
