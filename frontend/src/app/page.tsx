"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  HeartPulse,
  LogOut,
  Menu,
  Plus,
  ShieldCheck,
  Stethoscope,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { format, isToday, parseISO } from "date-fns";
import { useLogin, useLogout, useSession, useSignup, useSyncProfile } from "@/lib/hooks/use-session";
import {
  useBookAppointment,
  useCancelPatientAppointment,
  useDoctorAppointments,
  useCompleteAppointment,
  useFreeSlots,
  usePatientAppointments,
  usePatientDoctors,
} from "@/lib/hooks/use-appointments";
import { useDiary, useDiaryOverview, useCancelAnyAppointment } from "@/lib/hooks/use-reception";
import { useMyNotes } from "@/lib/hooks/use-notes";
import { useClinicStats } from "@/lib/hooks/use-clinic";
import { useToast } from "@/lib/hooks/use-toast";
import type { Appointment, DoctorPublic, UserRole } from "@/types/api";

const today = format(new Date(), "yyyy-MM-dd");

function Brand({ inverse = false }: { inverse?: boolean }) {
  return <div className={`flex items-center gap-3 ${inverse ? "text-white" : "text-base-content"}`}><span className="grid size-10 place-items-center rounded-2xl bg-primary text-primary-content shadow-sm"><HeartPulse size={21} /></span><span><strong className="block font-extrabold tracking-tight">Adeniran Street Clinic</strong><small className={inverse ? "text-white/65" : "text-base-content/55"}>Care, coordinated</small></span></div>;
}

function AuthScreen() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [confirm, setConfirm] = useState("");
  const login = useLogin();
  const signup = useSignup();
  const toast = useToast();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "signup") {
      if (password !== confirm) return toast.error("Passwords do not match", "Please check both password fields.");
      signup.mutate({ username, password, full_name: fullName }, { onError: (error) => toast.fromError(error, "Account creation failed.") });
    } else login.mutate({ username, password }, { onError: (error) => toast.fromError(error, "Sign in failed.") });
  }

  const busy = login.isPending || signup.isPending;
  return <main className="min-h-dvh bg-base-200 lg:grid lg:grid-cols-[1.05fr_.95fr]">
    <section className="relative hidden overflow-hidden bg-neutral px-8 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-16">
      <div className="absolute -right-40 -bottom-40 size-128 rounded-full border border-white/10 shadow-[0_0_0_40px_rgba(255,255,255,.04),0_0_0_80px_rgba(255,255,255,.03)]" />
      <Brand inverse />
      <div className="relative max-w-xl pb-10"><p className="mb-5 text-xs font-bold uppercase tracking-[.18em] text-primary-content/70">Your care, in one place</p><h1 className="max-w-lg text-6xl font-extrabold leading-[.98] tracking-[-.06em] xl:text-7xl">Health support that feels human.</h1><p className="mt-7 max-w-md text-lg leading-relaxed text-white/65">Appointments, trusted clinicians, and the details that keep your care moving forward.</p></div>
      <div className="flex items-center gap-3 text-sm text-white/70"><ShieldCheck size={18} /> Private, secure clinic access</div>
    </section>
    <section className="flex min-h-dvh items-center justify-center px-5 py-10 sm:px-10"><div className="w-full max-w-md animate-[fade-up_.65s_ease-out] lg:max-w-lg"><div className="mb-12 lg:hidden"><Brand /></div><div className="mb-8"><p className="text-xs font-bold uppercase tracking-[.18em] text-primary">{mode === "login" ? "Welcome back" : "Patient registration"}</p><h2 className="mt-3 text-4xl font-extrabold tracking-tighter">{mode === "login" ? "Sign in to your care space" : "Create your care space"}</h2><p className="mt-3 leading-relaxed text-base-content/60">{mode === "login" ? "Use your clinic username and password to continue." : "Create a patient account and keep your clinic appointments close at hand."}</p></div><form onSubmit={submit} className="space-y-4">
      {mode === "signup" && <label className="form-control"><span className="label-text mb-2 font-semibold">Full name</span><input className="input input-bordered w-full" placeholder="Your name" value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>}
      <label className="form-control"><span className="label-text mb-2 font-semibold">Username</span><input className="input input-bordered w-full" autoComplete="username" minLength={3} required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
      <label className="form-control"><span className="label-text mb-2 font-semibold">Password</span><input className="input input-bordered w-full" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={6} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {mode === "signup" && <label className="form-control"><span className="label-text mb-2 font-semibold">Confirm password</span><input className="input input-bordered w-full" type="password" autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)} /></label>}
      <button className="btn btn-primary btn-lg mt-3 w-full shadow-lg shadow-primary/20" disabled={busy}>{busy ? <span className="loading loading-spinner" /> : mode === "login" ? "Continue to clinic" : "Create patient account"}<ArrowRight size={18} /></button>
    </form><div className="divider my-8 text-xs uppercase tracking-wider opacity-50">or</div><button className="btn btn-ghost w-full" onClick={() => setMode(mode === "login" ? "signup" : "login")}>{mode === "login" ? "New to the clinic? Create a patient account" : "Already have an account? Sign in"}</button></div></section>
  </main>;
}

