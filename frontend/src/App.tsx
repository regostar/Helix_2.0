import React, { useState, useEffect } from 'react';
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import ChatBar from './components/ChatBar';
import Workspace from './components/Workspace';
import { useSocket } from './components/SocketContext';
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

// Get backend URL from environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sequence, setSequence] = useState<Sequence | null>(null);
  const [socketId, setSocketId] = useState<string | null>(null);

  useEffect(() => {
    // Create socket connection using environment variable
    const newSocket = io(BACKEND_URL);
    setSocket(newSocket);

    // Socket event handlers
    newSocket.on('connect', () => {
      setIsConnected(true);
      console.log('Connected to server');
    });

    // Connection events
    newSocket.on('connection_response', (data) => {
      setSocketId(data.socket_id);
      newSocket.emit('get_chat_history');
    });

    // Message response events
    newSocket.on('chat_response', (data) => {
      try {
        console.log('Received chat_response:', data);
        const responseData = JSON.parse(data.data);
        
        console.log('Parsed responseData:', responseData);
        console.log('Status:', responseData.status);
        console.log('LLM Response:', responseData.llm_response);
        console.log('Tool Result:', responseData.tool_result);
        
        if (responseData.status === 'success') {
          // Handle chat response if present
          if (responseData.chat_response) {
            const chatMessage: Message = {
              id: Date.now().toString(),
              text: responseData.chat_response,
              sender: 'ai',
              timestamp: new Date()
            };
            setMessages(prev => [...prev, chatMessage]);
          }

          // Handle sequence generation
          if (responseData.llm_response?.action === 'generate_sequence' && responseData.tool_result) {
            try {
              console.log('Parsing tool_result:', responseData.tool_result);
              const toolResult = JSON.parse(responseData.tool_result);
              console.log('Parsed sequence data:', toolResult);
              
              if (toolResult.metadata && toolResult.steps) {
                console.log('Setting sequence with valid data:', toolResult);
                setSequence(toolResult);
              } else {
                console.error('Invalid sequence data structure:', toolResult);
              }
            } catch (e) {
              console.error('Error parsing sequence data:', e);
            }
          }
          
          // Handle sequence modification
          else if (responseData.llm_response?.action === 'modify_sequence' && !responseData.chat_response) {
            const newMessage: Message = {
              id: Date.now().toString(),
              text: "I've refined the sequence step based on your feedback.",
              sender: 'ai',
              timestamp: new Date()
            };
            setMessages(prev => [...prev, newMessage]);
          }
          
          // Handle other tool results
          else if (responseData.tool_result && !responseData.chat_response) {
            const newMessage: Message = {
              id: Date.now().toString(),
              text: responseData.tool_result,
              sender: 'ai',
              timestamp: new Date()
            };
            setMessages(prev => [...prev, newMessage]);
          }
        } else if (responseData.error) {
          const errorMessage: Message = {
            id: Date.now().toString(),
            text: `Error: ${responseData.error}`,
            sender: 'ai',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } catch (e) {
        console.error('Error processing chat response:', e);
        const errorMessage: Message = {
          id: Date.now().toString(),
          text: "I apologize, but I encountered an error processing the response.",
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    });

    // Chat history events
    newSocket.on('chat_history', (data) => {
      const formattedMessages = data.data.map((msg: any) => ({
        id: Date.now().toString(),
        text: msg.text,
        sender: msg.sender,
        timestamp: new Date(msg.timestamp)
      }));
      setMessages(formattedMessages);
    });

    // Sequence update events
    newSocket.on('sequence_updated', (data) => {
      if (data.data && sequence) {
        setSequence({
          ...sequence,
          steps: data.data
        });
      }
    });

    // Step refinement events
    newSocket.on('step_refined', (data) => {
      if (data.step_id && data.refined_content && sequence) {
        const updatedSteps = sequence.steps.map(step => 
          step.id === data.step_id 
            ? { ...step, content: data.refined_content }
            : step
        );
        
        setSequence({
          ...sequence,
          steps: updatedSteps
        });
        
        const newMessage: Message = {
          id: Date.now().toString(),
          text: "I've refined the sequence step based on your feedback.",
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, newMessage]);
      }
    });

    return () => {
      newSocket.close();
    };
  }, []);

  const handleSendMessage = (message: string) => {
    if (!isConnected) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, newMessage]);
    
    // Type assertion for the emit function
    (socket as Socket).emit('chat_message', { 
      message,
      current_sequence: sequence?.steps || []
    });
  };

  const handleSequenceUpdate = (updatedSteps: SequenceStep[]) => {
    console.log("App - Handling sequence update:", updatedSteps);
    
    if (!isConnected) {
      console.warn("App - Cannot update sequence: socket not connected");
      return;
    }
    
    if (!sequence) {
      console.warn("App - Cannot update sequence: no sequence exists");
      return;
    }
    
    try {
      // Create an updated sequence with the new steps but keep the original metadata
      const updatedSequence = {
        ...sequence,
        steps: updatedSteps
      };
      
      console.log("App - Updating sequence state with:", updatedSequence);
      // Update local state
      setSequence(updatedSequence);
      
      // Send only the steps to the backend as that's what it expects
      console.log("App - Emitting sequence_update event");
      // Type assertion for the emit function
      (socket as Socket).emit('sequence_update', { sequence: updatedSteps });
    } catch (error) {
      console.error("App - Error updating sequence:", error);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden'
      }}>
        <Box sx={{ 
          display: 'flex', 
          flexGrow: 1,
          overflow: 'hidden'
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
      </Box>
    </ThemeProvider>
  );
}

export default App; 