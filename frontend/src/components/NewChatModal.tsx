import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { authApi, chatApi } from "@/api/client";
import type { User } from "@/types";
import Avatar from "./Avatar";
import { getDisplayName } from "@/utils/format";

interface Props {
  onClose: () => void;
  onChatCreated: (conversation?: import("@/types").Conversation) => void;
}

export default function NewChatModal({ onClose, onChatCreated }: Props) {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (query.length < 2) {
      setUsers([]);
      return;
    }
    const timer = setTimeout(() => {
      authApi.searchUsers(query).then((res) => setUsers(res.data)).catch(console.error);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const startChat = async (userId: number) => {
    setLoading(true);
    try {
      const res = await chatApi.createDirectChat(userId);
      onChatCreated(res.data);
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3>New Chat</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>
        <div className="form-group">
          <input
            placeholder="Search by name or phone number"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
        </div>
        <div className="user-search-results">
          {users.map((u) => (
            <div key={u.id} className="user-result" onClick={() => !loading && startChat(u.id)}>
              <Avatar user={u} size={44} />
              <div>
                <div style={{ fontWeight: 500 }}>{getDisplayName(u)}</div>
                <div style={{ fontSize: 13, color: "var(--wa-text-secondary)" }}>{u.phone_number}</div>
              </div>
            </div>
          ))}
          {query.length >= 2 && users.length === 0 && (
            <p style={{ textAlign: "center", color: "var(--wa-text-secondary)", padding: 20 }}>
              No users found
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
