import { useRef, useState } from "react";
import { ArrowLeft, Camera, LogOut, Shield, Trash2 } from "lucide-react";
import { authApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import type { PrivacyVisibility } from "@/types";
import Avatar from "./Avatar";

interface Props {
  onClose: () => void;
}

const PRIVACY_OPTIONS: { value: PrivacyVisibility; label: string; hint: string }[] = [
  { value: "everyone", label: "Everyone", hint: "All ChatApp users" },
  { value: "contacts", label: "My contacts", hint: "People you chat with" },
  { value: "nobody", label: "Nobody", hint: "Only you" },
];

const PRIVACY_FIELDS: {
  key: "profile_photo_privacy" | "about_privacy" | "last_seen_privacy" | "status_privacy";
  label: string;
  description: string;
}[] = [
  {
    key: "profile_photo_privacy",
    label: "Profile photo",
    description: "Who can see your profile picture",
  },
  {
    key: "about_privacy",
    label: "About",
    description: "Who can see your about text",
  },
  {
    key: "last_seen_privacy",
    label: "Last seen & online",
    description: "Who can see when you were last online",
  },
  {
    key: "status_privacy",
    label: "Status",
    description: "Who can see your status updates",
  },
];

export default function ProfilePanel({ onClose }: Props) {
  const { user, updateUser, logout } = useAuth();
  const [name, setName] = useState(user?.display_name || "");
  const [about, setAbout] = useState(user?.about || "");
  const [privacy, setPrivacy] = useState({
    profile_photo_privacy: (user?.profile_photo_privacy || "everyone") as PrivacyVisibility,
    about_privacy: (user?.about_privacy || "everyone") as PrivacyVisibility,
    last_seen_privacy: (user?.last_seen_privacy || "everyone") as PrivacyVisibility,
    status_privacy: (user?.status_privacy || "contacts") as PrivacyVisibility,
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [privacySaved, setPrivacySaved] = useState(false);
  const avatarRef = useRef<HTMLInputElement>(null);

  const handleSave = async () => {
    setSaving(true);
    setPrivacySaved(false);
    const form = new FormData();
    form.append("display_name", name);
    form.append("about", about);
    form.append("profile_photo_privacy", privacy.profile_photo_privacy);
    form.append("about_privacy", privacy.about_privacy);
    form.append("last_seen_privacy", privacy.last_seen_privacy);
    form.append("status_privacy", privacy.status_privacy);
    const file = avatarRef.current?.files?.[0];
    if (file) form.append("avatar", file);
    try {
      const res = await authApi.updateProfile(form);
      updateUser(res.data);
      setPrivacy({
        profile_photo_privacy: res.data.profile_photo_privacy || privacy.profile_photo_privacy,
        about_privacy: res.data.about_privacy || privacy.about_privacy,
        last_seen_privacy: res.data.last_seen_privacy || privacy.last_seen_privacy,
        status_privacy: res.data.status_privacy || privacy.status_privacy,
      });
      setPrivacySaved(true);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handlePrivacyChange = (
    key: keyof typeof privacy,
    value: PrivacyVisibility
  ) => {
    setPrivacy((prev) => ({ ...prev, [key]: value }));
    setPrivacySaved(false);
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      "Delete your account permanently? Your phone number will be freed and you will be logged out."
    );
    if (!confirmed) return;
    const typed = window.prompt("Type DELETE to confirm account deletion:");
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
          <div
            onClick={() => avatarRef.current?.click()}
            style={{ cursor: "pointer", position: "relative", display: "inline-block" }}
          >
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" className="profile-avatar-large" />
            ) : (
              <Avatar user={user!} size={160} className="profile-avatar-large" />
            )}
            <div
              style={{
                position: "absolute",
                bottom: 8,
                right: 8,
                background: "var(--wa-teal-light)",
                borderRadius: "50%",
                width: 40,
                height: 40,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
              }}
            >
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

          <section className="privacy-section" aria-labelledby="privacy-heading">
            <div className="privacy-section-header">
              <Shield size={18} aria-hidden />
              <h3 id="privacy-heading">Privacy</h3>
            </div>
            <p className="privacy-section-intro">
              Control who can see your profile photo, about, last seen, and status.
            </p>
            {PRIVACY_FIELDS.map((field) => (
              <div key={field.key} className="privacy-field">
                <div className="privacy-field-labels">
                  <span className="privacy-field-title">{field.label}</span>
                  <span className="privacy-field-desc">{field.description}</span>
                </div>
                <div className="privacy-options" role="radiogroup" aria-label={field.label}>
                  {PRIVACY_OPTIONS.map((opt) => {
                    const selected = privacy[field.key] === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        className={`privacy-option${selected ? " selected" : ""}`}
                        aria-pressed={selected}
                        title={opt.hint}
                        onClick={() => handlePrivacyChange(field.key, opt.value)}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
            {privacySaved && (
              <p className="privacy-saved-hint" role="status">
                Privacy settings saved.
              </p>
            )}
          </section>

          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={saving || deleting}
            style={{ marginBottom: 16 }}
          >
            {saving ? "Saving..." : "Save Profile"}
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              logout();
              onClose();
            }}
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
