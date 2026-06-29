import { useState } from "react";
import { authApi } from "@/api/client";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.sendOtp(phone);
      setStep("otp");
    } catch {
      setError("Failed to send OTP. Check your phone number.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.verifyOtp(phone, otp);
      login(res.data.access, res.data.refresh, res.data.user);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Invalid OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <h1>ChatApp</h1>
          <p>Connect with friends and family</p>
        </div>

        {error && <div className="error-msg">{error}</div>}

        {step === "phone" ? (
          <form onSubmit={handleSendOtp}>
            <div className="form-group">
              <label>Phone Number</label>
              <input
                type="tel"
                placeholder="+1 234 567 8900"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Sending..." : "Send OTP"}
            </button>
            <p className="otp-hint">
              We'll send a verification code via SMS. In development mode, check the server console for the OTP.
            </p>
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp}>
            <div className="form-group">
              <label>Verification Code</label>
              <input
                type="text"
                placeholder="6-digit code"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading || otp.length !== 6}>
              {loading ? "Verifying..." : "Verify & Login"}
            </button>
            <p className="otp-hint">
              Code sent to {phone}.{" "}
              <button type="button" onClick={() => { setStep("phone"); setOtp(""); }} style={{ color: "var(--wa-teal-light)", fontWeight: 600 }}>
                Change number
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
