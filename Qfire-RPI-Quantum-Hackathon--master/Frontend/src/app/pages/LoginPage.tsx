import { useRef } from "react";
import type { SVGProps } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight, Atom } from "lucide-react";

function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full opacity-80" />;
}

function Shield(props: SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
    </svg>
  );
}

export function LoginPage() {
  const navigate = useNavigate();

  return (
    <div className="grid min-h-screen bg-[linear-gradient(180deg,#eef3f7_0%,#f8fafc_100%)] lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-[linear-gradient(160deg,#101b31_0%,#13233d_45%,#0f1729_100%)] p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <AnimatedBackground />
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10">
            <Atom className="h-5 w-5 text-qp-cyan" />
          </div>
          <div>
            <p className="text-[15px] font-semibold">QuantumProj</p>
            <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Enterprise workflow</p>
          </div>
        </div>

        <div className="relative z-10 max-w-lg">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-qp-cyan">Launch access</p>
          <h1 className="mt-4 text-[38px] font-semibold tracking-[-0.05em]">Move from spatial setup to benchmark-backed intervention planning in one product flow.</h1>
          <p className="mt-5 text-[15px] leading-8 text-white/65">
            Sign in to open the wildfire workspace, run risk and forecast jobs, compare optimization modes, and generate reports from persisted backend runs.
          </p>
        </div>

        <div className="relative z-10 rounded-[28px] border border-white/10 bg-white/5 p-6">
          <p className="text-[12px] leading-6 text-white/70">
            The MVP uses a lightweight auth shell only. Operational integrity comes from real backend APIs, explicit simulator-only labeling, and qBraid-aware benchmark capability detection.
          </p>
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-md rounded-[28px] border border-white/70 bg-white/90 p-8 shadow-[0_30px_100px_-55px_rgba(15,23,41,0.45)]">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-qp-navy text-white">
              <Atom className="h-5 w-5 text-qp-cyan" />
            </div>
            <p className="text-[15px] font-semibold">QuantumProj</p>
          </div>

          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-qp-cyan">Sign in</p>
          <h2 className="mt-3 text-[30px] font-semibold tracking-[-0.04em] text-foreground">Access the workspace</h2>
          <p className="mt-3 text-[13px] leading-6 text-muted-foreground">
            This MVP ships a launch-ready auth surface. Submit the form to enter the platform shell.
          </p>

          <div className="mt-8 space-y-3">
            <button className="flex w-full items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 py-3 text-[13px] font-medium text-foreground">
              <Shield className="h-4 w-4" />
              Continue with SSO
            </button>
            <button
              onClick={() => navigate("/app")}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-qp-navy px-4 py-3 text-[13px] font-medium text-white"
            >
              Open workspace <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-6 rounded-2xl border border-border bg-slate-50 p-4 text-[12px] leading-5 text-muted-foreground">
            Prefer a marketing overview first? <Link to="/" className="font-medium text-qp-cyan">Return to homepage</Link>.
          </div>
        </div>
      </section>
    </div>
  );
}
