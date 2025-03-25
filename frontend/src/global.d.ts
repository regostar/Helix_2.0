import { Socket } from 'socket.io-client';

// Add socket to Window interface
declare global {
  interface Window {
    socket: Socket | null;
  }
}

// This is needed to make this file a module
export {}; 