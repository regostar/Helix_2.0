import { useState, useEffect } from 'react';
import { useSocket } from '../components/SocketContext';

export interface SuggestedPrompt {
  id: string;
  text: string;
  description: string;
}

export function useSuggestedPrompts() {
  const { socket } = useSocket();
  const [suggestedPrompts, setSuggestedPrompts] = useState<SuggestedPrompt[]>([]);

  useEffect(() => {
    if (!socket) return;

    // Handle receiving suggested prompts
    const handleSuggestedPrompts = (data: { prompts: SuggestedPrompt[] }) => {
      console.log('Received suggested prompts:', data.prompts);
      setSuggestedPrompts(data.prompts);
    };

    // Set up event listener
    socket.on('suggested_prompts', handleSuggestedPrompts);

    // Manually request suggested prompts on mount
    socket.emit('get_suggested_prompts');

    // Cleanup
    return () => {
      socket.off('suggested_prompts', handleSuggestedPrompts);
    };
  }, [socket]);

  return suggestedPrompts;
} 