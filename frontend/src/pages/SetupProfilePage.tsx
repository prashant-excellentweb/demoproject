import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";

export default function SetupProfilePage() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = displayName.trim();
    if (name.length < 2) {
      setError("Display name must be at least 2 characters.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const form = new FormData();
      form.append("display_name", name);
      const res = await authApi.updateProfile(form);
      updateUser(res.data);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save profile.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <h1>Welcome to ChatApp</h1>
          <p>Choose a display name so friends can find you</p>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Display Name *</label>
            <input
              type="text"
              placeholder="Your name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={100}
              autoFocus
              required
            />
          </div>
          <p className="otp-hint" style={{ marginBottom: 16 }}>
            Registered as {user?.phone_number}. You can add a profile photo later from settings.
          </p>
          <button type="submit" className="btn-primary" disabled={loading || displayName.trim().length < 2}>
            {loading ? "Saving..." : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
