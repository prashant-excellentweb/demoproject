import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { chatApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import type { Conversation, Message } from "@/types";
import Avatar from "./Avatar";
import GroupAvatar from "./GroupAvatar";
import { getDisplayName, getOtherParticipant } from "@/utils/format";
import { isGroupAdmin } from "@/utils/group";

const MAX_TARGETS = 10;

interface Props {
  sourceConversationId: number;
  message: Message;
  onClose: () => void;
  onForwarded: () => void;
}

export default function ForwardPicker({
  sourceConversationId,
  message,
  onClose,
  onForwarded,
}: Props) {
  const { user } = useAuth();
  const [chats, setChats] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    chatApi
      .getConversations("all")
      .then((res) => {
        if (cancelled) return;
        setChats(
          res.data.filter((c) => c.id !== sourceConversationId && !c.is_blocked)
        );
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load chats.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sourceConversationId]);

  const cannotPost = (c: Conversation) =>
    Boolean(user && c.is_group && c.admins_only_messages && !isGroupAdmin(c, user.id));

  const toggle = (id: number) => {
    const chat = chats.find((c) => c.id === id);
    if (chat && cannotPost(chat) && !selected.includes(id)) return;
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_TARGETS) return prev;
      return [...prev, id];
    });
    setError("");
  };

  const handleForward = async () => {
    if (selected.length === 0 || sending) return;
    setSending(true);
    setError("");
    try {
      const res = await chatApi.forwardMessage(sourceConversationId, message.id, selected);
      const failed = res.data?.failed || [];
      if (failed.length > 0 && (!res.data.forwarded || res.data.forwarded.length === 0)) {
        setError(failed[0].error || "Could not forward this message.");
        return;
      }
      if (failed.length > 0) {
        alert(`Forwarded to some chats. ${failed.length} failed.`);
      }
      onForwarded();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to forward.");
    } finally {
      setSending(false);
    }
  };

  const chatLabel = (c: Conversation) => {
    if (c.is_group) return c.group_name;
    const other = user ? getOtherParticipant(c, user.id) : undefined;
    return other ? getDisplayName(other) : "Chat";
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal forward-picker" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>Forward to…</h3>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <p className="forward-picker-hint">Select up to {MAX_TARGETS} chats.</p>
        {error && <div className="error-msg">{error}</div>}
        <div className="user-search-results">
          {loading && (
            <p style={{ textAlign: "center", color: "var(--wa-text-secondary)", padding: 20 }}>
              Loading chats…
            </p>
          )}
          {!loading && chats.length === 0 && (
            <p style={{ textAlign: "center", color: "var(--wa-text-secondary)", padding: 20 }}>
              No other chats to forward to.
            </p>
          )}
          {chats.map((c) => {
            const checked = selected.includes(c.id);
            const locked = cannotPost(c);
            const other = user && !c.is_group ? getOtherParticipant(c, user.id) : undefined;
            return (
              <label
                key={c.id}
                className={`user-result forward-option ${checked ? "selected" : ""}${locked ? " disabled" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={locked || (!checked && selected.length >= MAX_TARGETS)}
                  onChange={() => toggle(c.id)}
                />
                {c.is_group || !other ? (
                  <GroupAvatar name={c.group_name} imageUrl={c.group_avatar_url} size={44} />
                ) : (
                  <Avatar user={other} size={44} />
                )}
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500 }}>{chatLabel(c)}</div>
                  <div style={{ fontSize: 13, color: "var(--wa-text-secondary)" }}>
                    {locked
                      ? "Only admins can send messages"
                      : c.is_group
                        ? `${c.participants.length} participants`
                        : other?.phone_number}
                  </div>
                </div>
              </label>
            );
          })}
        </div>
        <button
          type="button"
          className="btn-primary"
          style={{ marginTop: 12 }}
          disabled={sending || selected.length === 0}
          onClick={handleForward}
        >
          {sending ? "Forwarding…" : `Forward${selected.length ? ` (${selected.length})` : ""}`}
        </button>
      </div>
    </div>
  );
}
