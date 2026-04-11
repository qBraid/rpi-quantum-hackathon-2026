Design a complete enterprise SaaS frontend for a product called QuantumProj.

Product thesis:
QuantumProj is a spatial decision intelligence platform for risk propagation and constrained intervention planning. It helps organizations model grid- and graph-based systems, identify where risk is emerging, simulate how it spreads, optimize limited interventions, and benchmark whether classical, quantum, or hybrid approaches perform best under realistic execution constraints.

Important:
This should feel like a real premium software product someone could sell to enterprise customers, not a hackathon toy, not a generic AI dashboard, and not three disconnected lab pages. The experience must feel cohesive and product-driven.

Design language:
Think Apple + Google Cloud + Schrödinger.
Very clean, modern, scientific, premium, calm, and trustworthy.
Desktop-first.
No clutter.
No cyberpunk.
No gamer neon.
No gimmicky 3D overload.
No overuse of glassmorphism.
Use subtle depth, careful spacing, thin dividers, clean cards, premium data tables, restrained accents, and polished motion.

Visual style:
- Primary palette: graphite, deep navy, slate, soft off-white, muted steel
- Accent colors: restrained cyan, soft violet, and one warm alert color for risk/warnings
- Typography: modern sans, highly legible, elegant hierarchy
- Rounded corners: subtle to medium, not overly bubbly
- Shadows: very soft and minimal
- Data visualization style: premium and analytical, similar to modern cloud/scientific platforms
- Quantum feel should be subtle: through structure, precision, motion, node-edge motifs, circuit-inspired detail lines, and scientific polish, not cheesy “futuristic” visuals

Create a complete design system first:
1. Color tokens
2. Typography scale
3. Spacing system
4. Grid/layout system
5. Buttons
6. Inputs
7. Dropdowns
8. Tabs
9. Chips/status pills
10. Data tables
11. Cards
12. Empty states
13. Loading states
14. Alerts
15. Modals
16. Right-side detail drawer
17. Chart styles
18. Map/heatmap styles
19. Job run status components
20. Diff/compare components

Core user flow:
Scenario Setup -> Risk Modeling -> Propagation Forecast -> Intervention Optimization -> Compiler-Aware Benchmarking -> Decision Report

Design the following pages/screens in a cohesive app shell:

1. Marketing Homepage
Purpose:
A polished homepage that presents QuantumProj as a serious enterprise platform.

Sections:
- Hero with strong product headline, supporting copy, and a premium scientific visual
- “How it works” in 4 steps: Model, Forecast, Optimize, Benchmark
- Industry use cases: wildfire resilience, infrastructure resilience, utilities, logistics
- “Why benchmark classical vs quantum?” section
- Product module cards
- Security / trust / auditability strip
- CTA area for “Request demo” and “View platform”
- Footer

Hero visual direction:
Use a refined spatial system visual: grid + node graph + subtle risk heat overlay + circuit-like precision layers. Make it feel premium, not loud.

2. Login / Auth Screen
- Clean, premium, enterprise login
- Support SSO look-and-feel
- Left side branding / right side login card or a similarly elegant split layout
- Include subtle animated scientific background

3. Main App Shell
Global app frame:
- Left sidebar navigation
- Top utility bar
- Global search / scenario search
- Project / workspace switcher
- Notifications
- User menu
- Clear hierarchy and lots of breathing room

Sidebar nav:
- Overview
- Scenarios
- Risk
- Forecast
- Optimize
- Benchmarks
- Reports
- Integrations
- Settings

4. Overview Dashboard
This must feel like the product’s command center.

Include:
- Portfolio summary cards
- Active scenarios
- Risk trend summary
- Recent benchmark runs
- Solver mix summary: classical / quantum / hybrid
- “Recommended next actions” panel
- Recent reports
- System/job health
- Quick launch actions

5. Scenario Library
A page for browsing, filtering, and managing saved scenarios.

Include:
- Search bar
- Filter chips
- Table/grid toggle
- Scenario cards or premium table rows
- Metadata: domain, last run, last report, geometry type, solver history
- Ability to open a scenario, duplicate, archive, or compare

6. Scenario Workspace
This is one of the most important screens.

Purpose:
Users define or edit a constrained spatial system.

Layout:
- Large main canvas
- Left configuration panel
- Right analysis drawer

