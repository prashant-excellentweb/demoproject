import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Message } from "@/types";

function getWebSocketUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // Use same host as the page so Vite dev proxy forwards /ws -> backend
  return `${protocol}//${window.location.host}/ws/chat/`;
}

const WS_URL = getWebSocketUrl();

type WSMessageHandler = (message: Message) => void;
type TypingHandler = (data: { user_id: number; user_name: string; is_typing: boolean }) => void;

interface WebSocketContextType {
  connected: boolean;
  joinConversation: (id: number) => void;
  leaveConversation: () => void;
  sendTyping: (isTyping: boolean) => void;
  markRead: (conversationId: number) => void;
  onMessage: (handler: WSMessageHandler) => () => void;
  onTyping: (handler: TypingHandler) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const messageHandlers = useRef<Set<WSMessageHandler>>(new Set());
  const typingHandlers = useRef<Set<TypingHandler>>(new Set());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const ws = new WebSocket(`${WS_URL}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.info("[ChatApp] WebSocket connected");
    };
    ws.onclose = (event) => {
      setConnected(false);
      console.warn("[ChatApp] WebSocket closed", event.code, event.reason);
      reconnectTimer.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => {
      console.error("[ChatApp] WebSocket error — check Network tab (WS filter)");
      ws.close();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "message" && data.message) {
        messageHandlers.current.forEach((h) => h(data.message));
      } else if (data.type === "typing") {
        typingHandlers.current.forEach((h) => h(data));
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = (data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  const joinConversation = (id: number) => send({ action: "join_conversation", conversation_id: id });
  const leaveConversation = () => send({ action: "leave_conversation" });
  const sendTyping = (isTyping: boolean) => send({ action: "typing", is_typing: isTyping });
  const markRead = (conversationId: number) => send({ action: "mark_read", conversation_id: conversationId });

  const onMessage = (handler: WSMessageHandler) => {
    messageHandlers.current.add(handler);
    return () => messageHandlers.current.delete(handler);
  };

  const onTyping = (handler: TypingHandler) => {
    typingHandlers.current.add(handler);
    return () => typingHandlers.current.delete(handler);
  };

  return (
    <WebSocketContext.Provider
      value={{ connected, joinConversation, leaveConversation, sendTyping, markRead, onMessage, onTyping }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWebSocket must be used within WebSocketProvider");
  return ctx;
}
