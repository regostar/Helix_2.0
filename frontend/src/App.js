import React, { useState, useEffect } from 'react';
import { Box, ThemeProvider, createTheme } from '@mui/material';
import ChatBar from './components/ChatBar';
import Workspace from './components/Workspace';
import io from 'socket.io-client';

// Create theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

function App() {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sequence, setSequence] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Create socket connection
    const newSocket = io('http://localhost:5000', {
      transports: ['websocket'],
      cors: {
        origin: "http://localhost:3000",
        credentials: true
      },
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    // Socket event handlers
    newSocket.on('connect', () => {
      console.log('Connected to server');
      setIsConnected(true);
    });

    newSocket.on('connect_error', (error) => {
      console.log('Connection error:', error);
      setIsConnected(false);
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from server');
      setIsConnected(false);
    });

    newSocket.on('chat_response', (data) => {
      console.log('Received chat response:', data);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        text: data.data,
        sender: 'ai',
        timestamp: new Date()
      }]);
    });

    newSocket.on('sequence_updated', (data) => {
      console.log('Received sequence update:', data);
      setSequence(data.data);
    });

    setSocket(newSocket);

    // Cleanup on unmount
    return () => {
      if (newSocket) {
        newSocket.disconnect();
      }
    };
  }, []);

  const handleSendMessage = (message) => {
    if (!socket || !isConnected) {
      console.log('Socket not connected');
      return;
    }

    const newMessage = {
      id: Date.now().toString(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    };

    console.log('Sending message:', message);
    setMessages(prev => [...prev, newMessage]);
    
    socket.emit('chat_message', { 
      message,
      chat_history: messages,
      current_sequence: sequence
    });
  };

  const handleSequenceUpdate = (updatedSequence) => {
    if (!socket || !isConnected) {
      console.log('Socket not connected');
      return;
    }

    console.log('Updating sequence:', updatedSequence);
    setSequence(updatedSequence);
    socket.emit('sequence_update', { sequence: updatedSequence });
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ 
        display: 'flex', 
        height: '100vh',
        bgcolor: 'background.default',
        color: 'text.primary'
      }}>
        <ChatBar
          messages={messages}
          onSendMessage={handleSendMessage}
          isConnected={isConnected}
        />
        <Workspace
          sequence={sequence}
          onSequenceUpdate={handleSequenceUpdate}
        />
      </Box>
    </ThemeProvider>
  );
}

export default App; 