import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Typography,
  Avatar,
  Tooltip,
  Fade,
  CircularProgress,
  Button,
  Chip,
  Paper,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ChatOutlinedIcon from '@mui/icons-material/ChatOutlined';
import PersonOutlineOutlinedIcon from '@mui/icons-material/PersonOutlineOutlined';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { styled, keyframes } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';

// Define types for the ChatBar props
interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

interface SuggestedPrompt {
  id: string;
  text: string;
  description: string;
}

interface ChatBarProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isConnected: boolean;
  isLoading: boolean;
  suggestedPrompts?: SuggestedPrompt[];
}

// Create keyframes for the typing animation
const typingAnimation = keyframes`
  0% {
    transform: translateY(0px);
  }
  28% {
    transform: translateY(-5px);
  }
  44% {
    transform: translateY(0px);
  }
`;

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

const MessageBubble = styled(Box)<{ isUser: boolean }>(({ theme, isUser }) => ({
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

const PromptSuggestionContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexWrap: 'wrap',
  gap: theme.spacing(1),
  marginBottom: theme.spacing(2),
  justifyContent: 'center',
}));

const PromptSuggestion = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius * 1.5,
  cursor: 'pointer',
  transition: 'all 0.2s ease-in-out',
  border: `1px solid ${theme.palette.divider}`,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'flex-start',
  width: 'calc(50% - 8px)',
  maxWidth: '350px',
  backgroundColor: theme.palette.background.paper,
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor: alpha(theme.palette.primary.main, 0.05),
    transform: 'translateY(-2px)',
  },
}));

const TypingDot = styled('span')<{ index: number }>(({ theme, index }) => ({
  display: 'inline-block',
  width: '6px',
  height: '6px',
  borderRadius: '50%',
  marginRight: '3px',
  backgroundColor: theme.palette.text.secondary,
  animation: `${typingAnimation} 1.5s infinite ease-in-out`,
  animationDelay: `${index * 0.2}s`,
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

const MessageAvatar = styled(Avatar)<{ isUser: boolean }>(({ theme, isUser }) => ({
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

const ChatBar: React.FC<ChatBarProps> = ({ 
  messages, 
  onSendMessage, 
  isConnected, 
  isLoading,
  suggestedPrompts = [] 
}) => {
  const [message, setMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && isConnected && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handlePromptClick = (promptText: string) => {
    if (isConnected && !isLoading) {
      onSendMessage(promptText);
    }
  };

  const formatMessageDate = (timestamp: Date) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // Typing indicator component
  const TypingIndicator = () => (
    <Fade in={true}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
        <MessageHeader>
          <MessageAvatar isUser={false}>
            <ChatOutlinedIcon fontSize="small" />
          </MessageAvatar>
          <Typography variant="body2" color="text.secondary">
            AI Assistant
          </Typography>
        </MessageHeader>
        <MessageBubble isUser={false} sx={{ px: 2, py: 1.5, minHeight: 24, display: 'flex', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TypingDot index={0} />
            <TypingDot index={1} />
            <TypingDot index={2} />
          </Box>
        </MessageBubble>
      </Box>
    </Fade>
  );

  return (
    <ChatContainer>
      <ChatHeader>
        <ChatOutlinedIcon color="primary" />
        <Typography variant="subtitle1" fontWeight={600}>
          Chat with AI Assistant
        </Typography>
        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', ml: 'auto' }}>
            <CircularProgress size={16} thickness={5} sx={{ mr: 1 }} />
            <Typography variant="caption" color="text.secondary">
              Processing...
            </Typography>
          </Box>
        )}
      </ChatHeader>
      <MessagesContainer>
        {messages.length === 0 && (
          <>
            <Box 
              sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                height: '50%',
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
            
            {suggestedPrompts.length > 0 && (
              <Box sx={{ mt: 'auto', mb: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, justifyContent: 'center' }}>
                  <AutoAwesomeIcon fontSize="small" sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="subtitle2" color="text.primary">
                    Try these suggestions
                  </Typography>
                </Box>
                <PromptSuggestionContainer>
                  {suggestedPrompts.map((prompt) => (
                    <PromptSuggestion 
                      key={prompt.id}
                      onClick={() => handlePromptClick(prompt.text)}
                      elevation={0}
                    >
                      <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                        {prompt.text}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {prompt.description}
                      </Typography>
                    </PromptSuggestion>
                  ))}
                </PromptSuggestionContainer>
              </Box>
            )}
          </>
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

        {/* Show the typing indicator when waiting for a response */}
        {isLoading && <TypingIndicator />}
        
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
            disabled={!isConnected || isLoading}
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
            disabled={!message.trim() || !isConnected || isLoading}
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
            {isLoading ? (
              <CircularProgress size={20} thickness={5} sx={{ color: 'white' }} />
            ) : (
              <SendIcon fontSize="small" />
            )}
          </IconButton>
        </InputContainer>
      </form>
    </ChatContainer>
  );
};

export default ChatBar; 