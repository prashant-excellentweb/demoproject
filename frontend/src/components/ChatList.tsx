import { useEffect, useState } from "react";
import { MessageCircle, MoreVertical, Search, Star, UserPlus } from "lucide-react";
import { chatApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import type { ChatListFilter, Conversation } from "@/types";
import Avatar from "./Avatar";
import GroupAvatar from "./GroupAvatar";
import StatusBar from "./StatusBar";
import {
  formatChatTime,
  getDisplayName,
  getMessagePreview,
  getOtherParticipant,
} from "@/utils/format";

const FILTERS: { id: ChatListFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "unread", label: "Unread" },
  { id: "favourites", label: "Favourites" },
  { id: "groups", label: "Groups" },
];

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
  const [filter, setFilter] = useState<ChatListFilter>("all");
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const loadConversations = (activeFilter = filter) => {
    chatApi.getConversations(activeFilter).then((res) => {
      setConversations(res.data);
      onConversationsChange?.(res.data);
    }).catch(console.error);
  };

  useEffect(() => {
    loadConversations(filter);
  }, [refreshKey, filter]);

  useEffect(() => {
    return onMessage(() => {
      loadConversations(filter);
    });
  }, [onMessage, filter]);

  useEffect(() => {
    if (connected) return;
    const interval = setInterval(() => loadConversations(filter), 5000);
    return () => clearInterval(interval);
  }, [connected, filter]);

  const handleToggleFavourite = async (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    if (togglingId) return;
    setTogglingId(conv.id);
    try {
      const res = await chatApi.toggleFavourite(conv.id);
      setConversations((prev) => {
        const updated = prev.map((c) =>
          c.id === conv.id ? { ...c, is_favourite: res.data.is_favourite } : c
        );
        if (filter === "favourites" && !res.data.is_favourite) {
          return updated.filter((c) => c.id !== conv.id);
        }
        return updated;
      });
    } catch (err) {
      console.error(err);
    } finally {
      setTogglingId(null);
    }
  };

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

      <div className="chat-filter-tabs" role="tablist" aria-label="Chat filters">
        {FILTERS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={filter === tab.id}
            className={`chat-filter-tab ${filter === tab.id ? "active" : ""}`}
            onClick={() => setFilter(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <StatusBar onViewStatus={onViewStatus} onCreateStatus={onCreateStatus} />

      <div className="chat-list">
        {filtered.length === 0 && (
          <p className="chat-filter-empty">
            {filter === "unread" && "No unread chats"}
            {filter === "favourites" && "No favourite chats yet"}
            {filter === "groups" && "No group chats yet"}
            {filter === "all" && "No chats yet"}
          </p>
        )}
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
                  <span className="chat-name">
                    {c.is_favourite && <Star size={12} className="favourite-inline-star" fill="currentColor" />}
                    {getChatName(c)}
                  </span>
                  {lastMsg && (
                    <span className="chat-time">{formatChatTime(lastMsg.created_at)}</span>
                  )}
                </div>
                <div className="chat-info-top">
                  <span className="chat-preview">{preview}</span>
                  <span className="chat-item-actions">
                    <button
                      type="button"
                      className={`favourite-btn ${c.is_favourite ? "active" : ""}`}
                      title={c.is_favourite ? "Remove from favourites" : "Add to favourites"}
                      disabled={togglingId === c.id}
                      onClick={(e) => handleToggleFavourite(e, c)}
                    >
                      <Star size={16} fill={c.is_favourite ? "currentColor" : "none"} />
                    </button>
                    {c.unread_count > 0 && (
                      <span className="unread-badge">{c.unread_count}</span>
                    )}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
