import React from 'react';
import {
  Users,
  Award,
  ShieldAlert,
  Network,
  Lock,
  ShieldCheck,
  Radio,
  Activity,
  Heart,
} from 'lucide-react';

interface TeamMember {
  name: string;
  role: string;
  initial: string;
}

const teamMembers: TeamMember[] = [
  { name: 'Krish Anand', role: 'Team Leader', initial: 'K' },
  { name: 'Abhinav Puri', role: 'Team Member', initial: 'A' },
  { name: 'Debojit Deb', role: 'Team Member', initial: 'D' },
  { name: 'Shreya Singh', role: 'Team Member', initial: 'S' },
];

const capabilities = [
  { icon: Network, label: 'P2P Multi-Hop Mesh Routing', color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
  { icon: Lock, label: 'ChaCha20-Poly1305 Encryption', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  { icon: ShieldCheck, label: 'Ed25519 Digital Signatures', color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20' },
  { icon: Radio, label: 'Zero-Infrastructure Blackout Mode', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
  { icon: Activity, label: 'Store-and-Forward Resilience', color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20' },
  { icon: ShieldAlert, label: 'Eavesdropping & Tamper Resistance', color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20' },
];

const techStack = [
  { label: 'React & Vite', desc: 'Tactical frontend UI with real-time state' },
  { label: 'FastAPI & Python', desc: 'High-performance asynchronous mesh backend' },
  { label: 'X25519 & ChaCha20-Poly1305', desc: 'Authenticated end-to-end encryption pipeline' },
  { label: 'Ed25519 Signatures', desc: 'Cryptographic identity verification' },
  { label: 'Ad-Hoc Mesh Routing', desc: 'Multi-hop store-and-forward packet propagation' },
  { label: 'Tailwind CSS & Lucide', desc: 'Glassmorphic tactical mission command theme' },
];

export const AboutUs: React.FC = () => {
  return (
    <div className="space-y-8 pb-12 animate-fade-in max-w-5xl">
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/70 pb-6">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl shrink-0">
            <Users className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-100 uppercase tracking-tight leading-tight">
              About Us
            </h1>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">
              Team InnovateX · SMIT · Tech Adrishta 26
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl self-start">
          <Award className="w-4 h-4 text-indigo-400" />
          <span className="text-indigo-400 text-xs font-black uppercase tracking-wider">
            Tech Adrishta 26
          </span>
        </div>
      </div>

      {/* ── Hero Card ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/60 px-6 py-8 sm:px-8">
        <div className="absolute inset-0 opacity-[0.06] bg-[radial-gradient(#6366f1_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none" />
        <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full bg-indigo-600/8 blur-[60px] pointer-events-none" />

        <div className="relative space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-indigo-300">
            <ShieldAlert className="h-3.5 w-3.5" />
            Zero-Infrastructure Emergency Mesh Network &amp; Cryptographic Pipeline
          </div>

          <p className="text-sm leading-7 text-slate-300">
            We are <span className="font-bold text-slate-100">Team InnovateX</span> from{' '}
            <span className="font-bold text-indigo-300">Sikkim Manipal Institute of Technology (SMIT)</span>,
            participating in <span className="font-bold text-slate-100">Tech Adrishta 26</span>. We are a team of
            passionate undergrad engineers building resilient, zero-trust emergency communication systems designed for
            extreme disaster environments.
          </p>

          <p className="text-sm leading-7 text-slate-400">
            <span className="font-bold text-slate-200">RESQ</span> addresses complete communication blackouts caused by
            earthquakes, floods, or severe infrastructure failures. By combining peer-to-peer ad-hoc multi-hop mesh routing
            with state-of-the-art cryptography (X25519, ChaCha20-Poly1305, and Ed25519 digital signatures), RESQ ensures
            that emergency distress signals, medic requests, and rescue coordinates reach their destination with
            guaranteed confidentiality, tamper resistance, and authenticity.
          </p>
        </div>
      </section>

      {/* ── Core Capabilities ────────────────────────────────────────────── */}
      <section className="space-y-4">
        <h2 className="text-xs font-black uppercase tracking-widest text-slate-500">Platform Capabilities</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {capabilities.map(({ icon: Icon, label, color, bg }) => (
            <div
              key={label}
              className="flex items-center gap-3 rounded-xl border border-slate-800/70 bg-slate-950/50 px-4 py-3"
            >
              <div className={`p-2 rounded-lg border shrink-0 ${bg}`}>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
              <span className="text-xs font-semibold text-slate-300 leading-tight">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Team Members ─────────────────────────────────────────────────── */}
      <section className="space-y-4">
        <h2 className="text-xs font-black uppercase tracking-widest text-slate-500">The Team</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {teamMembers.map(({ name, role, initial }, idx) => (
            <div
              key={name}
              className="flex items-center gap-4 rounded-xl border border-slate-800/70 bg-slate-950/50 px-4 py-4 transition-colors hover:border-indigo-500/30"
            >
              <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/25 flex items-center justify-center text-sm font-black text-indigo-300 shrink-0">
                {initial}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-slate-200 truncate">{name}</p>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mt-0.5">
                  {idx === 0 ? (
                    <span className="text-indigo-400 font-bold">{role}</span>
                  ) : (
                    role
                  )}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Tech Stack ───────────────────────────────────────────────────── */}
      <section className="space-y-4">
        <h2 className="text-xs font-black uppercase tracking-widest text-slate-500">Technology Stack</h2>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {techStack.map(({ label, desc }) => (
            <div
              key={label}
              className="flex items-start gap-3 rounded-xl border border-slate-800/70 bg-slate-950/50 px-4 py-3"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
              <div>
                <span className="text-xs font-black text-slate-200 uppercase tracking-wider">{label}</span>
                <p className="text-[11px] text-slate-500 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer Attribution ───────────────────────────────────────────── */}
      <div className="pt-6 border-t border-slate-800/60 text-center">
        <p className="text-xs text-slate-500 flex items-center justify-center gap-1.5">
          <span>RESQ</span> · Built with <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500 inline" /> for{' '}
          <strong className="text-slate-400">Tech Adrishta 26</strong> by{' '}
          <strong className="text-indigo-400">Team InnovateX, SMIT</strong>
        </p>
      </div>
    </div>
  );
};
