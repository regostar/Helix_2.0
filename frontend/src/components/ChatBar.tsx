import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Avatar,
  Divider,
  Tooltip,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

interface ChatBarProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isConnected: boolean;
}

// Function to determine if a string is JSON and simplify it for display
const formatMessage = (text: string): string => {
  try {
    // Try to parse as JSON
    const parsed = JSON.parse(text);
    console.log("parsed = ", parsed);
    
    // If it's a success response with tool_result, show only the tool_result
    if (parsed.status === 'success' && parsed.tool_result) {
      return parsed.tool_result;
    }
    
    // If it contains an error, display that
    if (parsed.error) {
      return `Error: ${parsed.error}`;
    }
    
    // Default to original message
    return text;
  } catch (e) {
    // Not JSON, return original
    return text;
  }
};

const ChatBar: React.FC<ChatBarProps> = ({ messages, onSendMessage, isConnected }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && isConnected) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <Paper
      sx={{
        width: '400px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid',
        borderColor: 'divider',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Helix Recruiter
        </Typography>
        <Tooltip title={isConnected ? 'Connected' : 'Disconnected'}>
          {isConnected ? <WifiIcon color="success" /> : <WifiOffIcon color="error" />}
        </Tooltip>
      </Box>
      <Divider />

      {/* Messages */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {messages.map((message) => (
          <Box
            key={message.id}
            sx={{
              display: 'flex',
              gap: 1,
              alignItems: 'flex-start',
              flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <Avatar
              sx={{
                bgcolor: message.sender === 'user' ? 'primary.main' : 'secondary.main',
              }}
            >
              {message.sender === 'user' ? 'U' : 'H'}
            </Avatar>
            <Paper
              sx={{
                p: 1.5,
                maxWidth: '70%',
                bgcolor: message.sender === 'user' ? 'primary.light' : 'grey.100',
                color: message.sender === 'user' ? 'primary.contrastText' : 'text.primary',
              }}
            >
              <Typography variant="body1">
                {message.sender === 'ai' ? formatMessage(message.text) : message.text}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                {message.timestamp.toLocaleTimeString()}
              </Typography>
            </Paper>
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>
      <Divider />

      {/* Input */}
      <Box component="form" onSubmit={handleSubmit} sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!isConnected}
          />
          <IconButton
            type="submit"
            color="primary"
            disabled={!input.trim() || !isConnected}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
};

export default ChatBar; 