function StatCard({ icon: Icon, label, value }: { icon: typeof CalendarDays; label: string; value: string | number }) { return <div className="stat border border-base-300 bg-base-100 shadow-sm"><div className="stat-figure text-primary"><Icon size={24} /></div><div className="stat-title">{label}</div><div className="stat-value text-3xl">{value}</div></div>; }

function AppointmentList({ appointments, role, onAction }: { appointments: Appointment[]; role: UserRole; onAction?: (appointment: Appointment) => void }) {
  if (!appointments.length) return <div className="rounded-box border border-dashed border-base-300 p-10 text-center text-base-content/55"><CalendarDays className="mx-auto mb-3 opacity-50" size={28} /><p>No appointments to show yet.</p></div>;
  return <div className="space-y-3">{appointments.map((appointment) => <div key={appointment.id} className="flex flex-col gap-4 rounded-box border border-base-300 bg-base-100 p-4 transition hover:border-primary/40 hover:shadow-sm sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary/10 text-primary"><strong className="text-lg">{format(parseISO(appointment.appointment_date), "d")}</strong><small>{format(parseISO(appointment.appointment_date), "MMM")}</small></div><div><strong className="block">{role === "patient" ? appointment.doctor_name : appointment.patient_name}</strong><span className="text-sm text-base-content/55">{appointment.doctor_speciality} · {appointment.appointment_time.slice(0, 5)}</span></div></div><div className="flex items-center gap-2"><span className={`badge ${appointment.status === "completed" ? "badge-info" : appointment.status === "cancelled" ? "badge-error" : "badge-success"}`}>{appointment.status}</span>{onAction && appointment.status === "booked" && <button className={role === "doctor" ? "btn btn-sm btn-primary" : "btn btn-sm btn-ghost text-error"} onClick={() => onAction(appointment)}>{role === "doctor" ? "Complete" : "Cancel"}</button>}</div></div>)}</div>;
}

