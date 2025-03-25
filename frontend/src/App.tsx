import React, { useState, useEffect } from 'react';
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import ChatBar from './components/ChatBar';
import Workspace from './components/Workspace';
import { useSocket } from './components/SocketContext';
import { Socket } from 'socket.io-client';

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
  const { socket, isConnected, emit } = useSocket();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sequence, setSequence] = useState<Sequence | null>(null);
  const [socketId, setSocketId] = useState<string | null>(null);

  useEffect(() => {
    if (!socket) return;

    const typedSocket = socket as Socket;

    // Connection events
    typedSocket.on('connection_response', (data) => {
      setSocketId(data.socket_id);
      typedSocket.emit('get_chat_history');
    });

    // Message response events
    typedSocket.on('chat_response', (data) => {
      try {
        const responseData = JSON.parse(data.data);
        
        if (responseData.status === 'success') {
          // Handle sequence updates separately from chat messages
          if (responseData.action === 'generate_sequence' && responseData.tool_result) {
            try {
              const toolResult = JSON.parse(responseData.tool_result);
              if (toolResult.metadata && toolResult.steps) {
                setSequence(toolResult);
                // Use chat_response if available, otherwise use default message
                const newMessage: Message = {
                  id: Date.now().toString(),
                  text: responseData.chat_response || `I've created a recruiting sequence for ${toolResult.metadata.role} position. You can view and edit it in the workspace.`,
                  sender: 'ai',
                  timestamp: new Date()
                };
                setMessages(prev => [...prev, newMessage]);
              }
            } catch (e) {
              console.error('Error parsing sequence:', e);
            }
          } 
          // Handle step refinement messages
          else if (responseData.action === 'modify_sequence') {
            const newMessage: Message = {
              id: Date.now().toString(),
              text: responseData.chat_response || "I've refined the sequence step based on your feedback.",
              sender: 'ai',
              timestamp: new Date()
            };
            setMessages(prev => [...prev, newMessage]);
          }
          // Handle other tool results
          else if (responseData.tool_result) {
            const newMessage: Message = {
              id: Date.now().toString(),
              text: responseData.chat_response || responseData.tool_result,
              sender: 'ai',
              timestamp: new Date()
            };
            setMessages(prev => [...prev, newMessage]);
          }
        } else if (responseData.error) {
          const newMessage: Message = {
            id: Date.now().toString(),
            text: responseData.chat_response || `Error: ${responseData.error}`,
            sender: 'ai',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, newMessage]);
        }
      } catch (e) {
        console.error('Error processing chat response:', e);
        const newMessage: Message = {
          id: Date.now().toString(),
          text: "I apologize, but I encountered an error processing the response.",
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, newMessage]);
      }
    });

    // Chat history events
    typedSocket.on('chat_history', (data) => {
      const formattedMessages = data.data.map((msg: any) => ({
        id: Date.now().toString(),
        text: msg.text,
        sender: msg.sender,
        timestamp: new Date(msg.timestamp)
      }));
      setMessages(formattedMessages);
    });

    // Sequence update events
    typedSocket.on('sequence_updated', (data) => {
      if (data.data && sequence) {
        setSequence({
          ...sequence,
          steps: data.data
        });
      }
    });

    // Step refinement events
    typedSocket.on('step_refined', (data) => {
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
      typedSocket.off('connection_response');
      typedSocket.off('chat_response');
      typedSocket.off('chat_history');
      typedSocket.off('sequence_updated');
      typedSocket.off('step_refined');
    };
  }, [socket, sequence]);

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
    (emit as (event: string, data: any) => boolean)('chat_message', { 
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
      const updatedSequence = {
        ...sequence,
        steps: updatedSteps
      };
      
      console.log("App - Updating sequence state");
      setSequence(updatedSequence);
      
      console.log("App - Emitting sequence_update event");
      // Type assertion for the emit function
      (emit as (event: string, data: any) => boolean)('sequence_update', { sequence: updatedSteps });
    } catch (error) {
      console.error("App - Error updating sequence:", error);
    }
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