import { useState, type ReactElement } from "react";

const steps = [
  {
    title: "Finance labels are noisy",
    body: "The target is short-horizon SPY-relative outperformance. The benchmark treats weak signal and changing regimes as the point, not an inconvenience.",
  },
  {
    title: "Classical baselines are strong",
    body: "Logistic regression, RBF SVM, random forest, and XGBoost all use the same frozen dataset and walk-forward splits.",
  },
  {
    title: "QML is tested honestly",
    body: "The quantum kernel SVM is measured under exact statevectors, finite shots, and noisy shot-limited execution.",
  },
  {
    title: "qBraid checks portability",
    body: "The same kernel-estimation circuit is compiled through QASM2 roundtrip and Cirq paths, then judged by output probability preservation.",
  },
  {
    title: "The claim is a boundary map",
    body: "QML does not need to win everywhere. The result maps where it is useful, where it is competitive, and what it costs.",
  },
] as const;

export function JudgeTour(): ReactElement {
  const [index, setIndex] = useState(0);
  const step = steps[index];

  return (
    <section className="panel tour-panel" aria-labelledby="tour-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">90-second judge tour</p>
          <h2 id="tour-title">{step.title}</h2>
        </div>
        <p>
          Step {index + 1} of {steps.length}
        </p>
      </div>
      <p className="tour-copy">{step.body}</p>
      <div className="tour-progress" aria-label="Tour progress">
        {steps.map((tourStep, stepIndex) => (
          <button
            className={stepIndex === index ? "progress-dot active" : "progress-dot"}
            key={tourStep.title}
            type="button"
            onClick={() => setIndex(stepIndex)}
            aria-label={`Go to ${tourStep.title}`}
          />
        ))}
      </div>
      <div className="tour-actions">
        <button type="button" onClick={() => setIndex((current) => Math.max(0, current - 1))} disabled={index === 0}>
          Previous
        </button>
        <button
          type="button"
          onClick={() => setIndex((current) => Math.min(steps.length - 1, current + 1))}
          disabled={index === steps.length - 1}
        >
          Next
        </button>
      </div>
    </section>
  );
}
