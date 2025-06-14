# WebSocket Message Format Documentation

## Overview
This document outlines the message format used in the WebSocket communication between the server and client for the Pizza AI Assistant application. The system supports persistent sessions, message tracing, and tool execution monitoring.

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
    "response": string, // Optional: tool response content
    "arguments": object, // Optional: tool call arguments
    "execution_info": string, // Optional: tool execution details
    "execution_time_ms": number, // Optional: tool execution time in milliseconds
    
    // Correlation and Session Fields
    "message_id": string,      // Unique identifier for each message
    "parent_id": string,       // ID of the message this is responding to
    "conversation_id": string, // ID of the conversation thread
    "timestamp": string,       // ISO 8601 timestamp of message creation
    "sequence": number,        // Sequential number in conversation
    "user_input_id": string,   // ID of original user input that triggered this message
    "tool_call_id": string,   // ID of the tool call this message relates to (if applicable)
    "session_id": string      // ID of the client session
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

#### Tool Call
```json
{
    "status": "success",
    "stage": "tool_call",
    "tool": "tool_name",
    "arguments": {
        // Tool-specific arguments
    },
    "content": "Optional content accompanying the tool call"
}
```

#### Tool Result
```json
{
    "status": "success",
    "stage": "tool_result",
    "tool": "tool_name",
    "args": {
        // Arguments used in the tool call
    },
    "response": "tool execution result",
    "execution_info": "Detailed execution information",
    "execution_time_ms": 123.45
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

#### Tool-specific Errors
```json
{
    "status": "error",
    "stage": "tool_exec" | "tool_args" | "tool_missing" | "tool_call",
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
- `tool_call`: When AI decides to use a tool
- `tool_result`: Result from a tool execution
- `final_response`: Final response after tool usage
- `tool_exec`: During tool execution
- `tool_args`: During tool argument processing
- `tool_missing`: When requested tool is not available
- `initial_call`: During initial LLM call

## Implementation Notes
1. All messages are sent as JSON strings
2. The client should handle all possible message types and statuses
3. Error handling should be implemented for all error statuses
4. Messages may contain additional fields based on the specific context
5. The content field may contain markdown formatting for rich text display
6. Tool execution includes timing information for performance monitoring
7. Tool calls may include both arguments and optional content

## Message Tracing
Messages now support full traceability through the following mechanisms:

1. **Message Chain**
   - `message_id`: Unique identifier for each message
   - `parent_id`: References the message this is responding to
   - `conversation_id`: Groups messages in the same conversation thread

2. **Tool Execution Chain**

The system maintains a consistent tool execution chain through the following mechanisms:

1. **Tool Call Lifecycle**
   - A unique `tool_call_id` is generated when a tool call is initiated
   - This ID remains constant throughout the entire tool execution lifecycle
   - All related messages (results, errors) reference the same ID

2. **Chain Tracking**
   ```json
   {
       "stage": "tool_call",
       "tool_call_id": "uuid",
       "tool": "tool_name",
       // ...other fields...
   }
   ```
   ```json
   {
       "stage": "tool_result",
       "tool_call_id": "same-uuid-as-above",
       "tool": "tool_name",
       // ...other fields...
   }
   ```

3. **Error Handling in Chain**
   - Tool-related errors maintain the same `tool_call_id`
   - Enables tracing of failed tool executions
   - Supports debugging and monitoring

4. **Message Enrichment**
   - Each message is enriched with correlation IDs
   - Tool call chains are preserved in session history
   - Supports reconstruction of tool execution flow

3. **Temporal Tracking**
   - `timestamp`: Precise message creation time
   - `sequence`: Order in conversation flow

## Example Flow
1. Client connects → Receives welcome message
2. Client sends message → Receives initial response
3. If tools are used:
   - Receives tool call message with arguments
   - Receives tool result with execution details
4. Finally → Receives final response
5. On exit → Receives goodbye message

## Performance Monitoring
The system includes execution timing information for tool calls:
- `execution_time_ms`: Time taken to execute the tool in milliseconds
- `execution_info`: Detailed information about the tool execution

## Session Management
The system maintains persistent sessions with the following features:

1. **Session Identification**
   - Each client connection is assigned a unique `session_id`
   - Sessions persist across disconnections
   - Historical messages are preserved and retrievable

2. **Session Statistics**
   - Message counts (user and assistant)
   - Total message count
   - Approximate token usage
   - Last message timestamp

3. **Active Session Tracking**
   - Maintains active connections
   - Handles reconnections gracefully
   - Preserves conversation context

## Message Persistence
Messages are persisted with the following characteristics:

1. **Storage Format**
   - Messages stored as JSONL (one JSON object per line)
   - Each session has a dedicated history file
   - Messages include all correlation fields for tracing

2. **Message Types Stored**
   - User messages
   - AI responses
   - Tool calls and results
   - Error messages
   - (Welcome and session info messages are not persisted)

3. **History Management**
   - Messages are appended in real-time
   - Each message includes sequence number
   - Messages can be retrieved by session ID

## Security and Error Handling

1. **Connection Security**
   - Invalid session IDs are rejected
   - Connections are monitored for activity
   - Automatic cleanup of inactive sessions

2. **Error Recovery**
   - Graceful handling of disconnections
   - Message delivery confirmation
   - Automatic reconnection support

3. **Resource Management**
   - Session cleanup on disconnect
   - Memory efficient message storage
   - Concurrent session support

## Recent Improvements

1. **Tool Chain Consistency**
   - Consistent `tool_call_id` throughout tool execution lifecycle
   - Improved traceability of tool calls and their results
   - Enhanced debugging capabilities through reliable chaining

2. **Memory Optimization**
   - Efficient message storage with JSONL format
   - Selective persistence of important messages
   - Smart session cleanup and resource management

3. **Enhanced Error Handling**
   - Detailed error messages with proper correlation IDs
   - Error recovery with context preservation
   - Consistent error reporting across all stages

## Client Implementation Considerations

1. **Message Processing**
   - Handle all message types and stages
   - Maintain message chain for UI updates
   - Track tool execution progress

2. **State Management**
   - Store session ID for reconnection
   - Track conversation ID for message grouping
   - Maintain tool execution state

3. **UI/UX Guidelines**
   - Show progress during tool execution
   - Group related messages by conversation
   - Display errors with context
   - Support message threading

4. **Performance Considerations**
   - Handle message streaming efficiently
   - Implement reconnection logic
   - Cache relevant session data