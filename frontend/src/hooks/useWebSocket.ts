import { useEffect, useRef, useCallback } from 'react';
import type { WsEvent } from '../types';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/api/v1';

export function useWebSocket(
  path: string,
  onMessage: (event: WsEvent) => void,
  enabled = true
) {
  const ws = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!enabled) return;

    const socket = new WebSocket(`${WS_BASE}${path}`);
    ws.current = socket;

    socket.onmessage = (e) => {
      try {
        const data: WsEvent = JSON.parse(e.data);
        onMessageRef.current(data);
      } catch {/* ignore malformed frames */}
    };

    // Heartbeat ping every 25s
    const ping = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send('ping');
    }, 25_000);

    return () => {
      clearInterval(ping);
      socket.close();
    };
  }, [path, enabled]);

  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
