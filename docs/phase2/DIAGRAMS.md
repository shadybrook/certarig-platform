# CertaRig Phase 2 diagrams

## Architecture

~~~~mermaid
flowchart TB
    U["Engineering user"] --> B["Browser review interface"]
    B --> R["Evidence reasoning layer"]
    R --> M["Typed rig model"]
    M --> V["Deterministic validator"]
    V -->|Valid bounded plan| X["Deterministic simulator"]
    V -->|Missing or conflicting evidence| H["Human review required"]
    X --> T["Synthetic telemetry"]
    T --> D["Diagnosis and decision"]
    D --> E["Versioned evidence bundle"]
    S["Independent safety policy"] --> V
    S --> X
~~~~

The Phase 2 browser is the review and demonstration layer. Reasoning produces a recommendation, but deterministic rules control plan status and simulated abort behaviour.

## Data flow

~~~~mermaid
flowchart LR
    A["Configuration"] --> N["Normalize typed evidence"]
    B["Calibration records"] --> N
    C["Procedure"] --> N
    N --> C1["Compare with baseline"]
    C1 --> P["Compile bounded plan"]
    P --> G{"Evidence and limits valid?"}
    G -->|No| R["Stop or request review"]
    G -->|Yes| S["Run deterministic simulation"]
    S --> T["Evaluate telemetry"]
    T --> O{"Within policy?"}
    O -->|Yes| AC["Accept result"]
    O -->|No| AB["Safe abort"]
    R --> E["Export evidence bundle"]
    AC --> E
    AB --> E
~~~~

## Phase 2 boundary

The diagrams describe synthetic data execution. The supplementary edge service is an implementation reference and does not change the Phase 2 physical validation boundary.
