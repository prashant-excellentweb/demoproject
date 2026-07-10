import { useEffect, useRef, useState } from "react";
import { Check, CheckCheck, FileText, SmilePlus, Trash2 } from "lucide-react";
import type { Message } from "@/types";
import { formatFileSize, formatMessageTime, getDisplayName } from "@/utils/format";

const QUICK_REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🙏", "🔥", "👏"];

interface Props {
  message: Message;
  isSent: boolean;
  showSenderName?: boolean;
  canDeleteForEveryone?: boolean;
  onDelete?: (message: Message, deleteFor: "me" | "everyone") => Promise<void> | void;
  onReact?: (message: Message, emoji: string) => Promise<void> | void;
}

export default function MessageBubble({
  message,
  isSent,
  showSenderName = false,
  canDeleteForEveryone = false,
  onDelete,
  onReact,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reactOpen, setReactOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [reacting, setReacting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const reactRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen && !reactOpen) return;
    const handleClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (menuRef.current && !menuRef.current.contains(target)) setMenuOpen(false);
      if (reactRef.current && !reactRef.current.contains(target)) setReactOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen, reactOpen]);

  const handleDelete = async (deleteFor: "me" | "everyone") => {
    if (!onDelete || deleting) return;
    const confirmText =
      deleteFor === "everyone"
        ? "Delete this message for everyone?"
        : "Delete this message for you only? Others will still see it.";
    if (!window.confirm(confirmText)) return;
    setDeleting(true);
    setMenuOpen(false);
    try {
      await onDelete(message, deleteFor);
    } finally {
      setDeleting(false);
    }
  };

  const handleReact = async (emoji: string) => {
    if (!onReact || reacting || message.is_deleted) return;
    setReacting(true);
    setReactOpen(false);
    try {
      await onReact(message, emoji);
    } finally {
      setReacting(false);
    }
  };

  const renderContent = () => {
    if (message.is_deleted) {
      return <p className="message-text message-deleted">This message was deleted</p>;
    }

    switch (message.message_type) {
      case "image":
        return (
          <div className="message-media">
            <img src={message.file_url || ""} alt={message.file_name} loading="lazy" />
            {message.content && <p className="message-text">{message.content}</p>}
          </div>
        );
      case "video":
        return (
          <div className="message-media">
            <video src={message.file_url || ""} controls />
            {message.content && <p className="message-text">{message.content}</p>}
          </div>
        );
      case "pdf":
      case "document":
        return (
          <div className="message-file">
            <FileText size={32} color="#128c7e" />
            <div>
              <a href={message.file_url || "#"} target="_blank" rel="noopener noreferrer">
                {message.file_name || "Document"}
              </a>
              <div style={{ fontSize: 11, color: "var(--wa-text-secondary)" }}>
                {formatFileSize(message.file_size)}
              </div>
            </div>
          </div>
        );
      case "audio":
        return (
          <audio src={message.file_url || ""} controls style={{ width: "100%", minWidth: 200 }} />
        );
      default:
        return <p className="message-text">{message.content}</p>;
    }
  };

  const reactions = message.reactions || [];

  return (
    <div className={`message-row ${isSent ? "sent" : "received"}`}>
      <div
        className={`message-bubble ${message.is_deleted ? "deleted" : ""}`}
        onContextMenu={(e) => {
          if (message.is_deleted) return;
          e.preventDefault();
          setReactOpen(true);
        }}
      >
        {showSenderName && !isSent && !message.is_deleted && (
          <div className="message-sender-name">{getDisplayName(message.sender)}</div>
        )}
        {renderContent()}

        {reactions.length > 0 && !message.is_deleted && (
          <div className="message-reactions">
            {reactions.map((r) => (
              <button
                key={r.emoji}
                type="button"
                className={`reaction-chip ${message.my_reaction === r.emoji ? "mine" : ""}`}
                title={`${r.count} reaction${r.count === 1 ? "" : "s"}`}
                disabled={reacting}
                onClick={() => handleReact(r.emoji)}
              >
                <span>{r.emoji}</span>
                {r.count > 1 && <span className="reaction-count">{r.count}</span>}
              </button>
            ))}
          </div>
        )}

        <div className="message-meta">
          <span className="message-time">{formatMessageTime(message.created_at)}</span>
          {isSent && !message.is_deleted && (
            message.is_read ? <CheckCheck size={14} color="#53bdeb" /> : <Check size={14} color="#8696a0" />
          )}
          {!message.is_deleted && (
            <button
              type="button"
              className="message-action-btn"
              title="React"
              disabled={reacting}
              onClick={() => setReactOpen((o) => !o)}
            >
              <SmilePlus size={13} />
            </button>
          )}
          {!message.is_deleted && (
            <button
              type="button"
              className="message-action-btn"
              title="Delete"
              disabled={deleting}
              onClick={() => setMenuOpen((o) => !o)}
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>

        {reactOpen && !message.is_deleted && (
          <div className="reaction-picker" ref={reactRef}>
            {QUICK_REACTIONS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                className={message.my_reaction === emoji ? "active" : ""}
                disabled={reacting}
                onClick={() => handleReact(emoji)}
              >
                {emoji}
              </button>
            ))}
          </div>
        )}

        {menuOpen && !message.is_deleted && (
          <div className="message-action-menu" ref={menuRef}>
            <button type="button" onClick={() => handleDelete("me")} disabled={deleting}>
              <Trash2 size={14} />
              {deleting ? "Deleting..." : "Delete for me"}
            </button>
            {canDeleteForEveryone && (
              <button type="button" onClick={() => handleDelete("everyone")} disabled={deleting}>
                <Trash2 size={14} />
                Delete for everyone
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
