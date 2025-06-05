import React, { useEffect, useState } from "react";

const ws = new WebSocket("ws://localhost:8000/ws/ai");

function App() {
  const [msg, setMsg] = useState("");
  const [log, setLog] = useState([]);

  useEffect(() => {
    ws.onmessage = (event) => {
      setLog((prev) => [...prev, "AI: " + event.data]);
    };
  }, []);

  const sendMsg = () => {
    setLog((prev) => [...prev, "You: " + msg]);
    ws.send(msg);
    setMsg("");
  };

  return (
    <div>
      <h1>Pizza AI Chat</h1>
      <textarea rows="10" value={log.join("\n")} readOnly />
      <input value={msg} onChange={(e) => setMsg(e.target.value)} />
      <button onClick={sendMsg}>Send</button>
    </div>
  );
}

export default App;
