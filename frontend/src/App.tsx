import React, { useState, useEffect } from 'react';
import { Box, CssBaseline, ThemeProvider, createTheme, AppBar, Toolbar, Typography } from '@mui/material';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle
} from 'react-resizable-panels';
import ChatBar from './components/ChatBar';
import Workspace from './components/Workspace';
import { useSocket } from './components/SocketContext';

// Create theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563eb', // Modern blue
    },
    secondary: {
      main: '#10b981', // Modern teal
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h5: {
      fontWeight: 600,
      letterSpacing: '-0.02em',
    },
    subtitle1: {
      letterSpacing: '-0.01em',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          borderBottom: '1px solid #e2e8f0',
        },
      },
    },
  },
});

// Resize handle component
const ResizeHandle = () => {
  return (
    <PanelResizeHandle>
      <div 
        style={{
          width: '8px',
          height: '100%',
          cursor: 'col-resize',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: 'transparent'
        }}
      >
        <div 
          style={{
            width: '3px',
            height: '40px',
            backgroundColor: '#e2e8f0',
            borderRadius: '3px',
          }}
        />
      </div>
    </PanelResizeHandle>
  );
};

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

// Socket event response interfaces
interface ConnectionResponse {
  socket_id: string;
}

interface ChatHistoryResponse {
  data: Array<{
    text: string;
    sender: 'user' | 'ai';
    timestamp: string;
  }>;
}

interface ChatResponse {
  data: string;
}

interface SequenceUpdatedResponse {
  data: SequenceStep[];
}

interface StepRefinedResponse {
  step_id: string;
  refined_content: string;
}

function App() {
  const { socket, isConnected, emit } = useSocket();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sequence, setSequence] = useState<Sequence | null>(null);
  const [socketId, setSocketId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Add state for panel sizes
  const [panelSizes, setPanelSizes] = useState(() => {
    const savedSizes = localStorage.getItem('panelSizes');
    return savedSizes ? JSON.parse(savedSizes) : [30, 70]; // Default sizes: 30% chat, 70% sequence
  });

  useEffect(() => {
    if (!socket) return;

    // Socket event handlers
    const setupSocketListeners = () => {
      // Connection events
      socket.on('connection_response', (data: ConnectionResponse) => {
        setSocketId(data.socket_id);
        emit('get_chat_history');
      });

      // Message response events
      socket.on('chat_response', (data: ChatResponse) => {
        setIsLoading(false); // Stop loading when response received
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
      socket.on('chat_history', (data: ChatHistoryResponse) => {
        const formattedMessages = data.data.map((msg) => ({
          id: Date.now().toString(),
          text: msg.text,
          sender: msg.sender,
          timestamp: new Date(msg.timestamp)
        }));
        setMessages(formattedMessages);
      });

      // Sequence update events
      socket.on('sequence_updated', (data: SequenceUpdatedResponse) => {
        if (data.data && sequence) {
          setSequence({
            ...sequence,
            steps: data.data
          });
        }
      });

      // Step refinement events
      socket.on('step_refined', (data: StepRefinedResponse) => {
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
    };

    setupSocketListeners();

    // Cleanup function
    return () => {
      if (socket) {
        socket.off('connection_response');
        socket.off('chat_response');
        socket.off('chat_history');
        socket.off('sequence_updated');
        socket.off('step_refined');
      }
    };
  }, [socket, sequence, emit]);

  // Save panel sizes to localStorage when they change
  const handlePanelResize = (sizes: number[]) => {
    setPanelSizes(sizes);
    localStorage.setItem('panelSizes', JSON.stringify(sizes));
  };

  const handleSendMessage = (message: string) => {
    if (!isConnected) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, newMessage]);
    setIsLoading(true); // Start loading when message sent
    
    emit('chat_message', { 
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
      
      // Send only the steps to the backend using the emit function from context
      console.log("App - Emitting sequence_update event");
      emit('sequence_update', { sequence: updatedSteps });
    } catch (error) {
      console.error("App - Error updating sequence:", error);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
        <AppBar position="static" color="default" elevation={0}>
          <Toolbar sx={{ justifyContent: 'space-between' }}>
            <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
              Helix Recruiting
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isConnected ? 'Connected to server' : 'Disconnected'}
            </Typography>
          </Toolbar>
        </AppBar>
        
        <Box 
          sx={{ 
            flexGrow: 1,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <PanelGroup 
            direction="horizontal" 
            onLayout={handlePanelResize}
            style={{ height: '100%' }}
          >
            <Panel 
              defaultSize={panelSizes[0]} 
              minSize={20}
              style={{ overflow: 'hidden' }}
            >
              <ChatBar 
                messages={messages} 
                onSendMessage={handleSendMessage} 
                isConnected={isConnected}
                isLoading={isLoading}
              />
            </Panel>
            
            <ResizeHandle />
            
            <Panel 
              defaultSize={panelSizes[1]} 
              minSize={30}
              style={{ overflow: 'hidden' }}
            >
              <Workspace 
                sequence={sequence} 
                onSequenceUpdate={handleSequenceUpdate} 
              />
            </Panel>
          </PanelGroup>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App; 