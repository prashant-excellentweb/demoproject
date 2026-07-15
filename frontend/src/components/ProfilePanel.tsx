import { useRef, useState } from "react";
import { ArrowLeft, Camera, LogOut, Trash2 } from "lucide-react";
import { authApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import Avatar from "./Avatar";

interface Props {
  onClose: () => void;
}

export default function ProfilePanel({ onClose }: Props) {
  const { user, updateUser, logout } = useAuth();
  const [name, setName] = useState(user?.display_name || "");
  const [about, setAbout] = useState(user?.about || "");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const avatarRef = useRef<HTMLInputElement>(null);

  const handleSave = async () => {
    setSaving(true);
    const form = new FormData();
    form.append("display_name", name);
    form.append("about", about);
    const file = avatarRef.current?.files?.[0];
    if (file) form.append("avatar", file);
    try {
      const res = await authApi.updateProfile(form);
      updateUser(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      "Delete your account permanently? Your phone number will be freed and you will be logged out."
    );
    if (!confirmed) return;
    const typed = window.prompt('Type DELETE to confirm account deletion:');
    if (typed !== "DELETE") return;
    setDeleting(true);
    try {
      await authApi.deleteAccount();
      logout();
      onClose();
    } catch (e) {
      console.error(e);
      alert("Failed to delete account. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="profile-panel" onClick={onClose}>
      <div className="profile-content" onClick={(e) => e.stopPropagation()}>
        <div className="profile-header">
          <button className="icon-btn" onClick={onClose} style={{ color: "white" }}>
            <ArrowLeft size={24} />
          </button>
          <h2>Profile</h2>
        </div>

        <div className="profile-avatar-section">
          <div onClick={() => avatarRef.current?.click()} style={{ cursor: "pointer", position: "relative", display: "inline-block" }}>
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" className="profile-avatar-large" />
            ) : (
              <Avatar user={user!} size={160} className="profile-avatar-large" />
            )}
            <div style={{
              position: "absolute", bottom: 8, right: 8,
              background: "var(--wa-teal-light)", borderRadius: "50%",
              width: 40, height: 40, display: "flex", alignItems: "center", justifyContent: "center", color: "white",
            }}>
              <Camera size={20} />
            </div>
          </div>
          <input ref={avatarRef} type="file" accept="image/*" hidden onChange={handleSave} />
          <p style={{ color: "var(--wa-text-secondary)", fontSize: 14 }}>{user?.phone_number}</p>
        </div>

        <div className="profile-form">
          <div className="form-group">
            <label>Display Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>
          <div className="form-group">
            <label>About</label>
            <textarea value={about} onChange={(e) => setAbout(e.target.value)} placeholder="About you" />
          </div>
          <button className="btn-primary" onClick={handleSave} disabled={saving || deleting} style={{ marginBottom: 16 }}>
            {saving ? "Saving..." : "Save Profile"}
          </button>
          <button
            className="btn-primary"
            onClick={() => { logout(); onClose(); }}
            disabled={deleting}
            style={{ background: "#ea0038", marginBottom: 16 }}
          >
            <LogOut size={18} style={{ display: "inline", marginRight: 8, verticalAlign: "middle" }} />
            Logout
          </button>
          <button
            className="btn-primary"
            onClick={handleDeleteAccount}
            disabled={deleting}
            style={{ background: "#7f1d1d" }}
          >
            <Trash2 size={18} style={{ display: "inline", marginRight: 8, verticalAlign: "middle" }} />
            {deleting ? "Deleting..." : "Delete Account"}
          </button>
        </div>
      </div>
    </div>
  );
}
