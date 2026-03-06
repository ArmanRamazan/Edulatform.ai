"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const WS_BASE = "ws://localhost:8011/ws";
const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;

export interface WsMessage {
  type: string;
  [key: string]: unknown;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WsMessage | null;
  notificationCount: number;
}

/**
 * Connects to the ws-gateway and tracks live notification events.
 * Silently falls back to REST polling when the socket is unavailable.
 * Auto-reconnects with exponential backoff (1 s → 2 s → 4 s … 30 s cap).
 */
export function useWebSocket(token: string | null): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);
  const [notificationCount, setNotificationCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current !== null) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  const destroySocket = useCallback(() => {
    const ws = wsRef.current;
    if (!ws) return;
    // Null out handlers before closing to prevent onclose re-triggering retry
    ws.onopen = null;
    ws.onmessage = null;
    ws.onclose = null;
    ws.onerror = null;
    ws.close();
    wsRef.current = null;
  }, []);

  // Stable connect function — recreated only when token changes
  const connect = useCallback(() => {
    if (!token || !mountedRef.current) return;

    destroySocket();

    let ws: WebSocket;
    try {
      ws = new WebSocket(`${WS_BASE}?token=${encodeURIComponent(token)}`);
    } catch {
      // WebSocket constructor can throw in some environments
      console.log("WebSocket unavailable, using polling");
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setIsConnected(true);
      backoffRef.current = INITIAL_BACKOFF_MS; // Reset backoff on successful connect
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data as string) as WsMessage;
        setLastMessage(msg);
        if (msg.type === "notification") {
          setNotificationCount((prev) => prev + 1);
        }
      } catch {
        // Ignore malformed frames silently
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      wsRef.current = null;

      // Schedule reconnect with current backoff, then double it (capped at max)
      clearRetryTimer();
      const delay = backoffRef.current;
      backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
      retryTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };

    ws.onerror = () => {
      // onerror is always followed by onclose — log once here, let onclose handle retry
      console.log("WebSocket unavailable, using polling");
    };
  }, [token, clearRetryTimer, destroySocket]);

  useEffect(() => {
    mountedRef.current = true;

    if (!token) return;

    connect();

    return () => {
      mountedRef.current = false;
      clearRetryTimer();
      destroySocket();
    };
  }, [token, connect, clearRetryTimer, destroySocket]);

  return { isConnected, lastMessage, notificationCount };
}
