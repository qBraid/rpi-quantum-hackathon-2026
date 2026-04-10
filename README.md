# qBraid Challenge: Compiler-Aware Quantum Benchmarking

## Overview
Build a **portable quantum algorithm workflow** in **Python** using the **qBraid SDK** and a framework it can transpile. Show that the algorithm remains performant after compilation to a constrained execution target.

This challenge is about more than simply transpiling a circuit. You should study how **compilation choices** affect both:

- **algorithmic performance**, and
- **compiled resource cost**

Your goal is to identify which compilation strategy best preserves useful algorithm behavior under realistic execution constraints.

---

## Theme
**Compiler-aware benchmarking**

Submissions should answer a technical question:

> How well does a quantum algorithm survive compilation across frameworks and execution targets?

---

## Programming Language
All submissions must be implemented in:

- **Python**

---

## Core Requirement
Each team must build a workflow around a **quantum algorithm**, not just a circuit primitive.

A valid submission must:

1. implement a nontrivial quantum algorithm in Python
2. begin from at least one **framework-level source representation** such as cirq, braket, qiskit.
3. use **qBraid** to compile or transpile the workload
4. compare at least **two qBraid compilation strategies**
5. run the compiled workload on at least **two execution environments**
6. evaluate the tradeoff between:
   - **output quality**
   - **compiled resource cost**

---

## What Counts as a Workload
The workload should be an **algorithm**, not just a simple state-preparation demo.

### Good examples
- QAOA for MaxCut on a small graph
- Quantum Fourier Transform-based routine
- Hamiltonian simulation of a small spin model
- Variational observable estimation
- Bernstein-Vazirani or Deutsch-Jozsa, if extended into a meaningful benchmark study

### _Great_ example
- Cutting edge quantum algorithms with few tutorials and your own personal twist / optimization

### Not sufficient by itself
- Bell-state generation
- GHZ-only preparation
- “hello world” entanglement demos
- a single circuit with no algorithmic objective
- copying qbraid-algorithms and qbraid-lab-demo tutorials verbatim

---

## Required qBraid Usage
Your submission is only eligible if qBraid is central to the workflow.

Examples of valid qBraid usage include:
- `qbraid.transpile(...)`
- `ConversionGraph`
- `ConversionScheme`
- qBraid-based framework conversion
- qBraid-based target preparation or execution workflow

A submission that only uses native framework transpilation without meaningful qBraid usage is not eligible.

---

## Required Comparison
You must compare at least **two qBraid compilation strategies**.

Examples:
- default transpilation vs constrained path depth
- one target framework vs another
- one conversion scheme vs another
- one compilation path vs an alternative path

The point is not just to compile once, but to study how **compilation choices** affect the final result.

---

## Execution Requirement
You must run the workload on at least **two execution environments**.

Examples:
- ideal simulator vs noisy simulator
- one simulator backend vs another
- unconstrained simulation vs constrained target simulation

Bonus: try running on real hardware.

---

## Metrics

### Output-quality metrics
Report at least **one** output-quality metric, such as:
- success probability
- approximation ratio
- expectation value error
- total variation distance
- Hellinger distance
- fidelity proxy

### Compiled-resource metrics
Report at least **two** compiled-resource metrics, such as:
- circuit depth
- 2-qubit gate count
- circuit width
- shot count
- measurement overhead

---

## Deliverables
Each team must submit via PR:

### 1. Code Repository
A GitHub repository containing:
- Python source code
- runnable notebook or script
- dependency/setup instructions

### 2. README
Your repository README must include:
- the algorithm you chose
- the source framework representation
- the qBraid compilation strategies you compared
- the execution environments you used
- the metrics you collected
- a conclusion about the best tradeoff between quality and cost

### 3. Demo
A short presentation or demo recording explaining:
- what you built
- how qBraid was used
- what you learned from the benchmark

---

## Required Questions to Answer
Your submission must clearly answer:

1. What algorithm did you implement?
2. What was your source representation?
3. How did qBraid transform the workload?
4. What two compilation strategies did you compare?
5. What changed in the compiled programs?
6. Which strategy best preserved algorithm performance?
7. What was the cost of that strategy in compiled resources?

---

## Eligibility Rules
A submission is eligible only if it includes all of the following:

- a nontrivial algorithmic workload
- Python implementation
- at least one framework-level source representation such as Qiskit or Cirq
- explicit qBraid usage in code
- comparison of at least two qBraid compilation strategies
- execution on at least two environments
- quantitative analysis of both quality and compiled cost
- clear getting started procedures
