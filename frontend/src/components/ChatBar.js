import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Avatar,
  Divider,
  Tooltip,
  Fade,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import { styled } from '@mui/material/styles';

const ChatContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  width: '100%',
  backgroundColor: theme.palette.background.default,
}));

const MessagesContainer = styled(Box)(({ theme }) => ({
  flex: 1,
  overflow: 'auto',
  padding: theme.spacing(2),
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(2),
}));

const MessageBubble = styled(Paper)(({ theme, isUser }) => ({
  padding: theme.spacing(2),
  maxWidth: '80%',
  alignSelf: isUser ? 'flex-end' : 'flex-start',
  backgroundColor: isUser ? theme.palette.primary.main : theme.palette.grey[100],
  color: isUser ? theme.palette.primary.contrastText : theme.palette.text.primary,
  borderRadius: theme.spacing(2),
  position: 'relative',
  '&:before': {
    content: '""',
    position: 'absolute',
    top: '50%',
    [isUser ? 'right' : 'left']: -8,
    transform: 'translateY(-50%)',
    border: `8px solid transparent`,
    borderRightColor: isUser ? theme.palette.primary.main : theme.palette.grey[100],
    [isUser ? 'borderRightColor' : 'borderLeftColor']: isUser ? theme.palette.primary.main : theme.palette.grey[100],
  },
}));

const InputContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  borderTop: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.paper,
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
}));

const MessageHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  marginBottom: theme.spacing(1),
}));

const MessageTime = styled(Typography)(({ theme }) => ({
  fontSize: '0.75rem',
  color: theme.palette.text.secondary,
  marginTop: theme.spacing(0.5),
}));

const ChatBar = ({ messages, onSendMessage, isConnected }) => {
  const [message, setMessage] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && isConnected) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  return (
    <ChatContainer>
      <MessagesContainer>
        {messages.map((msg) => (
          <Fade in={true} key={msg.id}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <MessageHeader>
                <Avatar sx={{ width: 32, height: 32, bgcolor: msg.sender === 'user' ? 'primary.main' : 'secondary.main' }}>
                  {msg.sender === 'user' ? <PersonIcon /> : <SmartToyIcon />}
                </Avatar>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                  {msg.sender === 'user' ? 'You' : 'AI Assistant'}
                </Typography>
              </MessageHeader>
              <MessageBubble isUser={msg.sender === 'user'}>
                <Typography variant="body1">{msg.text}</Typography>
                <MessageTime>
                  {new Date(msg.timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </MessageTime>
              </MessageBubble>
            </Box>
          </Fade>
        ))}
        <div ref={messagesEndRef} />
      </MessagesContainer>
      <Divider />
      <form onSubmit={handleSubmit}>
        <InputContainer>
          <TextField
            fullWidth
            variant="outlined"
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!isConnected}
            size="small"
          />
          <Tooltip title={isConnected ? "Send message" : "Connecting..."}>
            <span>
              <IconButton 
                color="primary" 
                type="submit" 
                disabled={!message.trim() || !isConnected}
                sx={{ 
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                }}
              >
                <SendIcon />
              </IconButton>
            </span>
          </Tooltip>
        </InputContainer>
      </form>
    </ChatContainer>
  );
};

export default ChatBar; 