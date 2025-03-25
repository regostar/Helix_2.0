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

// Get backend URL from environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';
console.log('SocketContext - Using backend URL:', BACKEND_URL);

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
    console.error("useSocket called outside of SocketProvider");
    throw new Error("useSocket must be used within a SocketProvider");
  }
  return context;
};

// Socket provider component
export const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    console.log('SocketProvider - Initializing socket connection to', BACKEND_URL);
    
    // Initialize socket
    const newSocket = io(BACKEND_URL);
    
    // Save socket to state
    setSocket(newSocket);
    
    // Make socket available globally for backward compatibility
    window.socket = newSocket;
    console.log('Socket connection established and made available globally via window.socket');
    
    // Socket event listeners
    newSocket.on('connect', () => {
      console.log('Socket connected with ID:', newSocket.id);
      setIsConnected(true);
    });
    
    newSocket.on('disconnect', () => {
      console.log('Socket disconnected');
      setIsConnected(false);
    });
    
    newSocket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      setIsConnected(false);
    });
    
    // Log all incoming socket events (for debugging)
    const originalOnevent = newSocket.onevent;
    newSocket.onevent = function(packet) {
      const args = packet.data || [];
      console.log('Socket received event:', args[0], args.slice(1));
      originalOnevent.call(this, packet);
    };
    
    // Cleanup function
    return () => {
      console.log('Cleaning up socket connection');
      newSocket.disconnect();
      window.socket = null;
    };
  }, []);

  // Emit with better logging
  const emitEvent = (event, data) => {
    if (!socket) {
      console.error(`Cannot emit ${event} - socket is null`);
      return false;
    }
    
    if (!isConnected) {
      console.warn(`Emitting ${event} while socket is disconnected`);
    }
    
    try {
      console.log(`Emitting socket event: ${event}`, data);
      socket.emit(event, data);
      return true;
    } catch (error) {
      console.error(`Error emitting socket event ${event}:`, error);
      return false;
    }
  };

  // Value to be provided
  const contextValue = {
    socket,
    isConnected,
    emit: emitEvent
  };

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  );
};

export default SocketContext; 