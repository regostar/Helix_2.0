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
import ChatOutlinedIcon from '@mui/icons-material/ChatOutlined';
import PersonOutlineOutlinedIcon from '@mui/icons-material/PersonOutlineOutlined';
import { styled } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';

const ChatContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  width: '400px',
  borderRight: `1px solid ${theme.palette.divider}`,
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

const MessageBubble = styled(Box)(({ theme, isUser }) => ({
  padding: theme.spacing(1.5, 2),
  maxWidth: '90%',
  width: 'fit-content',
  alignSelf: isUser ? 'flex-end' : 'flex-start',
  backgroundColor: isUser 
    ? alpha(theme.palette.primary.main, 0.1)
    : theme.palette.background.paper,
  color: isUser 
    ? theme.palette.primary.main
    : theme.palette.text.primary,
  borderRadius: theme.shape.borderRadius * 2,
  boxShadow: isUser 
    ? 'none'
    : '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  border: isUser 
    ? `1px solid ${alpha(theme.palette.primary.main, 0.2)}`
    : `1px solid ${theme.palette.divider}`,
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
  marginBottom: theme.spacing(0.5),
}));

const MessageTime = styled(Typography)(({ theme }) => ({
  fontSize: '0.75rem',
  color: theme.palette.text.secondary,
  marginTop: theme.spacing(0.5),
  textAlign: 'right',
}));

const MessageAvatar = styled(Avatar)(({ theme, isUser }) => ({
  width: 28,
  height: 28,
  backgroundColor: isUser 
    ? alpha(theme.palette.primary.main, 0.1)
    : alpha(theme.palette.secondary.main, 0.1),
  color: isUser 
    ? theme.palette.primary.main
    : theme.palette.secondary.main,
  fontSize: '0.875rem',
  fontWeight: 600,
}));

const ChatHeader = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  borderBottom: `1px solid ${theme.palette.divider}`,
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
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

  const formatMessageDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <ChatContainer>
      <ChatHeader>
        <ChatOutlinedIcon color="primary" />
        <Typography variant="subtitle1" fontWeight={600}>
          Chat with AI Assistant
        </Typography>
      </ChatHeader>
      <MessagesContainer>
        {messages.length === 0 && (
          <Box 
            sx={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              height: '100%',
              gap: 2,
              color: 'text.secondary',
              px: 4,
              textAlign: 'center'
            }}
          >
            <ChatOutlinedIcon sx={{ fontSize: 40, opacity: 0.5 }} />
            <Typography variant="h6">Start a conversation</Typography>
            <Typography variant="body2">
              Ask the AI to create a recruiting sequence for any role or position.
            </Typography>
          </Box>
        )}
        
        {messages.map((msg) => (
          <Fade in={true} key={msg.id} timeout={500}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
              <MessageHeader>
                <MessageAvatar isUser={msg.sender === 'user'}>
                  {msg.sender === 'user' ? <PersonOutlineOutlinedIcon fontSize="small" /> : <ChatOutlinedIcon fontSize="small" />}
                </MessageAvatar>
                <Typography variant="body2" color="text.secondary">
                  {msg.sender === 'user' ? 'You' : 'AI Assistant'}
                </Typography>
              </MessageHeader>
              <MessageBubble isUser={msg.sender === 'user'}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {msg.text}
                </Typography>
                <MessageTime>
                  {formatMessageDate(msg.timestamp)}
                </MessageTime>
              </MessageBubble>
            </Box>
          </Fade>
        ))}
        <div ref={messagesEndRef} />
      </MessagesContainer>
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
            sx={{ 
              '& .MuiOutlinedInput-root': {
                borderRadius: 1.5,
              }
            }}
          />
          <IconButton 
            color="primary" 
            type="submit" 
            disabled={!message.trim() || !isConnected}
            sx={{ 
              bgcolor: 'primary.main',
              color: 'white',
              '&:hover': {
                bgcolor: 'primary.dark',
              },
              '&.Mui-disabled': {
                bgcolor: 'action.disabledBackground',
                color: 'action.disabled',
              },
              borderRadius: 1.5,
              width: 40,
              height: 40
            }}
          >
            <SendIcon fontSize="small" />
          </IconButton>
        </InputContainer>
      </form>
    </ChatContainer>
  );
};

export default ChatBar; 