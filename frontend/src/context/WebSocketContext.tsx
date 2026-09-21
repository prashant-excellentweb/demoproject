import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Conversation, Message } from "@/types";

function getWebSocketUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/chat/`;
}

const WS_URL = getWebSocketUrl();

type WSMessageHandler = (message: Message) => void;
type TypingHandler = (data: { user_id: number; user_name: string; is_typing: boolean }) => void;
type MessageDeletedHandler = (message: Message) => void;
type MessageUpdatedHandler = (message: Message) => void;
type PresenceHandler = (data: {
  user_id: number;
  is_online: boolean;
  last_seen: string | null;
}) => void;
type ConversationUpdatedHandler = (conversation: Conversation) => void;

interface WebSocketContextType {
  connected: boolean;
  joinConversation: (id: number) => void;
  leaveConversation: () => void;
  sendTyping: (isTyping: boolean) => void;
  markRead: (conversationId: number) => void;
  onMessage: (handler: WSMessageHandler) => () => void;
  onTyping: (handler: TypingHandler) => () => void;
  onMessageDeleted: (handler: MessageDeletedHandler) => () => void;
  onMessageUpdated: (handler: MessageUpdatedHandler) => () => void;
  onPresence: (handler: PresenceHandler) => () => void;
  onConversationUpdated: (handler: ConversationUpdatedHandler) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const messageHandlers = useRef<Set<WSMessageHandler>>(new Set());
  const typingHandlers = useRef<Set<TypingHandler>>(new Set());
  const deletedHandlers = useRef<Set<MessageDeletedHandler>>(new Set());
  const updatedHandlers = useRef<Set<MessageUpdatedHandler>>(new Set());
  const presenceHandlers = useRef<Set<PresenceHandler>>(new Set());
  const conversationUpdatedHandlers = useRef<Set<ConversationUpdatedHandler>>(new Set());
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
      } else if (data.type === "message_deleted" && data.message) {
        deletedHandlers.current.forEach((h) => h(data.message));
      } else if (data.type === "message_updated" && data.message) {
        updatedHandlers.current.forEach((h) => h(data.message));
      } else if (data.type === "typing") {
        typingHandlers.current.forEach((h) => h(data));
      } else if (data.type === "presence") {
        presenceHandlers.current.forEach((h) =>
          h({
            user_id: data.user_id,
            is_online: Boolean(data.is_online),
            last_seen: data.last_seen ?? null,
          })
        );
      } else if (data.type === "conversation_updated" && data.conversation) {
        conversationUpdatedHandlers.current.forEach((h) => h(data.conversation));
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

  const onMessageDeleted = (handler: MessageDeletedHandler) => {
    deletedHandlers.current.add(handler);
    return () => deletedHandlers.current.delete(handler);
  };

  const onMessageUpdated = (handler: MessageUpdatedHandler) => {
    updatedHandlers.current.add(handler);
    return () => updatedHandlers.current.delete(handler);
  };

  const onPresence = (handler: PresenceHandler) => {
    presenceHandlers.current.add(handler);
    return () => presenceHandlers.current.delete(handler);
  };

  const onConversationUpdated = (handler: ConversationUpdatedHandler) => {
    conversationUpdatedHandlers.current.add(handler);
    return () => conversationUpdatedHandlers.current.delete(handler);
  };

  return (
    <WebSocketContext.Provider
      value={{
        connected,
        joinConversation,
        leaveConversation,
        sendTyping,
        markRead,
        onMessage,
        onTyping,
        onMessageDeleted,
        onMessageUpdated,
        onPresence,
        onConversationUpdated,
      }}
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
