import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { authApi, chatApi } from "@/api/client";
import type { Conversation, User } from "@/types";
import Avatar from "./Avatar";
import { getDisplayName } from "@/utils/format";

interface Props {
  onClose: () => void;
  onGroupCreated: (conversation: Conversation) => void;
}

export default function NewGroupModal({ onClose, onGroupCreated }: Props) {
  const [groupName, setGroupName] = useState("");
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [selected, setSelected] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  const isSelected = (userId: number) => selected.some((u) => u.id === userId);

  const toggleUser = (user: User) => {
    setSelected((prev) =>
      isSelected(user.id) ? prev.filter((u) => u.id !== user.id) : [...prev, user]
    );
  };

  const removeSelected = (userId: number) => {
    setSelected((prev) => prev.filter((u) => u.id !== userId));
  };

  const createGroup = async () => {
    const name = groupName.trim();
    if (name.length < 2) {
      setError("Group name must be at least 2 characters.");
      return;
    }
    if (selected.length === 0) {
      setError("Add at least one participant.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const res = await chatApi.createGroup(
        name,
        selected.map((u) => u.id)
      );
      onGroupCreated(res.data);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create group.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>New Group</h3>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="form-group">
          <label>Group name</label>
          <input
            placeholder="e.g. Family, Work team"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            maxLength={100}
            autoFocus
          />
        </div>

        {selected.length > 0 && (
          <div className="selected-participants">
            {selected.map((u) => (
              <span key={u.id} className="participant-chip">
                {getDisplayName(u)}
                <button type="button" onClick={() => removeSelected(u.id)} aria-label="Remove">
                  <X size={14} />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="form-group">
          <label>Add participants</label>
          <input
            placeholder="Search by name or phone number"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="user-search-results">
          {users.map((u) => {
            const picked = isSelected(u.id);
            return (
              <div
                key={u.id}
                className={`user-result ${picked ? "selected" : ""}`}
                onClick={() => toggleUser(u)}
              >
                <Avatar user={u} size={44} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500 }}>{getDisplayName(u)}</div>
                  <div style={{ fontSize: 13, color: "var(--wa-text-secondary)" }}>{u.phone_number}</div>
                </div>
                {picked && <Check size={20} color="var(--wa-teal)" />}
              </div>
            );
          })}
          {query.length >= 2 && users.length === 0 && (
            <p style={{ textAlign: "center", color: "var(--wa-text-secondary)", padding: 20 }}>
              No users found
            </p>
          )}
        </div>

        <button
          type="button"
          className="btn-primary"
          style={{ marginTop: 16 }}
          disabled={loading || groupName.trim().length < 2 || selected.length === 0}
          onClick={createGroup}
        >
          {loading ? "Creating..." : `Create group (${selected.length} member${selected.length === 1 ? "" : "s"})`}
        </button>
      </div>
    </div>
  );
}
