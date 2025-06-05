import React from "react";

const Header = ({ isConnected, connectionStatus }) => {
  const getStatusIndicator = () => {
    switch (connectionStatus) {
      case "connected":
        return (
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-green-400 text-sm font-medium">
              Connected
            </span>
          </div>
        );
      case "connecting":
        return (
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
            <span className="text-yellow-400 text-sm font-medium">
              Connecting...
            </span>
          </div>
        );
      case "disconnected":
        return (
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-orange-400 rounded-full"></div>
            <span className="text-orange-400 text-sm font-medium">
              Reconnecting...
            </span>
          </div>
        );
      case "error":
        return (
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-red-400 rounded-full"></div>
            <span className="text-red-400 text-sm font-medium">
              Connection Error
            </span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700/50 p-4">
      <div className="flex items-center justify-between">
        {/* Left Section: Logo + Title */}
        <div className="flex items-center gap-3">
          {/* Logo/Icon */}
          <div aria-hidden="true" className="text-2xl text-white">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-6 h-6"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
              />
            </svg>
          </div>

          {/* Title and Subtitle */}
          <div>
            <h1 className="text-xl font-semibold text-white leading-tight">
              AI Agent
            </h1>
            <p className="text-sm text-gray-400 leading-none">
              Your friendly assistant
            </p>
          </div>
        </div>

        {/* Right Section: Status Indicator */}
        <div className="flex items-center">{getStatusIndicator()}</div>
      </div>
    </header>
  );
};

export default Header;