function PatientWorkspace() {
  const [bookingOpen, setBookingOpen] = useState(false); const [doctorId, setDoctorId] = useState<number | null>(null); const [date, setDate] = useState(today); const [time, setTime] = useState("");
  const appointments = usePatientAppointments(); const doctors = usePatientDoctors(); const slots = useFreeSlots(doctorId, date); const book = useBookAppointment(); const cancel = useCancelPatientAppointment(); const notes = useMyNotes(); const toast = useToast();
  const next = appointments.data?.filter((item) => item.status === "booked") ?? [];
  function submit(event: FormEvent) { event.preventDefault(); if (!doctorId || !time) return; book.mutate({ doctor_id: doctorId, appointment_date: date, appointment_time: time }, { onSuccess: () => { setBookingOpen(false); setTime(""); toast.success("Appointment booked", "Your clinic slot is confirmed."); }, onError: (error) => toast.fromError(error, "That slot is no longer available.") }); }
  return <WorkspaceFrame title="Your care overview" subtitle="A clear view of what is next in your care."><div className="stats mb-6 w-full border border-base-300 bg-base-100 shadow-sm"><StatCard icon={CalendarDays} label="Upcoming appointments" value={next.length} /><StatCard icon={Stethoscope} label="Care team available" value={doctors.data?.length ?? 0} /><StatCard icon={ShieldCheck} label="Workspace" value="Secure" /></div><div className="grid gap-6 xl:grid-cols-[1.4fr_.8fr]"><section className="card border border-base-300 bg-base-100 shadow-sm"><div className="card-body"><div className="mb-4 flex items-start justify-between gap-4"><div><h2 className="card-title">Your appointments</h2><p className="text-sm text-base-content/55">Keep track of upcoming care.</p></div><button className="btn btn-primary btn-sm" onClick={() => setBookingOpen(true)}><Plus size={16} /> Book appointment</button></div><AppointmentList appointments={appointments.data ?? []} role="patient" onAction={(item) => cancel.mutate(item.id, { onSuccess: () => toast.success("Appointment cancelled"), onError: (error) => toast.fromError(error) })} /></div></section><section className="card border border-base-300 bg-base-100 shadow-sm"><div className="card-body"><h2 className="card-title">Your care team</h2><p className="mb-4 text-sm text-base-content/55">Clinicians available to book.</p><div className="space-y-3">{(doctors.data ?? []).slice(0, 4).map((doctor) => <div className="flex items-center gap-3" key={doctor.id}><div className="grid size-10 place-items-center rounded-xl bg-accent/20 font-bold text-accent-content">{doctor.name.split(" ").map((part) => part[0]).join("").slice(0, 2)}</div><div><strong className="block text-sm">{doctor.name}</strong><span className="text-xs text-base-content/55">{doctor.speciality}</span></div></div>)}</div><div className="divider" /><p className="text-sm text-base-content/55">{notes.data?.length ?? 0} consultation notes available in your record.</p></div></section></div>{bookingOpen && <dialog open className="modal modal-open"><div className="modal-box"><button className="btn btn-ghost btn-sm btn-circle absolute right-3 top-3" onClick={() => setBookingOpen(false)}><X size={17} /></button><h3 className="text-xl font-bold">Book an appointment</h3><p className="mt-1 text-sm text-base-content/55">Choose a clinician, date, and live slot.</p><form onSubmit={submit} className="mt-6 space-y-4"><label className="form-control"><span className="label-text mb-2 font-semibold">Doctor</span><select className="select select-bordered" required value={doctorId ?? ""} onChange={(event) => setDoctorId(Number(event.target.value) || null)}><option value="">Choose a doctor</option>{(doctors.data ?? []).map((doctor) => <option key={doctor.id} value={doctor.id}>{doctor.name} · {doctor.speciality}</option>)}</select></label><label className="form-control"><span className="label-text mb-2 font-semibold">Date</span><input className="input input-bordered" type="date" min={today} value={date} onChange={(event) => setDate(event.target.value)} required /></label><label className="form-control"><span className="label-text mb-2 font-semibold">Available time</span><select className="select select-bordered" value={time} onChange={(event) => setTime(event.target.value)} disabled={!doctorId} required><option value="">{slots.isLoading ? "Loading slots..." : "Choose a time"}</option>{(slots.data ?? []).map((slot) => <option key={slot} value={slot}>{slot.slice(0, 5)}</option>)}</select></label><button className="btn btn-primary w-full" disabled={book.isPending}>{book.isPending ? <span className="loading loading-spinner" /> : "Confirm appointment"}</button></form></div><div className="modal-backdrop" onClick={() => setBookingOpen(false)} /></dialog>}</WorkspaceFrame>;
}

