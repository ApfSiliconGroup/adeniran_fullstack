"use client";

import { useState } from "react";
import { ArrowLeft, ArrowRight, Eye, HeartPulse, ShieldCheck } from "lucide-react";
import { api, ApiRequestError } from "../lib/api";

type SignupProps = { onBack: () => void; onComplete: (token: string) => void };

export default function Signup({ onBack, onComplete }: SignupProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Your passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api.registerPatient(username.trim(), password);
      const session = await api.login(username.trim(), password);
      onComplete(session.access_token);
    } catch (caught) {
      setError(caught instanceof ApiRequestError ? caught.message : "We could not create your account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page auth-enter">
      <section className="login-art signup-art">
        <div className="brand"><div className="brand-mark"><HeartPulse size={19} /></div><div>Adeniran Street Clinic<small>Care, coordinated</small></div></div>
        <div className="art-copy"><div className="eyebrow" style={{ color: "#a9dfc8" }}>A gentler first step</div><h1>Make room for better care.</h1><p>Create a secure patient account and keep your clinic appointments close at hand.</p></div>
        <div className="care-note"><ShieldCheck size={18} /> Patient accounts are protected by the clinic</div>
      </section>
      <section className="login-panel"><form className="login-card auth-card" onSubmit={submit}>
        <button type="button" className="back-link" onClick={onBack}><ArrowLeft size={15} /> Back to sign in</button>
        <div className="eyebrow">Patient registration</div><h2>Create your care space</h2><p className="subtle">Choose a username and password for your patient account.</p>
        <div className="form-stack">
          <div className="field"><label htmlFor="signup-username">Username</label><input id="signup-username" className="input" minLength={3} autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /><span className="field-help">At least 3 characters</span></div>
          <div className="field"><label htmlFor="signup-password">Password</label><div className="password-wrap"><input id="signup-password" className="input" type={showPassword ? "text" : "password"} minLength={6} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required /><button className="icon-button" type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}><Eye size={17} /></button></div><span className="field-help">At least 6 characters</span></div>
          <div className="field"><label htmlFor="signup-confirm">Confirm password</label><input id="signup-confirm" className="input" type={showPassword ? "text" : "password"} autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></div>
          {error && <div className="error-box" role="alert">{error}</div>}
          <button className="primary-button button-wide" disabled={busy}>{busy ? "Creating your account..." : "Create patient account"}<ArrowRight size={17} /></button>
        </div>
        <div className="demo-hint">By creating an account, you are joining Adeniran Street Clinic as a patient. Doctor and receptionist accounts are provisioned by the clinic.</div>
      </form></section>
    </main>
  );
}
