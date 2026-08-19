"use client";

import { useEffect, useRef, useCallback } from "react";

type MessageHandler = (event: MessageEvent) => void;

export function useInboxWebSocket(onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"}/ws/inbox/?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => console.log("[WS] Connected to Wow Chat inbox");

    ws.onmessage = onMessage;

    ws.onclose = (e) => {
      console.log("[WS] Disconnected, reconnecting in 3s...", e.code);
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    ws.onerror = (err) => console.error("[WS] Error:", err);
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
