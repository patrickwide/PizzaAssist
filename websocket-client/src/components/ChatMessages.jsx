import React from "react";

const ChatMessages = ({ log, isTyping, messagesEndRef, connectionStatus }) => {
  const renderMessage = (message, index) => {
    const isUser = message.type === "user";
    const isAI = message.type === "ai";
  
    return (
      <div
        key={index}
        className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6 group`}
      >
        <div
          className={`relative min-w-[200px] max-w-sm lg:max-w-lg xl:max-w-xl px-5 py-3 rounded-2xl shadow-lg backdrop-blur-sm transition-all duration-200 hover:shadow-xl ${
            isUser
              ? "bg-gradient-to-br from-emerald-600 to-teal-700 text-white ml-12"
              : isAI
              ? "bg-gradient-to-br from-gray-800 to-gray-900 text-white mr-12 border border-gray-600/50"
              : "bg-gradient-to-br from-zinc-600/10 to-neutral-700/10 text-gray-300 text-sm mr-12 border border-zinc-500/20"
          }`}
        >
          {/* Message tail */}
          <div
            className={`absolute top-4 w-3 h-3 transform rotate-45 ${
              isUser
                ? "bg-gradient-to-br from-emerald-600 to-teal-700 -right-1"
                : isAI
                ? "bg-gradient-to-br from-gray-800 to-gray-900 -left-1 border-l border-t border-gray-600/50"
                : "bg-gradient-to-br from-zinc-600/10 to-neutral-700/10 -left-1 border-l border-t border-zinc-500/20"
            }`}
          />
  
          {isUser && (
            <div className="flex items-center mb-2 pb-2 border-b border-emerald-300/30">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center mr-3 shadow-lg">
                <div className="w-3 h-3 bg-white rounded-full"></div>
              </div>
              <span className="text-xs text-emerald-100 font-semibold tracking-wide">YOU</span>
              <div className="ml-auto">
                <div className="w-2 h-2 bg-emerald-300 rounded-full animate-pulse shadow-lg shadow-emerald-300/50"></div>
              </div>
            </div>
          )}
  
          {isAI && (
            <div className="flex items-center mb-2 pb-2 border-b border-gray-500/30">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center mr-3 shadow-lg">
                <div className="w-4 h-1 bg-white rounded-full"></div>
              </div>
              <span className="text-xs text-gray-200 font-semibold tracking-wide">AI AGENT</span>
              <div className="ml-auto">
                <div className="w-2 h-2 bg-amber-300 rounded-full animate-pulse shadow-lg shadow-amber-300/50"></div>
              </div>
            </div>
          )}
  
          <div className={`${isUser ? "font-medium" : ""} leading-relaxed`}>
            {message.text}
          </div>
  
          {/* Timestamp */}
          <div className={`text-xs mt-2 opacity-60 ${isUser ? "text-right" : "text-left"}`}>
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    );
  };
  
  

  const renderTypingIndicator = () => (
    <div className="flex justify-start mb-6 group">
      <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 text-white max-w-sm lg:max-w-lg xl:max-w-xl px-5 py-3 rounded-2xl mr-12 border border-gray-700/50 shadow-lg backdrop-blur-sm">
        {/* Message tail */}
        <div className="absolute top-4 w-3 h-3 transform rotate-45 bg-gradient-to-br from-gray-800 to-gray-900 -left-1 border-l border-t border-gray-700/50" />
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce shadow-lg shadow-blue-400/50"></div>
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce shadow-lg shadow-purple-400/50" style={{ animationDelay: "0.1s" }}></div>
            <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce shadow-lg shadow-pink-400/50" style={{ animationDelay: "0.2s" }}></div>
          </div>
          <span className="text-gray-300 text-sm font-medium">thinking...</span>
        </div>
      </div>
    </div>
  );

  const renderEmptyState = () => {
    if (connectionStatus === "connecting") {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-300 max-w-md mx-auto">
            <div className="relative mb-8">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center mr-3 shadow-lg">
                <div className="w-4 h-1 bg-white rounded-full"></div>
              </div>
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center animate-spin">
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full"></div>
              </div>
            </div>
            <div className="text-xl font-bold mb-3 bg-gradient-to-r from-orange-400 to-red-500 bg-clip-text text-transparent">
              Connecting to AI
            </div>
            <div className="text-sm text-gray-400 leading-relaxed">
              Establishing secure connection to your personal assistant
            </div>
            <div className="mt-6 flex justify-center space-x-1">
              <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
            </div>
          </div>
        </div>
      );
    }

    if (connectionStatus === "error" || connectionStatus === "disconnected") {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-300 max-w-md mx-auto">
            <div className="relative mb-8">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center mr-3 shadow-lg">
                <div className="w-4 h-1 bg-white rounded-full"></div>
              </div>
              <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-4 h-4 bg-red-500 rounded-full animate-ping"></div>
            </div>
            <div className="text-xl font-bold mb-3 bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">
              Connection Issue
            </div>
            <div className="text-sm text-gray-400 leading-relaxed">
              {connectionStatus === "error" 
                ? "Unable to reach  AI servers. Please check your internet connection and try again." 
                : "Connection lost. Attempting to reconnect automatically..."}
            </div>
            {connectionStatus === "disconnected" && (
              <div className="mt-6 flex justify-center space-x-1">
                <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-orange-400 rounded-full animate-pulse" style={{ animationDelay: "0.3s" }}></div>
                <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" style={{ animationDelay: "0.6s" }}></div>
              </div>
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-2 bg-gradient-to-b from-gray-900/50 to-gray-900/80">
      {log.length === 0 ? (
        renderEmptyState()
      ) : (
        <>
          {log.map((message, index) => renderMessage(message, index))}
          {isTyping && renderTypingIndicator()}
        </>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;