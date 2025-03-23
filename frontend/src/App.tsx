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
  delay: number;
  personalization_tips?: string;
}

interface SequenceMetadata {
  role: string;
  industry: string;
  seniority: string;
  company_type: string;
  generated_at: string;
}

interface Sequence {
  metadata: SequenceMetadata;
  steps: SequenceStep[];
}

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sequence, setSequence] = useState<Sequence | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [socketId, setSocketId] = useState<string | null>(null);

  useEffect(() => {
    const newSocket = io('http://localhost:5000');
    setSocket(newSocket);

    newSocket.on('connect', () => {
      setIsConnected(true);
    });

    newSocket.on('connection_response', (data) => {
      setSocketId(data.socket_id);
      newSocket.emit('get_chat_history');
    });

    newSocket.on('disconnect', () => {
      setIsConnected(false);
      setSocketId(null);
    });

    newSocket.on('chat_response', (data) => {
      try {
        // Parse the response JSON
        const responseData = JSON.parse(data.data);
        
        // Extract the readable message to display to the user
        let displayText = '';
        
        if (responseData.status === 'success') {
          // For successful responses, show only the tool_result (the actual message to the user)
          if (responseData.tool_result) {
            // Check if tool_result is a JSON string (like a sequence)
            try {
              const toolResult = JSON.parse(responseData.tool_result);
              if (toolResult.metadata && toolResult.steps) {
                setSequence(toolResult);
                displayText = "I've created a recruiting sequence based on your requirements.";
              } else {
                // Not a sequence, but still JSON - use it directly
                displayText = responseData.tool_result;
              }
            } catch (e) {
              // Not JSON, use the tool_result directly
              displayText = responseData.tool_result;
            }
          } else {
            displayText = "Request processed successfully.";
          }
        } else if (responseData.error) {
          // For error responses, show the error message
          displayText = `Error: ${responseData.error}`;
        } else {
          // Default case - use original text
          displayText = data.data;
        }
        
        // Add the message to chat
        const newMessage: Message = {
          id: Date.now().toString(),
          text: displayText,
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, newMessage]);
        
      } catch (e) {
        // If we can't parse the response, just show the raw text
        const newMessage: Message = {
          id: Date.now().toString(),
          text: data.data,
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, newMessage]);
      }
    });

    newSocket.on('chat_history', (data) => {
      const formattedMessages = data.data.map((msg: any) => ({
        id: Date.now().toString(),
        text: msg.text,
        sender: msg.sender,
        timestamp: new Date(msg.timestamp)
      }));
      setMessages(formattedMessages);
    });

    newSocket.on('sequence_updated', (data) => {
      if (data.data && sequence) {
        setSequence({
          ...sequence,
          steps: data.data
        });
      }
    });

    return () => {
      newSocket.close();
    };
  }, []);

  const handleSendMessage = (message: string) => {
    if (!socket || !isConnected) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, newMessage]);
    socket.emit('chat_message', { 
      message,
      current_sequence: sequence?.steps || []
    });
  };

  const handleSequenceUpdate = (updatedSteps: SequenceStep[]) => {
    if (!socket || !isConnected || !sequence) return;
    
    const updatedSequence = {
      ...sequence,
      steps: updatedSteps
    };
    setSequence(updatedSequence);
    socket.emit('sequence_update', { sequence: updatedSteps });
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