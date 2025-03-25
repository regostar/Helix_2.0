import React, { createContext, useContext, useState, useEffect } from 'react';
import { io } from 'socket.io-client';

// Add socket to window object type for global access
// This is for backward compatibility with existing code
// that accesses window.socket directly
/* 
  This declaration ensures TypeScript code can access window.socket:
  declare global {
    interface Window {
      socket: any;
    }
  }
*/

// Create context with initial values
const SocketContext = createContext({
  socket: null,
  isConnected: false,
  emit: () => false
});

// Custom hook to use the socket context
export const useSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error("useSocket must be used within a SocketProvider");
  }
  return context;
};

// Socket provider component
export const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Initialize socket
    const newSocket = io('http://localhost:5000');
    
    // Save socket to state
    setSocket(newSocket);
    
    // Make socket available globally for backward compatibility
    window.socket = newSocket;
    console.log('Socket connection established and made available globally via window.socket');
    
    // Socket event listeners
    newSocket.on('connect', () => {
      console.log('Socket connected:', newSocket.id);
      setIsConnected(true);
    });
    
    newSocket.on('disconnect', () => {
      console.log('Socket disconnected');
      setIsConnected(false);
    });
    
    // Cleanup function
    return () => {
      console.log('Cleaning up socket connection');
      newSocket.disconnect();
      window.socket = null;
    };
  }, []);

  // Value to be provided
  const contextValue = {
    socket,
    isConnected,
    emit: (event, data) => {
      if (socket) {
        socket.emit(event, data);
        return true;
      }
      console.warn(`Failed to emit ${event} - socket not connected`);
      return false;
    }
  };

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  );
};

export default SocketContext; 