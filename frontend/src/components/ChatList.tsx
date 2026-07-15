import { useEffect, useRef, useState } from "react";
import {
  Archive,
  ArchiveRestore,
  Ban,
  MessageCircle,
  MoreVertical,
  Pin,
  PinOff,
  Search,
  ShieldOff,
  Star,
  UserPlus,
} from "lucide-react";
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
  { id: "archived", label: "Archived" },
  { id: "blocked", label: "Blocked" },
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
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (menuOpenId == null) return;
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenId(null);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpenId]);

  const applyConversationUpdate = (updated: Conversation) => {
    setConversations((prev) => {
      const next = prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c));
      const shouldRemove =
        (filter === "archived" && !updated.is_archived) ||
        (filter === "blocked" && !updated.is_blocked) ||
        (filter !== "archived" && updated.is_archived) ||
        (filter === "favourites" && !updated.is_favourite);
      if (shouldRemove) {
        return next.filter((c) => c.id !== updated.id);
      }
      return next;
    });
  };

  const handleToggleFavourite = async (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    if (busyId) return;
    setBusyId(conv.id);
    try {
      const res = await chatApi.toggleFavourite(conv.id);
      applyConversationUpdate(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setBusyId(null);
    }
  };

  const handleArchive = async (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    if (busyId) return;
    setBusyId(conv.id);
    setMenuOpenId(null);
    try {
      const action = conv.is_archived ? "unarchive" : "archive";
      const res = await chatApi.archiveConversation(conv.id, action);
      applyConversationUpdate(res.data);
      loadConversations(filter);
    } catch (err) {
      console.error(err);
    } finally {
      setBusyId(null);
    }
  };

  const handleBlock = async (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    if (busyId) return;
    const action = conv.is_blocked ? "unblock" : "block";
    if (action === "block" && !window.confirm("Block this chat? You won't be able to send messages until you unblock.")) {
      return;
    }
    setBusyId(conv.id);
    setMenuOpenId(null);
    try {
      const res = await chatApi.blockConversation(conv.id, action);
      applyConversationUpdate(res.data);
      loadConversations(filter);
    } catch (err) {
      console.error(err);
    } finally {
      setBusyId(null);
    }
  };

  const handlePin = async (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    if (busyId) return;
    setBusyId(conv.id);
    setMenuOpenId(null);
    try {
      const action = conv.is_pinned ? "unpin" : "pin";
      const res = await chatApi.pinConversation(conv.id, action);
      applyConversationUpdate(res.data);
      loadConversations(filter);
    } catch (err) {
      console.error(err);
    } finally {
      setBusyId(null);
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

  const emptyMessage = () => {
    switch (filter) {
      case "unread": return "No unread chats";
      case "favourites": return "No favourite chats yet";
      case "groups": return "No group chats yet";
      case "archived": return "No archived chats";
      case "blocked": return "No blocked chats";
      default: return "No chats yet";
    }
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
          <p className="chat-filter-empty">{emptyMessage()}</p>
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
              className={`chat-item ${activeId === c.id ? "active" : ""} ${c.is_blocked ? "blocked" : ""}`}
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
                    {c.is_pinned && <Pin size={12} className="pinned-inline-icon" fill="currentColor" />}
                    {c.is_favourite && <Star size={12} className="favourite-inline-star" fill="currentColor" />}
                    {c.is_blocked && <Ban size={12} className="blocked-inline-icon" />}
                    {getChatName(c)}
                  </span>
                  {lastMsg && (
                    <span className="chat-time">{formatChatTime(lastMsg.created_at)}</span>
                  )}
                </div>
                <div className="chat-info-top">
                  <span className="chat-preview">
                    {c.is_blocked ? "Blocked" : preview}
                  </span>
                  <span className="chat-item-actions">
                    <button
                      type="button"
                      className={`favourite-btn ${c.is_favourite ? "active" : ""}`}
                      title={c.is_favourite ? "Remove from favourites" : "Add to favourites"}
                      disabled={busyId === c.id}
                      onClick={(e) => handleToggleFavourite(e, c)}
                    >
                      <Star size={16} fill={c.is_favourite ? "currentColor" : "none"} />
                    </button>
                    <button
                      type="button"
                      className="chat-more-btn"
                      title="Chat options"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId((id) => (id === c.id ? null : c.id));
                      }}
                    >
                      <MoreVertical size={16} />
                    </button>
                    {c.unread_count > 0 && !c.is_blocked && (
                      <span className="unread-badge">{c.unread_count}</span>
                    )}
                  </span>
                </div>
              </div>

              {menuOpenId === c.id && (
                <div className="chat-item-menu" ref={menuRef} onClick={(e) => e.stopPropagation()}>
                  <button type="button" onClick={(e) => handlePin(e, c)} disabled={busyId === c.id}>
                    {c.is_pinned ? <PinOff size={16} /> : <Pin size={16} />}
                    {c.is_pinned ? "Unpin" : "Pin"}
                  </button>
                  <button type="button" onClick={(e) => handleArchive(e, c)} disabled={busyId === c.id}>
                    {c.is_archived ? <ArchiveRestore size={16} /> : <Archive size={16} />}
                    {c.is_archived ? "Unarchive" : "Archive"}
                  </button>
                  <button type="button" onClick={(e) => handleBlock(e, c)} disabled={busyId === c.id}>
                    {c.is_blocked ? <ShieldOff size={16} /> : <Ban size={16} />}
                    {c.is_blocked ? "Unblock" : "Block"}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
