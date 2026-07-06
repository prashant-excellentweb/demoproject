import { useEffect, useState } from "react";
import { MessageCircle, MoreVertical, Search, UserPlus } from "lucide-react";
import { chatApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import type { Conversation } from "@/types";
import Avatar from "./Avatar";
import GroupAvatar from "./GroupAvatar";
import StatusBar from "./StatusBar";
import {
  formatChatTime,
  getDisplayName,
  getMessagePreview,
  getOtherParticipant,
} from "@/utils/format";

interface Props {
  activeId: number | null;
  onSelect: (conv: Conversation) => void;
  onNewChat: () => void;
  onNewGroup: () => void;
  onProfile: () => void;
  onCreateStatus: () => void;
  onViewStatus: (userId: number, statuses: import("@/types").Status[], startIndex?: number) => void;
  refreshKey: number;
  onConversationsChange?: (conversations: Conversation[]) => void;
}

export default function ChatList({
  activeId,
  onSelect,
  onNewChat,
  onNewGroup,
  onProfile,
  onCreateStatus,
  onViewStatus,
  refreshKey,
  onConversationsChange,
}: Props) {
  const { user } = useAuth();
  const { onMessage, connected } = useWebSocket();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [search, setSearch] = useState("");

  const loadConversations = () => {
    chatApi.getConversations().then((res) => {
      setConversations(res.data);
      onConversationsChange?.(res.data);
    }).catch(console.error);
  };

  useEffect(() => {
    loadConversations();
  }, [refreshKey]);

  // Real-time: refresh chat list when any new message arrives
  useEffect(() => {
    return onMessage(() => {
      loadConversations();
    });
  }, [onMessage]);

  // Fallback polling when WebSocket is disconnected
  useEffect(() => {
    if (connected) return;
    const interval = setInterval(loadConversations, 5000);
    return () => clearInterval(interval);
  }, [connected]);

  const filtered = conversations.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    if (c.is_group) return c.group_name.toLowerCase().includes(q);
    const other = getOtherParticipant(c, user!.id);
    return other && getDisplayName(other).toLowerCase().includes(q);
  });

  const getChatName = (c: Conversation) => {
    if (c.is_group) return c.group_name;
    const other = getOtherParticipant(c, user!.id);
    return other ? getDisplayName(other) : "Unknown";
  };

  const getChatAvatar = (c: Conversation) => {
    if (c.is_group) return null;
    return getOtherParticipant(c, user!.id);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <button type="button" onClick={onProfile} style={{ border: "none", background: "none", padding: 0, cursor: "pointer" }}>
          <Avatar user={user!} size={40} />
        </button>
        <div className="header-actions" style={{ alignItems: "center", gap: 8 }}>
          <span
            title={connected ? "Real-time connected" : "Connecting…"}
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: connected ? "var(--wa-green)" : "#ccc",
              flexShrink: 0,
            }}
          />
          <button className="icon-btn" title="New chat" onClick={onNewChat}>
            <MessageCircle size={22} />
          </button>
          <button className="icon-btn" title="New group" onClick={onNewGroup}>
            <UserPlus size={22} />
          </button>
          <button className="icon-btn" title="Menu" onClick={onProfile}>
            <MoreVertical size={22} />
          </button>
        </div>
      </div>

      <div className="search-bar">
        <div className="search-wrapper">
          <Search size={18} />
          <input
            placeholder="Search or start new chat"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <StatusBar onViewStatus={onViewStatus} onCreateStatus={onCreateStatus} />

      <div className="chat-list">
        {filtered.map((c) => {
          const avatarUser = getChatAvatar(c);
          const lastMsg = c.last_message;
          const preview = lastMsg
            ? c.is_group
              ? `${getDisplayName(lastMsg.sender)}: ${getMessagePreview(lastMsg)}`
              : getMessagePreview(lastMsg)
            : "No messages yet";
          return (
            <div
              key={c.id}
              className={`chat-item ${activeId === c.id ? "active" : ""}`}
              onClick={() => onSelect(c)}
            >
              {avatarUser ? (
                <Avatar user={avatarUser} />
              ) : (
                <GroupAvatar name={c.group_name} imageUrl={c.group_avatar_url} />
              )}
              <div className="chat-info">
                <div className="chat-info-top">
                  <span className="chat-name">{getChatName(c)}</span>
                  {lastMsg && (
                    <span className="chat-time">{formatChatTime(lastMsg.created_at)}</span>
                  )}
                </div>
                <div className="chat-info-top">
                  <span className="chat-preview">{preview}</span>
                  {c.unread_count > 0 && (
                    <span className="unread-badge">{c.unread_count}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
