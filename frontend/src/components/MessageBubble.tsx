import { useEffect, useRef, useState } from "react";
import { Check, CheckCheck, CornerUpLeft, FileText, Forward, Pencil, SmilePlus, Trash2 } from "lucide-react";
import type { Message } from "@/types";
import { canEditMessage, formatFileSize, formatMessageTime, getDisplayName, getQuotePreview, MESSAGE_EDIT_WINDOW_MS } from "@/utils/format";
import MentionText from "./MentionText";

const QUICK_REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🙏", "🔥", "👏"];

interface Props {
  message: Message;
  isSent: boolean;
  showSenderName?: boolean;
  canDeleteForEveryone?: boolean;
  onDelete?: (message: Message, deleteFor: "me" | "everyone") => Promise<void> | void;
  onReact?: (message: Message, emoji: string) => Promise<void> | void;
  onReply?: (message: Message) => void;
  onForward?: (message: Message) => void;
  onEdit?: (message: Message, content: string) => Promise<void> | void;
  onOpenViewOnce?: (message: Message) => Promise<void> | void;
  highlighted?: boolean;
}

export default function MessageBubble({
  message,
  isSent,
  showSenderName = false,
  canDeleteForEveryone = false,
  onDelete,
  onReact,
  onReply,
  onForward,
  onEdit,
  onOpenViewOnce,
  highlighted = false,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reactOpen, setReactOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [reacting, setReacting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);
  const [savingEdit, setSavingEdit] = useState(false);
  const [openingViewOnce, setOpeningViewOnce] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const menuRef = useRef<HTMLDivElement>(null);
  const reactRef = useRef<HTMLDivElement>(null);
  const editRef = useRef<HTMLTextAreaElement>(null);

  const allowEdit = Boolean(onEdit) && canEditMessage(message, isSent, now);

  useEffect(() => {
    if (!allowEdit) return;
    const remaining =
      MESSAGE_EDIT_WINDOW_MS - (Date.now() - new Date(message.created_at).getTime());
    if (remaining <= 0) return;
    const timer = window.setTimeout(() => setNow(Date.now()), remaining + 50);
    return () => window.clearTimeout(timer);
  }, [allowEdit, message.created_at]);

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

  const startEdit = () => {
    if (!allowEdit) return;
    setMenuOpen(false);
    setEditText(message.content);
    setEditing(true);
    window.setTimeout(() => editRef.current?.focus(), 0);
  };

  const cancelEdit = () => {
    setEditing(false);
    setEditText(message.content);
  };

  const saveEdit = async () => {
    if (!onEdit || savingEdit) return;
    const next = editText.trim();
    if (!next) return;
    if (next === message.content.trim()) {
      setEditing(false);
      return;
    }
    setSavingEdit(true);
    try {
      await onEdit(message, next);
      setEditing(false);
    } catch (e) {
      console.error(e);
      alert(e instanceof Error ? e.message : "Failed to edit message.");
    } finally {
      setSavingEdit(false);
    }
  };

  const renderContent = () => {
    if (message.is_deleted) {
      return <p className="message-text message-deleted">This message was deleted</p>;
    }

    if (message.is_view_once) {
      if (message.view_once_opened) {
        return (
          <p className="message-text view-once-opened">
            {message.message_type === "video" ? "View once video opened" : "View once photo opened"}
          </p>
        );
      }
      if (isSent && message.file_url) {
        // Sender preview until opened
        if (message.message_type === "video") {
          return (
            <div className="message-media view-once-preview">
              <video src={message.file_url} controls />
              <span className="view-once-badge">View once</span>
            </div>
          );
        }
        return (
          <div className="message-media view-once-preview">
            <img src={message.file_url} alt={message.file_name} loading="lazy" />
            <span className="view-once-badge">View once</span>
          </div>
        );
      }
      if (!isSent && onOpenViewOnce) {
        return (
          <button
            type="button"
            className="view-once-open-btn"
            disabled={openingViewOnce}
            onClick={async () => {
              setOpeningViewOnce(true);
              try {
                await onOpenViewOnce(message);
              } finally {
                setOpeningViewOnce(false);
              }
            }}
          >
            {openingViewOnce
              ? "Opening…"
              : message.message_type === "video"
                ? "Tap to view once video"
                : "Tap to view once photo"}
          </button>
        );
      }
      return (
        <p className="message-text">
          {message.message_type === "video" ? "View once video" : "View once photo"}
        </p>
      );
    }

    switch (message.message_type) {
      case "image":
        return (
          <div className="message-media">
            <img src={message.file_url || ""} alt={message.file_name} loading="lazy" />
            {message.content && (
              <p className="message-text">
                <MentionText
                  content={message.content}
                  mentions={message.mentions}
                  mentionEveryone={message.mention_everyone}
                />
              </p>
            )}
          </div>
        );
      case "video":
        return (
          <div className="message-media">
            <video src={message.file_url || ""} controls />
            {message.content && (
              <p className="message-text">
                <MentionText
                  content={message.content}
                  mentions={message.mentions}
                  mentionEveryone={message.mention_everyone}
                />
              </p>
            )}
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
        return (
          <p className="message-text">
            <MentionText
              content={message.content}
              mentions={message.mentions}
              mentionEveryone={message.mention_everyone}
            />
          </p>
        );
    }
  };

  const reactions = message.reactions || [];

  const quote = message.reply_to;

  return (
    <div
      className={`message-row ${isSent ? "sent" : "received"}${highlighted ? " search-hit" : ""}${
        message.mentioned_me && !isSent ? " mentioned-me" : ""
      }`}
      id={`msg-${message.id}`}
    >
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
        {message.is_forwarded && !message.is_deleted && (
          <div className="message-forwarded-label">
            <Forward size={12} />
            Forwarded
          </div>
        )}
        {quote && !message.is_deleted && (
          <button
            type="button"
            className="reply-quote"
            onClick={() => {
              document.getElementById(`msg-${quote.id}`)?.scrollIntoView({
                behavior: "smooth",
                block: "center",
              });
            }}
          >
            <span className="reply-quote-name">{quote.sender_name}</span>
            <span className="reply-quote-text">
              {quote.is_deleted ? "This message was deleted" : getQuotePreview(quote)}
            </span>
          </button>
        )}
        {editing ? (
          <div className="message-edit-form">
            <textarea
              ref={editRef}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={3}
              disabled={savingEdit}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  saveEdit();
                }
                if (e.key === "Escape") cancelEdit();
              }}
            />
            <div className="message-edit-actions">
              <button type="button" onClick={cancelEdit} disabled={savingEdit}>
                Cancel
              </button>
              <button
                type="button"
                className="save"
                onClick={saveEdit}
                disabled={savingEdit || !editText.trim()}
              >
                {savingEdit ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        ) : (
          renderContent()
        )}

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
          {message.is_edited && !message.is_deleted && (
            <span className="message-edited">edited</span>
          )}
          {message.expires_at && !message.is_deleted && (
            <span className="message-disappearing" title="Disappearing message">⏱</span>
          )}
          <span className="message-time">{formatMessageTime(message.created_at)}</span>
          {isSent && !message.is_deleted && (
            message.is_read ? <CheckCheck size={14} color="#53bdeb" /> : <Check size={14} color="#8696a0" />
          )}
          {!message.is_deleted && onReply && (
            <button
              type="button"
              className="message-action-btn"
              title="Reply"
              onClick={() => onReply(message)}
            >
              <CornerUpLeft size={13} />
            </button>
          )}
          {allowEdit && !editing && (
            <button
              type="button"
              className="message-action-btn"
              title="Edit"
              onClick={startEdit}
            >
              <Pencil size={13} />
            </button>
          )}
          {!message.is_deleted && onForward && (
            <button
              type="button"
              className="message-action-btn"
              title="Forward"
              onClick={() => onForward(message)}
            >
              <Forward size={13} />
            </button>
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
            {onReply && (
              <button
                type="button"
                className="neutral"
                onClick={() => {
                  setMenuOpen(false);
                  onReply(message);
                }}
              >
                <CornerUpLeft size={14} />
                Reply
              </button>
            )}
            {onForward && (
              <button
                type="button"
                className="neutral"
                onClick={() => {
                  setMenuOpen(false);
                  onForward(message);
                }}
              >
                <Forward size={14} />
                Forward
              </button>
            )}
            {allowEdit && (
              <button
                type="button"
                className="neutral"
                onClick={startEdit}
              >
                <Pencil size={14} />
                Edit
              </button>
            )}
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
