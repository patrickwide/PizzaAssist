# WebSocket Message Format Documentation

## Overview
This document outlines the message format used in the WebSocket communication between the server and client for the Pizza AI Assistant application.

## Message Structure
All messages are sent as JSON objects with the following base structure:

```json
{
    "status": string,  // "success" | "error" | "warning"
    "type": string,    // Optional: message type identifier
    "stage": string,   // Optional: processing stage identifier
    "content": string, // Optional: main message content
    "error": string,   // Optional: error message if status is "error"
    "tool": string,    // Optional: tool name when using tools
    "response": string // Optional: tool response content
}
```

## Message Types

### 1. Welcome Message
Sent when a client first connects to establish the session.

```json
{
    "status": "success",
    "type": "welcome",
    "message": "Welcome message content"
}
```

### 2. AI Response Messages
Messages from the AI agent during conversation processing.

#### Initial Response
```json
{
    "status": "success",
    "stage": "initial_response",
    "content": "AI's response message"
}
```

#### Tool Result
```json
{
    "status": "success",
    "stage": "tool_result",
    "tool": "tool_name",
    "response": "tool execution result"
}
```

#### Final Response
```json
{
    "status": "success",
    "stage": "final_response",
    "content": "AI's final response after tool usage"
}
```

### 3. Error Messages
Various error conditions that may occur during processing.

#### General Error
```json
{
    "status": "error",
    "type": "exception",
    "message": "Error description"
}
```

#### Tool-specific Error
```json
{
    "status": "error",
    "stage": "tool_exec",
    "tool": "tool_name",
    "error": "Error description"
}
```

### 4. Goodbye Message
Sent when the session is ending.

```json
{
    "status": "success",
    "type": "goodbye",
    "message": "Farewell message"
}
```

## Status Codes
- `success`: Operation completed successfully
- `error`: An error occurred during processing
- `warning`: Operation completed with potential issues

## Stages
- `initial_response`: First response from the AI
- `tool_result`: Result from a tool execution
- `final_response`: Final response after tool usage
- `tool_exec`: During tool execution
- `tool_args`: During tool argument processing
- `tool_missing`: When requested tool is not available

## Implementation Notes
1. All messages are sent as JSON strings
2. The client should handle all possible message types and statuses
3. Error handling should be implemented for all error statuses
4. Messages may contain additional fields based on the specific context
5. The content field may contain markdown formatting for rich text display

## Example Flow
1. Client connects → Receives welcome message
2. Client sends message → Receives initial response
3. If tools are used → Receives tool results
4. Finally → Receives final response
5. On exit → Receives goodbye message 