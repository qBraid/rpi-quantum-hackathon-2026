import { CheckCircle2, XCircle } from "lucide-react";

import { api } from "../api";
import { EmptyState, LoadingState, PageHeader, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

function DetailRow({ label, value, available }: { label: string; value: string; available?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 py-3 last:border-0">
      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-mono font-medium text-foreground">{value}</span>
        {available !== undefined &&
          (available ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-red-500" />)}
      </div>
    </div>
  );
}

const providerLabels: Record<string, string> = {
  qbraid: "qBraid SDK",
  qiskit: "Qiskit",
  ibm_quantum: "IBM Quantum",
  local_simulators: "Local Simulators",
};

const providerDescriptions: Record<string, string> = {
  qbraid: "Cross-framework transpilation and compiler-aware benchmarking backbone.",
  qiskit: "Primary circuit framework for wildfire QAOA workloads and Aer simulator execution.",
  ibm_quantum: "Cloud hardware access used when the benchmark workflow can execute on IBM Runtime.",
  local_simulators: "Ideal and noisy Aer backends used for fallback and controlled benchmark comparisons.",
};

export function IntegrationsPage() {
  const { data, loading, error, reload } = useAsyncData(api.integrations, []);

  if (loading) return <LoadingState label="Loading integrations..." />;
  if (error || !data) {
    return (
      <EmptyState
        title="Integrations unavailable"
        description={error ?? "Could not load integration status."}
        action={
          <button onClick={() => void reload()} className="bg-primary px-6 py-2.5 text-[12px] font-bold uppercase tracking-wider text-primary-foreground">
            Retry
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Integrations"
        title="Execution and compiler connectivity"
        description="Live status for qBraid, Qiskit, IBM Quantum, and simulator backends. Missing credentials produce transparent degraded mode; the wildfire planning workflow stays usable and never fabricates availability."
      />

      <SectionPanel>
        <div className="flex flex-wrap gap-3">
          <StatusPill label={data.qbraid_ready ? "qBraid ready" : "qBraid missing"} tone={data.qbraid_ready ? "good" : "warn"} />
          <StatusPill label={data.hardware_available ? "IBM hardware available" : "Simulator only"} tone={data.hardware_available ? "good" : "warn"} />
          <StatusPill label={data.simulator_only ? "Running in simulator-only mode" : "Full execution mode"} tone={data.simulator_only ? "warn" : "good"} />
        </div>
      </SectionPanel>

      <div className="grid gap-6 md:grid-cols-2">
        {data.providers.map((provider) => {
          const details = provider.details ?? {};
          return (
            <SectionPanel key={provider.provider} title={providerLabels[provider.provider] ?? provider.provider} subtitle={providerDescriptions[provider.provider] ?? ""}>
              <div className="mb-4 flex items-center gap-2">
                <StatusPill label={provider.available ? "Available" : "Unavailable"} tone={provider.available ? "good" : "warn"} />
                <StatusPill label={provider.mode} tone={provider.mode === "ready" || provider.mode === "hardware_ready" ? "good" : "neutral"} />
              </div>

              <div className="border border-border bg-card px-4 py-2">
                {provider.provider === "qbraid" && (
                  <>
                    <DetailRow label="SDK installed" value={details.installed ? "Yes" : "No"} available={details.installed} />
                    {details.version && <DetailRow label="Version" value={details.version} />}
                    <DetailRow label="API key configured" value={details.api_key_configured ? "Yes" : "No"} available={details.api_key_configured} />
                    <DetailRow label="Transpiler available" value={details.transpiler_available ? "Yes" : "No"} available={details.transpiler_available} />
                  </>
                )}
                {provider.provider === "qiskit" && (
                  <>
                    <DetailRow label="SDK installed" value={details.sdk_installed ? "Yes" : "No"} available={details.sdk_installed} />
                    {details.version && <DetailRow label="Version" value={details.version} />}
                    <DetailRow label="Aer installed" value={details.aer_installed ? "Yes" : "No"} available={details.aer_installed} />
                    {details.aer_version && <DetailRow label="Aer version" value={details.aer_version} />}
                    <DetailRow label="QASM3 import" value={details.qasm3_import_installed ? "Yes" : "No"} available={details.qasm3_import_installed} />
                    {details.qasm3_import_version && <DetailRow label="QASM3 import version" value={details.qasm3_import_version} />}
                  </>
                )}
                {provider.provider === "ibm_quantum" && (
                  <>
                    <DetailRow label="Token configured" value={details.token_configured ? "Yes" : "No"} available={details.token_configured} />
                    <DetailRow label="Connected" value={details.connected ? "Yes" : "No"} available={details.connected} />
                    <DetailRow label="Channel" value={details.channel ?? "-"} />
                    <DetailRow label="Instance" value={details.instance ?? "-"} />
                    {details.runtime_version && <DetailRow label="Runtime version" value={details.runtime_version} />}
                    {details.total_backends != null && <DetailRow label="Available backends" value={String(details.total_backends)} />}
                    {details.reason && !details.connected && <p className="mt-2 text-[11px] leading-4 text-amber-700">{details.reason}</p>}
                  </>
                )}
                {provider.provider === "local_simulators" && (
                  <>
                    <DetailRow label="Aer installed" value={details.aer_installed ? "Yes" : "No"} available={details.aer_installed} />
                    {details.aer_version && <DetailRow label="Aer version" value={details.aer_version} />}
                    <DetailRow label="Ideal simulator" value={details.ideal_simulator ? "Available" : "Unavailable"} available={details.ideal_simulator} />
                    <DetailRow label="Noisy simulator" value={details.noisy_simulator ? "Available" : "Unavailable"} available={details.noisy_simulator} />
                    <DetailRow label="Noise model" value={details.noise_model ?? "-"} />
                    {details.methods && <DetailRow label="Methods" value={details.methods.join(", ")} />}
                  </>
                )}
              </div>
            </SectionPanel>
          );
        })}
      </div>
    </div>
  );
}
