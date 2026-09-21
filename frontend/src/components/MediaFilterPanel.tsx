import { useEffect, useState } from "react";
import { FileText, Link2, Music, X } from "lucide-react";
import { chatApi } from "@/api/client";
import type { MediaFilterType, Message } from "@/types";
import { formatChatTime, getMessagePreview } from "@/utils/format";

const TABS: { id: MediaFilterType; label: string }[] = [
  { id: "photos", label: "Photos" },
  { id: "videos", label: "Videos" },
  { id: "links", label: "Links" },
  { id: "docs", label: "Docs" },
  { id: "audio", label: "Audio" },
];

interface Props {
  conversationId: number;
  onClose: () => void;
  onJumpToMessage?: (messageId: number) => void;
}

export default function MediaFilterPanel({ conversationId, onClose, onJumpToMessage }: Props) {
  const [type, setType] = useState<MediaFilterType>("photos");
  const [items, setItems] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    chatApi
      .getMedia(conversationId, type)
      .then((res) => setItems(res.data.results || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [conversationId, type]);

  return (
    <div className="media-filter-panel">
      <div className="media-filter-header">
        <h3>Media, links and docs</h3>
        <button type="button" className="icon-btn" onClick={onClose} title="Close">
          <X size={18} />
        </button>
      </div>
      <div className="media-filter-tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={type === tab.id}
            className={`media-filter-tab${type === tab.id ? " active" : ""}`}
            onClick={() => setType(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="media-filter-body">
        {loading && <p className="chat-filter-empty">Loading…</p>}
        {!loading && items.length === 0 && (
          <p className="chat-filter-empty">Nothing here yet</p>
        )}
        {!loading && type === "photos" && (
          <div className="media-grid">
            {items.map((m) => (
              <button
                key={m.id}
                type="button"
                className="media-grid-item"
                onClick={() => onJumpToMessage?.(m.id)}
              >
                {m.file_url ? (
                  <img src={m.file_url} alt={m.file_name || "Photo"} loading="lazy" />
                ) : (
                  <span>📷</span>
                )}
              </button>
            ))}
          </div>
        )}
        {!loading && type === "videos" && (
          <div className="media-grid">
            {items.map((m) => (
              <button
                key={m.id}
                type="button"
                className="media-grid-item"
                onClick={() => onJumpToMessage?.(m.id)}
              >
                {m.file_url ? (
                  <video src={m.file_url} muted />
                ) : (
                  <span>🎥</span>
                )}
              </button>
            ))}
          </div>
        )}
        {!loading && (type === "links" || type === "docs" || type === "audio") && (
          <ul className="media-list">
            {items.map((m) => (
              <li key={m.id}>
                <button type="button" onClick={() => onJumpToMessage?.(m.id)}>
                  <span className="media-list-icon">
                    {type === "links" ? (
                      <Link2 size={18} />
                    ) : type === "audio" ? (
                      <Music size={18} />
                    ) : (
                      <FileText size={18} />
                    )}
                  </span>
                  <span className="media-list-text">
                    <strong>{getMessagePreview(m) || m.file_name || m.content}</strong>
                    <small>{formatChatTime(m.created_at)}</small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