function DoctorWorkspace() {
  const appointments = useDoctorAppointments(today);
  const complete = useCompleteAppointment();
  const toast = useToast();
  return <WorkspaceFrame title="Your clinical day" subtitle="Only your assigned appointments can be completed or documented."><section className="card border border-base-300 bg-base-100 shadow-sm"><div className="card-body"><h2 className="card-title">Today's appointments</h2><AppointmentList appointments={appointments.data ?? []} role="doctor" onAction={(item) => { const note = window.prompt("Write the consultation note:"); if (note?.trim()) complete.mutate({ id: item.id, note }, { onSuccess: () => toast.success("Consultation filed"), onError: (error) => toast.fromError(error) }); }} /></div></section></WorkspaceFrame>;
}

function ReceptionWorkspace() {
  const [date, setDate] = useState(today);
  const diary = useDiary(date);
  const overview = useDiaryOverview(date);
  const cancel = useCancelAnyAppointment();
  const toast = useToast();
  return <WorkspaceFrame title="Clinic operations" subtitle="Keep the front desk moving with a clear diary."><div className="mb-6 flex justify-end"><input className="input input-bordered input-sm" type="date" value={date} onChange={(event) => setDate(event.target.value)} /></div><div className="stats mb-6 w-full border border-base-300 bg-base-100 shadow-sm"><StatCard icon={CalendarDays} label="Appointments" value={overview.data?.total ?? 0} /><StatCard icon={Activity} label="Utilisation" value={`${overview.data?.utilisation ?? 0}%`} /><StatCard icon={Users} label="Doctors on duty" value={overview.data?.doctors_on_duty ?? 0} /></div><section className="card border border-base-300 bg-base-100 shadow-sm"><div className="card-body"><h2 className="card-title mb-4">Clinic diary</h2><AppointmentList appointments={diary.data ?? []} role="receptionist" onAction={(item) => cancel.mutate(item.id, { onSuccess: () => toast.success("Appointment cancelled"), onError: (error) => toast.fromError(error) })} /></div></section></WorkspaceFrame>;
}

function WorkspaceFrame({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  const session = useSession();
  const logout = useLogout();
  return <div className="min-h-dvh bg-base-200"><aside className="fixed inset-y-0 left-0 z-20 hidden w-72 flex-col border-r border-base-300 bg-base-100 p-6 lg:flex"><Brand /><div className="mt-auto"><strong className="block text-sm">{session.displayName}</strong><span className="text-xs capitalize text-base-content/50">{session.role}</span><button className="btn btn-ghost btn-sm mt-5 w-full justify-start" onClick={logout}><LogOut size={16} /> Sign out</button></div></aside><header className="border-b border-base-300 bg-base-100 px-5 py-4 lg:ml-72 lg:px-10"><div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.16em] text-primary">{session.role} workspace</p><h1 className="mt-1 text-2xl font-extrabold tracking-tight">{title}</h1></div><span className="hidden text-sm text-base-content/55 sm:block">{format(new Date(), "EEE, MMM d, yyyy")}</span></div></header><main id="main" className="px-5 py-8 lg:ml-72 lg:px-10"><p className="mb-6 text-base-content/60">{subtitle}</p>{children}</main></div>;
}

function App() {
  const session = useSession();
  useSyncProfile();
  useEffect(() => { document.title = session.isAuthenticated ? `${session.displayName} · Adeniran Street Clinic` : "Adeniran Street Clinic"; }, [session.displayName, session.isAuthenticated]);
  if (!session.hydrated) return <AuthScreen />;
  if (!session.isAuthenticated) return <AuthScreen />;
  if (session.role === "doctor") return <DoctorWorkspace />;
  if (session.role === "receptionist") return <ReceptionWorkspace />;
  return <PatientWorkspace />;
}

export default function Page() { return <App />; }