Canvas should support:
- 10x10 grid view for wildfire-style scenarios
- node/edge network view for infrastructure-style scenarios
- heatmap overlays
- cell editing / node editing
- brush tools or simple state controls
- annotation markers
- selectable regions

Left panel:
- scenario metadata
- domain template selector
- constraints editor
- environment variables such as dryness/wind for wildfire or load/failure sensitivity for infrastructure
- intervention budget controls
- objective function summary

Right drawer:
- selected cell/node details
- local adjacency/risk details
- recommendation preview
- history / notes

7. Risk Modeling Page
Purpose:
Show where risk is concentrated and compare classical vs quantum risk scoring.

Include:
- split comparison view for Classical / Quantum / Hybrid
- risk heatmap on spatial canvas
- confidence overlay
- feature importance or explanation panel
- model summary cards
- benchmark strip showing runtime, score quality, and practicality
- “Run risk analysis” action
- job progress state
- previous run comparison

Important:
This must not feel like an ML notebook. It must feel like a product page for operational decision-making.

8. Propagation Forecast Page
Purpose:
Show how risk propagates through the system over time.

Include:
- timeline slider
- playback controls
- spread corridor visualization
- side-by-side “current vs projected” or “classical vs hybrid” forecast mode
- model diagnostics card
- simulation settings panel
- summary metrics such as projected spread area / affected nodes / time-to-threshold
- note about hardware-aware propagation engine

Design tone:
serious scientific software, not animation-heavy toy simulation.

9. Intervention Optimization Page
Purpose:
Recommend the best limited interventions under constraints.

Include:
- primary canvas with recommended intervention placements
- ranked intervention list
- before/after comparison
- budget panel
- objective function score card
- classical heuristic vs quantum optimization comparison
- impact estimates
- action buttons for save plan, export, compare plans

The user should immediately understand:
“What should I do?”
“Why these interventions?”
“What do I gain compared with alternatives?”

10. Compiler-Aware Benchmarking Page
This page is essential and should feel like a premium differentiator, not an afterthought.

Purpose:
Show how the product’s quantum workload survives compilation across frameworks and execution targets.

Frame this as:
“Execution Integrity” or “Compiler-Aware Benchmarking”

Include:
- algorithm/workload selector
- source representation card
- compilation strategy A vs strategy B compare panels
- execution environment selector
- results table with quality metrics and compiled resource metrics
- visual compare cards for circuit depth, 2-qubit gate count, width, shots, output-quality metric
- quality vs cost scatter plot
- compilation path / conversion graph style visual
- run history
- recommendation banner: best strategy under current constraints
- environment badges such as ideal simulator, noisy simulator, IBM hardware
- ability to inspect a specific run in detail

This page should make the platform feel more credible and technically differentiated.

11. Benchmark Run Detail Page
Detailed inspection page for one run.

Include:
- run metadata
- source framework
- target framework / target environment
- compilation strategy
- compiled resource metrics
- output quality metrics
- circuit summary view
- logs / job details
- notes and conclusions
- export button

12. Reports Page
Purpose:
Turn analysis into decision artifacts for teams.

Include:
- report templates
- saved reports
- report preview
- executive summary block
- key metrics summary
- recommendation section
- methodology section
- export controls for PDF / shareable link / presentation mode

13. Integrations Page
Include cards and configuration UI for:
- IBM Quantum / IBM Cloud credentials
- qBraid
- storage connector
- internal API / webhook
- future solver connectors

14. Settings Page
Include:
- workspace settings
- member management look-and-feel
- usage / compute limits
- theme options
- audit and logging settings

Add polished states for:
- empty states
- loading
- failed jobs
- no IBM credentials connected
- simulator-only mode
- partial benchmark results
- comparison unavailable
- report generating

Interactions and motion:
- subtle smooth transitions
- premium hover states
- elegant chart/tooltips
- soft progress indicators
- no flashy animations
- no novelty motion that hurts usability

Design quality bar:
Everything must feel like one product with one thesis:
Model spatial risk, simulate propagation, optimize interventions, and benchmark solver integrity under realistic execution constraints.

Do not make this feel like:
- 3 disconnected challenge tabs
- a student dashboard
- a crypto/AI landing page
- a generic bootstrap admin panel

Output:
Generate all major screens, a shared design system, reusable components, polished layouts, and a clearly cohesive product identity for QuantumProj.