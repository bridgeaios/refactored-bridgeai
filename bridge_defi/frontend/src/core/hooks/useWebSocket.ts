import { useEffect, useRef, useState } from 'react';

export type WsStatus = 'connecting' | 'open' | 'closed' | 'error';

interface UseWebSocketOptions {
  onMessage?: (event: MessageEvent) => void;
  reconnectDelayMs?: number;
}

export function useWebSocket(url: string | null, options: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>('closed');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!url) return;

    function connect() {
      setStatus('connecting');
      const ws = new WebSocket(url!);
      wsRef.current = ws;

      ws.onopen = () => setStatus('open');
      ws.onmessage = options.onMessage ?? (() => {});
      ws.onerror = () => setStatus('error');
      ws.onclose = () => {
        setStatus('closed');
        reconnectTimer.current = setTimeout(connect, options.reconnectDelayMs ?? 3000);
      };
    }

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [url, options.onMessage, options.reconnectDelayMs]);

  return { status, ws: wsRef.current };
}
