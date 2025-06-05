import React, { useEffect, useState, useRef } from "react";
import MessageInput from "./components/MessageInput";
import ChatMessages from "./components/ChatMessages";
import Header from "./components/Header";

function App() {
  const [msg, setMsg] = useState("");
  const [log, setLog] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("connecting"); // connecting, connected, disconnected, error
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const wsRef = useRef(null);
  const hasConnected = useRef(false);
  const reconnectTimeoutRef = useRef(null);
  const RECONNECT_INTERVAL = 3000;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionStatus("connecting");
    const ws = new WebSocket("ws://localhost:8000/ws/ai");
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setConnectionStatus("connected");
      
      // Clear any reconnection timeout when successfully connected
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      // Don't send welcome message - let the server handle it
    };

    ws.onmessage = (event) => {
      setIsTyping(false);
      setLog((prev) => [...prev, { type: "ai", text: event.data }]);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setConnectionStatus("disconnected");
      
      // Only show reconnection attempt if we had a successful connection before
      if (hasConnected.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          setConnectionStatus("connecting");
          connectWebSocket();
        }, RECONNECT_INTERVAL);
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
      setConnectionStatus("error");
    };
  };

  useEffect(() => {
    // Prevent duplicate initial connections
    if (hasConnected.current) return;
    hasConnected.current = true;

    connectWebSocket();

    // Cleanup function
    return () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [log]);

  const sendMsg = () => {
    if (!msg.trim() || !isConnected || !wsRef.current) return;
    
    setLog((prev) => [...prev, { type: "user", text: msg }]);
    wsRef.current.send(msg);
    setMsg("");
    setIsTyping(true);
    inputRef.current?.focus();
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMsg();
    }
  };

  // Filter out system messages from the chat log for cleaner display
  const cleanedLog = log.filter(message => message.type !== "system");

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 overflow-hidden">
      <Header 
        isConnected={isConnected} 
        connectionStatus={connectionStatus}
      />

      <ChatMessages 
        log={cleanedLog}
        isTyping={isTyping}
        messagesEndRef={messagesEndRef}
        connectionStatus={connectionStatus}
      />

      <MessageInput 
        msg={msg}
        setMsg={setMsg}
        sendMsg={sendMsg}
        isConnected={isConnected}
        inputRef={inputRef}
        connectionStatus={connectionStatus}
      />
    </div>
  );
}

export default App;