import React, { useState, useEffect } from 'react';
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import ChatBar from './components/ChatBar';
import Workspace from './components/Workspace';
import { io, Socket } from 'socket.io-client';

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

// Types
interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

interface SequenceStep {
  id: string;
  type: string;
  content: string;
  delay?: number;
}

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sequence, setSequence] = useState<SequenceStep[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const newSocket = io('http://localhost:5000');
    setSocket(newSocket);

    newSocket.on('connect', () => {
      setIsConnected(true);
    });

    newSocket.on('disconnect', () => {
      setIsConnected(false);
    });

    newSocket.on('chat_response', (data) => {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        text: data.data,
        sender: 'ai',
        timestamp: new Date()
      }]);
    });

    newSocket.on('sequence_updated', (data) => {
      setSequence(data.data);
    });

    return () => {
      newSocket.close();
    };
  }, []);

  const handleSendMessage = (message: string) => {
    if (!socket) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, newMessage]);
    socket.emit('chat_message', { message });
  };

  const handleSequenceUpdate = (updatedSequence: SequenceStep[]) => {
    if (!socket) return;
    setSequence(updatedSequence);
    socket.emit('sequence_update', { sequence: updatedSequence });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
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