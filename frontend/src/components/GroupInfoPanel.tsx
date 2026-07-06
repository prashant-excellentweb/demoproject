import { useRef, useState } from "react";
import { Camera, UserMinus, X } from "lucide-react";
import { chatApi } from "@/api/client";
import type { Conversation } from "@/types";
import Avatar from "./Avatar";
import GroupAvatar from "./GroupAvatar";
import { getDisplayName } from "@/utils/format";
import { isGroupAdmin } from "@/utils/group";

interface Props {
  conversation: Conversation;
  currentUserId: number;
  onClose: () => void;
  onUpdated: (conversation: Conversation) => void;
  onRefreshList: () => void;
}

export default function GroupInfoPanel({
  conversation,
  currentUserId,
  onClose,
  onUpdated,
  onRefreshList,
}: Props) {
  const isAdmin = isGroupAdmin(conversation, currentUserId);
  const [groupName, setGroupName] = useState(conversation.group_name);
  const [members, setMembers] = useState(conversation.participants);
  const [avatarUrl, setAvatarUrl] = useState(conversation.group_avatar_url);
  const [saving, setSaving] = useState(false);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const avatarRef = useRef<HTMLInputElement>(null);

  const saveGroup = async (overrides?: { name?: string; avatar?: File }) => {
    const name = (overrides?.name ?? groupName).trim();
    if (name.length < 2) {
      setError("Group name must be at least 2 characters.");
      return;
    }

    setError("");
    setSaving(true);
    try {
      const form = new FormData();
      form.append("group_name", name);
      if (overrides?.avatar) {
        form.append("group_avatar", overrides.avatar);
      }
      const res = await chatApi.updateGroup(conversation.id, form);
      setGroupName(res.data.group_name);
      setAvatarUrl(res.data.group_avatar_url);
      setMembers(res.data.participants);
      onUpdated(res.data);
      onRefreshList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update group.");
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await saveGroup({ avatar: file });
    if (avatarRef.current) avatarRef.current.value = "";
  };

  const handleRemoveMember = async (userId: number) => {
    if (!window.confirm("Remove this member from the group?")) return;

    setRemovingId(userId);
    setError("");
    try {
      const res = await chatApi.removeGroupMember(conversation.id, userId);
      setMembers(res.data.participants);
      onUpdated(res.data);
      onRefreshList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to remove member.");
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal group-info-panel" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Group info</h3>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="group-info-header">
          <div
            className={isAdmin ? "group-avatar-edit" : undefined}
            onClick={() => isAdmin && avatarRef.current?.click()}
          >
            <GroupAvatar name={groupName} imageUrl={avatarUrl} size={72} />
            {isAdmin && (
              <span className="group-avatar-camera">
                <Camera size={18} />
              </span>
            )}
          </div>
          {isAdmin && (
            <input
              ref={avatarRef}
              type="file"
              accept="image/*"
              hidden
              onChange={handleAvatarChange}
            />
          )}

          {isAdmin ? (
            <div className="form-group" style={{ marginTop: 16, textAlign: "left" }}>
              <label>Group name</label>
              <input
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                maxLength={100}
                disabled={saving}
              />
              <button
                type="button"
                className="btn-primary"
                style={{ marginTop: 12 }}
                disabled={saving || groupName.trim().length < 2}
                onClick={() => saveGroup()}
              >
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          ) : (
            <h2>{groupName}</h2>
          )}

          <p>{members.length} participants{isAdmin ? " · You are admin" : ""}</p>
        </div>

        <div className="group-members-list">
          <h4>Participants</h4>
          {members.map((member) => {
            const isSelf = member.id === currentUserId;
            const isGroupCreator = member.id === conversation.created_by
              || (conversation.created_by == null
                && member.id === Math.min(...members.map((m) => m.id)));
            return (
              <div key={member.id} className="user-result group-member-row">
                <Avatar user={member} size={44} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500 }}>
                    {getDisplayName(member)}
                    {isSelf && (
                      <span style={{ color: "var(--wa-text-secondary)", fontWeight: 400 }}> (You)</span>
                    )}
                    {isGroupCreator && (
                      <span className="admin-badge">Admin</span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--wa-text-secondary)" }}>
                    {member.is_online ? "online" : member.phone_number}
                  </div>
                </div>
                {isAdmin && !isSelf && (
                  <button
                    type="button"
                    className="icon-btn danger-btn"
                    title="Remove member"
                    disabled={removingId === member.id}
                    onClick={() => handleRemoveMember(member.id)}
                  >
                    <UserMinus size={18} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
