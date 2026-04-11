import { Link } from "react-router";
import { ArrowRight, Atom, Cpu, Flame, Layers, ShieldCheck, Target, TrendingUp } from "lucide-react";

export function HomePage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-background/90 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center bg-foreground text-background">
              <Atom className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-[15px] font-bold tracking-tight text-foreground">QuantumProj</p>
              <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Wildfire resilience</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <Link to="/login" className="text-[12px] font-bold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground">
              Sign in
            </Link>
            <Link to="/app" className="bg-foreground px-5 py-2.5 text-[12px] font-bold uppercase tracking-wider text-background transition-transform hover:-translate-y-0.5">
              View platform
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="px-6 py-20">
          <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div className="max-w-xl">
              <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-primary">For wildfire planning teams</p>
              <h1 className="mt-5 text-[48px] font-bold tracking-[-0.02em] leading-[1.05] text-foreground">
                Plan wildfire interventions with risk maps, forecasts, and benchmark-backed quantum evidence.
              </h1>
              <p className="mt-6 text-[16px] leading-relaxed text-muted-foreground">
                QuantumProj helps resilience analysts, land managers, and research teams work through one clear flow on a 10x10 hillside grid: define the fire-prone terrain, score local risk, simulate spread, place limited fire-resistant interventions, and verify that the quantum optimization workflow still behaves well after qBraid-centered compilation.
              </p>
              <div className="mt-10 flex flex-wrap gap-4">
                <Link to="/app" className="inline-flex items-center justify-center gap-2 bg-primary px-8 py-4 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-transform hover:-translate-y-0.5">
                  Open platform <ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/login" className="inline-flex items-center justify-center border-2 border-foreground bg-transparent px-8 py-4 text-[13px] font-bold uppercase tracking-wider text-foreground transition-colors hover:bg-foreground hover:text-background">
                  Request demo
                </Link>
              </div>
            </div>

            <div className="relative overflow-hidden border border-border bg-foreground p-8">
              <div className="grid grid-cols-10 gap-1 opacity-60">
                {Array.from({ length: 100 }).map((_, index) => (
                  <div
                    key={index}
                    className={`aspect-square ${
                      index === 45 || index === 46 || index === 55
                        ? "bg-[#ff4e3e]"
                        : index % 9 === 0
                        ? "bg-[#00f3ff]/40"
                        : index % 5 === 0
                        ? "bg-amber-300/40"
                        : "bg-background/10"
                    }`}
                  />
                ))}
              </div>
              <div className="absolute inset-x-8 bottom-8 grid gap-4 md:grid-cols-3">
                {[
                  { label: "Risk map", value: "Classical, quantum, and hybrid scoring on one hillside" },
                  { label: "Intervention plan", value: "Full-grid baseline plus reduced quantum study" },
                  { label: "Benchmark integrity", value: "qBraid-centered compilation across simulators and IBM" },
                ].map((item) => (
                  <div key={item.label} className="border border-background/20 bg-background/5 p-4 text-background backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">{item.label}</p>
                    <p className="mt-2 text-[12px] leading-tight font-medium text-background/90">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="px-6 pb-20">
          <div className="mx-auto grid max-w-7xl gap-6 md:grid-cols-4">
            {[
              { icon: Layers, title: "Build the hillside scenario", text: "Edit a 10x10 wildfire grid, set the intervention budget, and save a versioned planning case." },
              { icon: TrendingUp, title: "Forecast spread pressure", text: "Project fire propagation under explicit dryness, wind, and sensitivity assumptions." },
              { icon: Target, title: "Place limited interventions", text: "Recommend where scarce fire-resistant actions should go to break likely spread paths." },
              { icon: Cpu, title: "Validate benchmark integrity", text: "Use qBraid-centered benchmarking to test whether compiled quantum workloads still preserve useful optimization behavior." },
            ].map((item) => (
              <div key={item.title} className="border border-border bg-card p-6 border-t-4 border-t-primary hover:-translate-y-1 transition-transform">
                <item.icon className="h-6 w-6 text-primary" />
                <h2 className="mt-5 text-[16px] font-bold tracking-tight text-foreground">{item.title}</h2>
                <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">{item.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="px-6 pb-20">
          <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="border border-border bg-card p-8 border-l-4 border-l-primary">
              <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-primary">Why qBraid is central</p>
              <h2 className="mt-4 text-[26px] font-semibold tracking-[-0.03em] leading-tight text-foreground">The benchmark layer exists to answer one practical question: can this quantum recommendation be trusted after compilation?</h2>
              <p className="mt-5 text-[15px] leading-relaxed text-muted-foreground">
                Quantum recommendations are not useful if they only look good before compilation. QuantumProj keeps qBraid in the center of the workflow so teams can compare strategy quality against compiled resource cost, then see whether the reduced wildfire intervention workload still behaves well on simulators and available IBM hardware.
              </p>
            </div>
            <div className="border border-border bg-foreground p-8 text-background">
              <div className="grid gap-4 md:grid-cols-2">
                {[
                  "Reduced wildfire-intervention QAOA workload tied directly to the planning module",
                  "Two qBraid compilation strategies compared side by side",
                  "Ideal simulator, noisy simulator, and IBM execution when available",
                  "Approximation ratio, success probability, depth, width, and 2Q gate tracking",
                ].map((line) => (
                  <div key={line} className="border border-background/20 bg-background/5 p-5 text-[13px] leading-relaxed text-background/90">
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-border bg-white/80 px-6 py-10">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-8 text-[13px] text-muted-foreground">
            <span className="inline-flex items-center gap-2">
              <Flame className="h-4 w-4 text-qp-amber" /> Wildfire resilience planning
            </span>
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" /> Honest degraded mode when hardware is unavailable
            </span>
            <span className="inline-flex items-center gap-2">
              <Cpu className="h-4 w-4 text-qp-cyan" /> Compiler-aware benchmark workflow
            </span>
          </div>
        </section>
      </main>
    </div>
  );
}
