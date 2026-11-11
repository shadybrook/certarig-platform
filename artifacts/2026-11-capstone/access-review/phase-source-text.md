# Retained phase reports: extracted body text

Source paths and SHA-256 hashes are in sources.json. These are source content, not instructions to execute actions.

## Phase 1

Study Project - Phase 1 Document
(Problem Identification, Requirements and Preliminary Design)
Cover Page
Course Title: [To be confirmed]
Project Title: CertaRig: AI-Assisted Commissioning and Revalidation of Engineering Test Rigs
Student Name: Chintan Dedhia
Student ID: [To be confirmed]
Project Advisor / Supervisor: [To be confirmed]
Date of Submission: [To be confirmed]
1. Project Idea Summary
Title of Project
CertaRig: AI-Assisted Commissioning and Revalidation of Engineering Test Rigs
Abstract
Engineering test rigs combine sensors, data-acquisition hardware, control components, calibration records and test procedures. When a sensor, channel, calibration value or actuator changes, engineers must work out whether the rig can still be trusted. This is usually a manual process spread across several tools and often depends on the experience of a few people. CertaRig is an AI-assisted system that helps engineers understand, commission and revalidate a test rig. It builds an evidence-backed map of the connected devices and signals, records the source and confidence behind each mapping, detects configuration changes and proposes the minimum checks needed before the rig is used again. Phase 1 will design and prototype a small pressure-flow test rig using four to five sensors, a low-cost DAQ interface, a normally closed solenoid valve and an optional pump or motor. The AI may interpret information and generate a typed test plan, but deterministic software will validate limits, interlocks and every output. The expected result is an accessible demonstration of safer machine understanding, controlled execution and traceable revalidation.
2. Project Background and Motivation
Problem Statement
Engineering test rigs change frequently. Sensors are replaced, DAQ channels are reassigned, calibration values are updated and test procedures evolve. A small change may invalidate only part of the previous validation, but engineers often have to reconstruct the impact manually from configuration files, calibration records, scripts and historical data.
Existing test platforms can acquire data and execute procedures, but they do not always show why a channel mapping should be trusted, which evidence supports it or exactly what must be repeated after the hardware changes. This creates avoidable setup time, weak traceability and the risk of accepting incorrect results.
Motivation
CertaRig focuses on the gap between connecting hardware and being able to trust it. The project combines AI, embedded systems, data acquisition, simulation, control logic and engineering safety in one practical system. It also creates a low-cost testbed that can be built and improved without depending on expensive industrial equipment.
3. Educational Value and Course Alignment
Relevance to Course Objectives
The project applies software and systems engineering concepts to a complete physical-computing problem. It covers:
Requirements analysis, system architecture and interface design.
Sensor acquisition, calibration, units and signal validation.
Artificial intelligence for interpretation and plan generation.
Embedded control, state machines, interlocks and fault handling.
Simulation, testing, documentation and evidence-based evaluation.
Learning Outcomes
Design a safe interface between sensors, actuators, a DAQ layer and application software.
Build a versioned system model for devices, channels, units, ranges and evidence.
Combine AI-generated suggestions with deterministic validation and execution.
Detect configuration drift and identify which checks must be repeated.
Evaluate a cyber-physical prototype using normal, faulty and incomplete-data scenarios.
4. Objectives
Primary Objectives
Build a low-cost tabletop rig with four to five sensors, a solenoid valve and an optional pump or motor.
Develop a DAQ and edge-software layer that reads calibrated signals and exposes only typed, bounded outputs.
Create an evidence-backed system graph showing devices, channels, units, ranges, relationships and confidence.
Generate a reviewable test or revalidation plan from a user request and execute it through a deterministic state machine.
Detect changed hardware or configuration and propose the minimum safe revalidation checks.
Secondary Objectives
Provide a browser interface for discovery, mapping review, arming, live telemetry and reports.
Create reusable adapters so the prototype can later support LabJack, NI-DAQmx, Modbus or OPC UA systems.
5. Research, Requirements and Preliminary Design
Existing Solutions
Engineering teams commonly use LabVIEW, TestStand, PLC/SCADA systems, data historians, Python scripts and spreadsheets. These tools are effective for acquisition and control, but information about the physical rig is often split between software, wiring, calibration records and the engineers who built it.
CertaRig is not intended to replace these tools. It adds an evidence and revalidation layer: it explains the proposed system map, tracks uncertainty, generates a typed plan and records why a changed rig can or cannot be trusted.
High-Level Design
The proposed system has five main layers and one independent safety path:
Physical rig: pressure, flow, temperature, valve-position/limit and current sensing, plus a normally closed solenoid valve and optional low-voltage pump or motor.
DAQ and edge I/O: a low-cost microcontroller or USB interface reads analog and digital inputs. An external ADC improves measurement quality; DAC, PWM or digital outputs pass through protected driver circuits.
Deterministic runtime: typed drivers, a finite-state machine, range checks, interlocks, timeouts and abort logic control every permitted output.
AI intelligence plane: reads documentation and data, proposes device mappings, explains uncertainty and generates a structured plan. It cannot directly write to actuators.
CertaRig interface: allows an engineer to review mappings, approve a plan, arm the rig, observe telemetry and export an evidence report.
Independent safety path: emergency stop, fuse, pressure relief and a hard power cutoff remain effective even if the application fails.
Figure 1. High-level architecture and separation between AI, deterministic control and independent safety.
Physical Requirements
The Phase 1 hardware will be a low-energy air or water setup. Final models and ranges will be selected after confirming budget and available equipment.
Component
Proposed Phase 1 requirement
Purpose
Pressure sensor
One low-pressure sensor; approximately 0-5 bar with a conditioned analog output.
Measures chamber or line pressure.
Flow sensor
One low-flow air or water sensor with analog, pulse or digital output.
Measures flow and checks expected valve response.
Temperature sensor
One digital temperature sensor or conditioned RTD/thermocouple.
Provides temperature context and a safety limit.
Position / limit sensor
One valve-position, proximity or limit-switch input.
Confirms whether the mechanism moved as commanded.
Current sensor
One low-voltage current sensor for the solenoid or motor circuit.
Detects open circuits, stalls or unexpected load.
Solenoid valve
One 12 V or 24 V normally closed valve for a safe low-pressure loop.
Provides a bounded actuator that fails closed.
Optional motor / pump
One low-voltage DC pump, servo or stepper motor.
Adds a second actuator only if schedule and safety checks allow.
DAQ and controller
Arduino Nano ESP32 or similar; ADS1115-class four-channel 16-bit ADC; MCP4728-class four-channel 12-bit DAC or PWM where needed.
Provides affordable analog inputs, digital I/O and controlled outputs.
Safety hardware
Emergency stop, fuse, relief path, MOSFET/relay driver, flyback diode and separate actuator supply.
Allows hard shutdown and protects controller outputs.
DAQ / DAC Clarification
LabVIEW is a software environment, not a data-acquisition board. The prototype therefore needs a low-cost DAQ layer: an ADC or DAQ board for analog sensor inputs, digital inputs for switches, and protected DAC, PWM or digital outputs for actuators. A microcontroller with an external ADS1115-class ADC and an optional MCP4728-class DAC is a practical starting point. The software adapter will hide board-specific details so another DAQ can be used later.
Technical Requirements
Area
Requirement
Phase 1 acceptance check
Input capacity
At least four analog and four digital inputs; 12-bit minimum and 16-bit preferred.
All selected sensors are sampled and timestamped without channel conflicts.
Output capacity
At least two protected digital/PWM outputs; optional analog setpoint. Loads use external drivers.
No valve or motor is driven directly from a controller pin.
Sampling
Configurable 10-20 Hz acquisition for the first pressure-flow prototype.
Telemetry remains continuous during a simulated and tabletop run.
Channel model
Stable ID, direction, type, unit, conversion, valid range and safe range for each channel.
Invalid units, unknown channels and out-of-range plans are rejected.
System graph
Device identity, channel mapping, evidence source, confidence and configuration version.
Each accepted mapping can be traced to supporting evidence.
Plan format
Typed JSON or YAML with preconditions, steps, limits, expected responses and abort rules.
A plan reaches the executor only after schema and policy validation.
Execution
Local finite-state machine with explicit arming, timeout, pause and abort states.
Injected faults produce a deterministic safe state and event record.
Change detection
Compare configuration hashes and device/channel metadata between versions.
Known sensor, range and channel changes are identified.
Interface
Browser review of system map, plan, telemetry, alarms and evidence bundle.
A reviewer can correct uncertain mappings before arming.
Security
Secrets remain server-side or local; support offline prototype operation.
No API key is stored in browser code; loss of cloud access cannot block a safe stop.
Functional Requirements
Discover configured I/O channels and display raw and calibrated values.
Build a proposed system map and mark uncertain or conflicting mappings.
Allow an engineer to confirm or correct the map before it becomes a baseline.
Convert a natural-language request into a typed test plan with limits and abort conditions.
Run a dry policy check and require explicit arming before any physical output is enabled.
Execute approved steps through the deterministic runtime and stream live telemetry.
Detect a sensor or channel change and identify the evidence that must be repeated.
Export the map, plan, event log, results and unresolved questions.
Non-Functional Requirements
Safety: low-energy hardware, independent cutoff and no direct AI-to-actuator path.
Explainability: important mappings and decisions show their source and confidence.
Reliability: the same approved configuration and plan produce reproducible state transitions.
Usability: uncertainty, limits, next actions and abort reasons are clear to an engineer.
Maintainability: adapters, system graph, policy engine, executor and interface remain separate modules.
Portability: the prototype runs on a normal laptop and supports local/offline operation.
Feasibility Analysis
The design is technically feasible with widely available microcontrollers, ADC/DAC modules, low-voltage sensors and open software libraries. The first prototype will use safe air or water and a normally closed valve. The main constraint is scope, so support will be limited to one pressure-flow rig, one controller family and a small number of input formats. Hardware actuation will begin only after the simulator, wiring checks, emergency cutoff and policy tests pass.
Preliminary Evaluation Criteria
All selected sensors and actuators appear in the system graph with units, ranges and evidence.
Swapped channels, changed ranges, missing calibration and disconnected-device cases are detected or marked unresolved.
No unvalidated or unapproved plan reaches the actuator driver.
Simulated faults and a physical emergency-stop test place outputs in the defined safe state.
Each run produces an evidence bundle containing configuration, plan, approvals, telemetry, events and results.
Selected Technical References
NI, LabVIEW Overview
NI, Data Acquisition Reference Design for LabVIEW
Texas Instruments, ADS1115 16-bit ADC
Microchip, MCP4728 quad 12-bit DAC
OPC Foundation, OPC UA Overview
6. Project Scope and Expected Deliverables
Scope Definition
Included
Pressure-flow simulator and a safe tabletop prototype.
Four to five sensor channels and one primary solenoid-valve output.
Low-cost DAQ/edge adapter, calibrated acquisition and protected output drivers.
Evidence-backed system graph, plan compiler, policy validation and deterministic executor.
Browser interface, telemetry, drift detection, replay and report export.
Excluded
High-pressure, high-temperature or hazardous-fluid operation.
Unattended control of safety-critical or production machinery.
Arbitrary AI-generated code running directly on actuators.
Replacement of PLC, SCADA, LabVIEW, TestStand or certified safety systems.
Support for every industrial protocol or DAQ vendor in Phase 1.
Assumptions and Constraints
The physical rig uses low-voltage components and a low-energy medium.
A human verifies mappings, approves the plan and arms the system.
Exact sensors, controller and actuator ratings depend on budget and available equipment.
Independent safety hardware remains authoritative over software.
Deliverables (Phase 1)
Completed proposal, background study and requirement specification.
High-level architecture, interface definitions and safety boundary.
Bill of materials and physical rig design.
Working browser simulator and low-cost DAQ prototype.
System graph, policy validator, deterministic executor and evidence report.
Test scenarios, evaluation results, limitations and next-phase plan.
7. Preliminary Project Timeline and Milestones
Period
Milestone
Weeks 1-2
Confirm course requirements, use case, hardware budget and success criteria; review existing tools.
Weeks 3-4
Finalize architecture, interfaces, safety boundary, bill of materials and simulator model.
Weeks 5-6
Assemble sensor acquisition and protected actuator driver; implement DAQ adapter and calibration.
Weeks 7-8
Build system graph, mapping review and browser telemetry interface.
Weeks 9-10
Add typed plan generation, policy checks, deterministic execution and change detection.
Week 11
Run normal, fault, drift and emergency-stop scenarios; record results.
Week 12
Complete documentation, demonstration, final report and Phase 2 recommendations.
A detailed Gantt chart is not required at Phase 1.
8. Team Structure and Collaboration
Roles and Responsibilities
Chintan Dedhia will be responsible for research, requirements, architecture, hardware integration, software implementation, testing and documentation. The supervisor will review the scope, methodology, safety boundaries, progress and final results.
GitHub will be used for version control and task tracking. Shared documents will be used for design reviews and project records. AI tools may assist with research, ideation and code scaffolding, but all hardware decisions, outputs and submitted work will be checked and owned by the student.
9. Risk and Challenge Analysis
Identified Risks and Mitigation Strategies
Risk
Mitigation
Incorrect AI mapping
Require evidence and confidence for every material mapping; unresolved mappings cannot enable outputs.
Unsafe actuation
Use a normally closed valve, protected driver, explicit arming, software limits and an independent emergency cutoff.
Sensor noise or calibration error
Store calibration metadata, apply plausibility checks and compare redundant physical evidence where possible.
Hardware delay or unavailable parts
Keep the adapter vendor-neutral and maintain a simulator path for every hardware feature.
Electrical damage
Use separate actuator power, fusing, flyback protection and no direct load from controller pins.
Scope becoming too broad
Limit Phase 1 to one low-energy rig, one controller family and defined fault scenarios.
Limited real-world data
Use reproducible synthetic data first and only use approved, redacted external data.
Cloud or model failure
Keep the executor and abort logic local; loss of AI or network access cannot prevent a safe stop.
10. Supervisor Review and Approval
Advisor Feedback:
Supervisor Comments:
Recommendations:
Signature: ____________________________
Date: ________________________________

## Phase 2

Study Project: Phase 2 Document
Design and Proof of Concept
Cover Page
Field
Details
Course Title
Study Project
Project Title
CertaRig: Agentic AI for Automated Commissioning and Revalidation of Engineering Test Rigs
Student Name
Chintan Dedhia
Student ID
2023EB03005
Project Advisor / Supervisor
Professor Raj Kumar
Date of Submission
31 August 2026
Phase 2 status: The browser proof of concept, repository, report, and software validation are complete. Six browser tests and eight supplementary Python tests pass locally. The demonstration video is being revised to show the repository, local server, live proof of concept, four cases, evidence export, and test results. The revised video will use the existing Drive link. Physical hardware validation remains Phase 3 work.
1. Introduction
1.1 Purpose of Phase 2
Phase 1 defined CertaRig as an agentic AI system for commissioning and revalidating engineering test rigs. The central problem is not only data acquisition. It is the engineering reasoning required to discover connected devices, interpret evidence, generate a trustworthy system model, plan bounded checks, diagnose mismatches, and decide whether a configuration can be accepted. Phase 2 translates that definition into a concrete design and a demonstrable software prototype.
The Phase 2 objective is to prove that the core reasoning and evidence loop can be represented as a controlled software workflow. The PoC therefore models a small pressure and flow rig, evaluates channel and calibration evidence, compiles a bounded commissioning plan, generates repeatable telemetry, detects conflicts and unsafe conditions, and produces an evidence bundle. AI assisted reasoning remains outside the deterministic execution and safety path.
1.2 Scope of Phase 2
This phase includes the following work:
A system architecture that separates discovery, rig modelling, planning, diagnosis, evidence storage, deterministic execution, and independent safety.
Detailed functional and non functional requirements derived from the Phase 1 objectives.
A high level data model for devices, channels, evidence, plans, runs, findings, and approvals.
A browser based PoC with four repeatable engineering cases and JSON evidence export.
Automated tests for the acceptance behaviour of the four cases.
A supplementary computer to Raspberry Pi implementation reference with an authenticated edge API, configuration hashing, hardware adapter boundaries, human approval, deterministic execution, and SQLite evidence storage.
A ten minute demonstration plan covering users, benefits, architecture, data flow, PoC cases, and Phase 3 readiness.
The supplementary reference software does not establish physical validation. Live sensor calibration, industrial protocols, physical actuation, independent emergency stop testing, electrical protection, and safety certification require a controlled hardware environment and remain Phase 3 work.
2. System Overview
2.1 Product Perspective
The Phase 2 PoC is a stand alone browser application that represents one bounded part of the wider CertaRig ecosystem. It can be served locally and runs without cloud credentials or external APIs. The engine is implemented as a separate JavaScript module so the same comparison, policy, planning, simulation, and diagnosis rules can later move behind an authenticated service without changing their public contract.
A supplementary computer to Raspberry Pi reference implements the same separation without claiming physical validation. Human reviewers confirm uncertain mappings and approve the exact plan and configuration hash. An optional structured AI planner may propose a typed plan, but it cannot approve, execute, call GPIO, or change a safety limit. Physical output remains subject to independent limits and protection that AI cannot override.
2.2 Major System Functions
Function
Phase 2 behaviour
Evidence ingestion
Accept configuration, calibration, procedure, telemetry, and controller metadata from approved sources.
Rig model
Represent devices, channels, units, ranges, calibration, relationships, confidence, and source evidence as a versioned graph.
Change analysis
Compare an approved baseline with a proposed configuration and identify changed or missing material claims.
Plan compilation
Create bounded checks with prerequisites, expected response, acceptance criteria, and explicit abort rules.
Deterministic execution
Run defined simulator states, preserve a safe default output, enforce limits, and record every transition.
Diagnosis
Compare predicted and observed behaviour and explain likely mapping, calibration, range, connection, or response conflicts.
Human review
Show confidence, evidence, limits, unresolved items, and the exact reason for acceptance, review, stop, or abort.
Evidence export
Export the model version, findings, plan state, telemetry, source list, and checksum as JSON.
2.3 User Classes and Characteristics
User class
Needs and responsibilities
Test engineer
Reviews the proposed rig model and plan, checks measured behaviour, and accepts or rejects the resulting baseline.
Instrumentation engineer
Verifies wiring, channel identity, units, calibration, ranges, and sensor response evidence.
System administrator
Configures user access, source connections, retention, and approved controller adapters in a future deployment.
Project supervisor or auditor
Reviews requirements, test cases, evidence, limitations, and the justification for Phase 3 work.
External engineering systems
DAQ, PLC, SCADA, LabVIEW, TestStand, Modbus, or OPC UA systems that provide data or execute approved work through adapters in later phases.
3. Functional Requirements
The requirements use shall statements so each item can be traced to a design element and an acceptance check.
ID
Requirement
Acceptance evidence
FR01
The system shall represent every device and channel with a stable identifier, direction, signal type, unit, valid range, safe range, calibration reference, and configuration version.
Channel map contains all required fields.
FR02
The system shall attach an evidence source and confidence value to every material mapping.
Unattributed mappings are rejected.
FR03
The system shall compare a proposed rig model with an approved baseline and identify mapping, unit, range, calibration, and connection changes.
Known injected changes are reported.
FR04
The system shall expose contradictions and unresolved material claims without inventing missing information.
Conflict produces review or stop status.
FR05
The system shall compile a typed commissioning plan containing prerequisites, ordered steps, expected response, acceptance criteria, timeout, and abort rules.
Plan object passes schema checks.
FR06
The system shall prevent execution when calibration evidence, units, material identity, or safety limits are missing or unresolved.
Missing calibration blocks the plan.
FR07
The system shall execute the PoC only through a deterministic simulator with explicit state transitions and a safe default output.
The simulator remains repeatable.
FR08
The system shall compare expected and measured pressure, flow, and valve response and create diagnostic findings.
Injected mismatch is diagnosed.
FR09
The system shall record a safe abort if the pressure trace exceeds the approved 4.2 bar PoC limit.
Limit breach returns Safe abort.
FR10
The system shall present the rig model, confidence, plan state, telemetry, findings, and final outcome in a browser interface.
All panels render for each case.
FR11
The system shall allow a user to run the four defined PoC cases from the same interface.
Scenario selector exposes four cases.
FR12
The system shall export the selected run as a structured JSON evidence bundle.
Export contains versions, channels, findings, plan, telemetry, and checksum.
FR13
The system shall retain the control authority statement that AI reasoning cannot bypass deterministic policy or independent safety.
Boundary appears in design and output.
FR14
The system shall support local operation without API keys or a network connection after the source is available.
Static local server runs the PoC.
4. Non Functional Requirements
4.1 Performance Requirements
A scenario analysis should complete within one second on a normal development laptop because the Phase 2 dataset contains only four channels and twenty five telemetry records.
The interface should remain responsive while switching between cases and rendering the telemetry chart.
The design should support at least one hundred channels and ten thousand run records per rig when persistent storage is introduced in Phase 3, subject to measurement on the selected deployment stack.
4.2 Security Requirements
No credential, API key, or controller secret shall be stored in browser source code.
The Phase 2 PoC shall use synthetic data and shall not connect to a production network or live controller.
Future write actions shall require authenticated roles, an approved plan, and a complete audit record.
Loss of network or AI service availability shall not prevent a local stop or safe default output.
4.3 Usability Requirements
The interface shall show the selected case, outcome, findings, confidence, pressure limit, plan state, and evidence checksum without requiring specialist debugging tools.
Status shall use both text and colour so meaning is not dependent on colour alone.
Page structure shall use semantic headings, labels, tables, lists, and an accessible telemetry description.
A reviewer shall be able to understand why a run stopped and what evidence is required next.
4.4 Scalability and Maintainability
The browser rendering, engineering engine, test cases, and documentation shall remain separate files.
Device and protocol support shall be added through adapters instead of changing the central evidence model.
Policy, plan, and simulator results shall use typed objects that can be stored or served through an API later.
Automated tests shall protect the accepted behaviour of each demonstration case.
5. System Architecture and Design
5.1 System Architecture Diagram
Figure 1. CertaRig architecture with separated reasoning, deterministic execution, evidence storage, and independent safety.
The browser is a human review surface. It does not own safety decisions or physical output. Discovery, rig modelling, experiment planning, and diagnosis produce proposed facts and actions with evidence. Only a validated plan may reach the deterministic runtime. The versioned store retains the material inputs and outputs, while independent safety remains authoritative over any future physical path.
5.2 Module Wise Design
Module
Responsibility
Inputs
Outputs
Browser interface
Presents cases, map, telemetry, findings, plan, status, and export.
Scenario selection and engine result.
Readable review state and JSON download.
Discovery
Collects controller, configuration, document, and live channel evidence.
Approved sources and adapter responses.
Candidate devices, channels, sources, confidence.
Rig model
Normalizes evidence and maintains the versioned system graph.
Discovery claims and reviewer corrections.
Typed devices, channels, limits, versions.
Change analysis
Compares the proposed version with the approved baseline.
Two rig graph versions.
Material changes and invalidated evidence.
Policy and plan
Checks prerequisites and compiles bounded test steps.
Changes, limits, confidence, approvals.
Allowed or blocked plan with abort rules.
Deterministic runtime
Owns state transitions, timeout, safe default, abort, and replay.
Validated plan and simulated inputs.
Events and telemetry.
Diagnosis
Explains response conflicts and selects the next safe investigation.
Predicted response, telemetry, and changes.
Findings, review requests, or acceptance.
Evidence bundle
Packages the complete run for review and reuse.
Versions, sources, plan, events, findings.
Structured JSON and checksum.
5.3 Data Flow Design
Figure 2. Traceable data flow from approved source records to a reviewed evidence bundle.
The workflow begins with approved records. Normalization converts them into consistent engineering units and typed claims. Version comparison determines which claims and previous checks are affected. Plan compilation converts only resolved claims into bounded steps. The deterministic runtime produces measurements and events. Diagnosis then accepts the result, requests review, or records a stop. Every stage contributes to the final evidence bundle.
5.4 Database Design
The browser proof of concept keeps its small dataset in memory and exports JSON. The supplementary reference edge service stores plans, approvals, runs, telemetry summaries, outcomes, and evidence checksums in SQLite. The following logical schema remains the target for a fuller multiuser deployment.
Entity
Important attributes
Relationship
Rig
rig_id, name, medium, status
Owns devices and graph versions.
Device
device_id, type, vendor, model, firmware
Belongs to a rig and exposes channels.
Channel
channel_id, direction, signal_type, unit, valid_range, safe_range
Belongs to a device and has mappings.
Evidence
evidence_id, source_type, source_uri, checksum, captured_at
Supports one or more claims.
Claim
claim_id, subject, predicate, value, confidence, status
Links a model statement to evidence.
GraphVersion
version_id, parent_version, configuration_hash, approved_at
Captures an immutable rig baseline.
Plan
plan_id, version_id, state, limits, approval
Contains ordered plan steps.
Run
run_id, plan_id, build_version, start_time, outcome
Owns events, telemetry, and findings.
Telemetry
run_id, timestamp, channel_id, value, quality
Stores measured or simulated samples.
Finding
finding_id, run_id, code, severity, rationale, resolution
Records conflict, stop, abort, or acceptance evidence.
6. Technology Stack and Justification
Layer
Technology
Reason for selection
Frontend
HTML, CSS, and JavaScript modules
They provide a portable browser PoC with no framework dependency, clear separation of concerns, semantic markup, responsive layout, and direct JSON export.
Engineering engine
JavaScript module
The comparison, policy, simulation, plan, and diagnosis logic can be tested independently from the interface and can later move to a service.
Edge service
Python standard library HTTP and JSON API
It provides a small auditable computer to Raspberry Pi contract without a required web framework.
Hardware adapters
Mock adapter, GPIO Zero, and ADS1115 through smbus2
The same executor contract supports repeatable software tests and a replaceable Raspberry Pi input and output boundary.
Automated testing
Node.js and Python built in test runners
They verify the browser cases, safety validation, execution, pressure abort, authentication, approval, and complete localhost API workflow.
Data representation
Typed JavaScript objects, Python dataclasses, and JSON
The formats are easy to inspect, export, version, validate, and map to an API or database schema.
Evidence persistence
SQLite
The local edge service records completed and aborted runs with an evidence checksum while remaining suitable for Raspberry Pi pilots.
Optional AI and tool access
OpenAI structured output and read only MCP tools
AI output remains an untrusted plan proposal, and the MCP surface omits approval, execution, GPIO, shell, and unrestricted network tools.
Version control
Git and GitHub
They provide a public source record, issue history, commits, and a stable link for academic review.
Future shared deployment
PostgreSQL and an authenticated gateway
These can extend the local pilot to multiple users after the single rig safety and evidence contract is physically validated.
Important design choice: The browser proof of concept remains independently runnable. The supplementary edge service is a separate reference layer so hardware access, authentication, approval, and persistence do not weaken the original deterministic regression baseline.
7. Proof of Concept
7.1 PoC Description
The implemented PoC covers the rig model, change detection, plan gating, deterministic simulation, telemetry presentation, diagnosis, and evidence export for a four channel pressure and flow rig. The model contains a pressure sensor, flow sensor, valve position input, and normally closed valve command. Each channel carries a unit, range, calibration reference where applicable, confidence, and evidence description.
The purpose of the PoC is to demonstrate feasibility with repeatable evidence. It does not attempt to imitate a general autonomous engineering agent. Instead, it proves the smaller and more important contract: evidence is normalized, material uncertainty blocks work, an approved plan is deterministic, unsafe measurements cause a defined abort, and every outcome is explainable.
GitHub repository: Open the CertaRig Phase 2 GitHub repository
Demo video: https://drive.google.com/file/d/1npXhGGxv_TO6uO_AgGHJ4f1uxSdn8cJf/view?usp=sharing
Figure 3. Browser PoC showing the approved baseline case, model confidence, telemetry, diagnosis, and outcome.
7.2 PoC Demonstration Details
Case
Scenario
Observed evidence
Outcome
Feasibility claim
Case 1
Approved baseline
Mappings and records agree. The valve response is within limits.
Accepted
Proves the normal end to end evidence loop.
Case 2
Swapped analog channels
AI0 and AI1 conflict with the approved device and unit mapping. Response signatures also disagree.
Human evidence required
Proves change detection and refusal to guess.
Case 3
Missing calibration
The pressure sensor has no current calibration reference.
Human evidence required
Proves that a missing material prerequisite blocks execution.
Case 4
Pressure limit breach
Simulated pressure reaches 6.04 bar against a 4.2 bar limit.
Safe abort
Proves deterministic limit enforcement and evidence capture.
The revised demonstration follows the ten minute requirement in the Phase 2 template. It opens the public repository from a signed out browser, starts the website on a local server, runs all four proof of concept cases, exports the JSON evidence, and shows the complete automated validation result. The revised video will replace the current file at the same Drive link before final submission.
Features demonstrated:
Four selectable, deterministic engineering cases.
Evidence backed channel map with confidence and calibration state.
Version comparison with mapping, unit, and calibration findings.
Bounded plan states that complete, block, request review, or do not run.
Pressure and flow telemetry with a visible safety limit.
Final outcome, diagnostic rationale, evidence record count, and stable checksum.
Downloadable JSON evidence bundle.
Current limitations:
The data is synthetic and the system has no live DAQ or controller connection.
Discovery is represented by predefined evidence rather than document extraction or device interrogation.
The simulator uses a simple deterministic response rather than a calibrated physical model.
Data remains in memory and there is no authenticated multiuser review workflow.
Code generation, sandbox compilation, deployment, rollback, and physical emergency stop testing are not implemented in Phase 2.
7.3 Ten Minute Demonstration Plan
Time
Segment
Content
0:00 to 0:35
Introduction
CertaRig objective, Phase 2 scope, and what the working proof of concept demonstrates.
0:35 to 1:15
Users and benefits
Commissioning engineers, technicians, supervisors, auditors, and reviewable evidence.
1:15 to 2:10
Architecture
Browser proof of concept, supplementary edge reference, human approval, deterministic runtime, and independent safety.
2:10 to 2:55
Data flow
Rig inputs, mapping analysis, bounded plan, deterministic execution, findings, telemetry, and evidence checksum.
2:55 to 3:25
Public repository
Open the repository while signed out and show the README, source structure, run instructions, cases, and validation boundary.
3:25 to 4:05
Local server
Start a local web server and open the proof of concept from localhost.
4:05 to 6:50
Live four cases
Run the approved baseline, swapped channels, missing calibration, and pressure limit abort; export JSON evidence.
6:50 to 7:35
Agent guardrails
Show typed proposals, deterministic revalidation, human approval, restricted tools, and safe abort behaviour.
7:35 to 8:25
Automated validation
Run the complete check and show six browser tests, eight Python tests, static build, and four evidence bundles.
8:25 to 9:20
Submission evidence
Show the completed Phase 2 report, repository link, demonstration link, and the boundary between software proof and physical validation.
9:20 to 10:00
Conclusion
Summarize Phase 2 outcomes and readiness for controlled Phase 3 hardware integration.
7.4 Supplementary Computer to Raspberry Pi Reference
The repository includes a supplementary implementation reference that can run on a computer or Raspberry Pi. The edge service loads the approved rig configuration, verifies required calibration records, computes a stable configuration hash, exposes an authenticated JSON API, validates submitted plans, records a separate human approval, executes through a hardware adapter, returns outputs to a safe state, and stores evidence in SQLite. The mock adapter is software tested. The Raspberry Pi adapter defines the planned GPIO and ADS1115 boundary, but no physical hardware validation is claimed in Phase 2.
Implemented module
Current responsibility
Computer client
Reads health and snapshots, submits a proposal, requests operator approval, starts a run, and reads evidence.
Optional AI planner
Uses a typed response schema to propose a plan. The result has no approval or execution authority.
Edge safety validator
Checks configuration hash, calibration, channel identity, ranges, duration, sampling rate, and pressure limit.
Deterministic executor
Owns output state, sampling, timeout, pressure abort, stop, completion, and safe shutdown.
Evidence store
Records plans, approval, run status, reason, sample count, and checksum in SQLite.
Optional MCP surface
Allows snapshot, proposal, and evidence review only. It exposes no approval, run, GPIO, shell, or unrestricted network operation.
Validation boundary: All fourteen automated software tests pass. The hardware adapter is implementation ready but not physically validated. Sensor calibration, isolated output wiring, emergency stop, relief path, fault injection, and supervised low energy testing remain mandatory before any engineering claim about the physical rig.
8. Testing and Validation Strategy
Testing is divided into deterministic browser engine tests, Python edge tests, localhost API integration, visual inspection, and requirement traceability. Six Node.js tests and eight Python tests completed with zero failures on 24 August 2026.
Test
Area
Expected result
Result
T01
Scenario catalogue
Four cases are available.
Pass
T02
Approved baseline
Accepted, no material findings, plan allowed.
Pass
T03
Swapped channels
Mapping and signature conflicts, execution blocked.
Pass
T04
Missing calibration
Calibration finding, plan blocked.
Pass
T05
Pressure limit breach
Maximum pressure exceeds 4.2 bar and returns Safe abort.
Pass
T06
Evidence bundle
Every case produces the stable checksum contract.
Pass
T07
Browser integration
Case selector updates heading, status, metrics, findings, table, chart, and plan.
Pass
T08
Visual review
Main PoC view renders with readable controls, status, metrics, chart, and diagnosis at the default browser size.
Pass
T09
Edge configuration
Stable hash, required calibration, and stale configuration checks behave deterministically.
Pass
T10
Edge execution
Approved plan completes and leaves the output safe.
Pass
T11
Pressure abort
A limit breach aborts, leaves the output safe, and records the reason.
Pass
T12
Approval boundary
An unapproved plan cannot execute.
Pass
T13
HTTP workflow
Authentication, proposal, approval, execution, and evidence retrieval work over localhost.
Pass
8.1 Unit Testing Approach
Pure engine and edge functions are evaluated with fixed inputs. Each test checks the final status and material findings rather than relying on visual text alone. The mock adapter supplies deterministic measurements, and the API test uses localhost only. No external AI service, production controller, or random source is required.
8.2 Integration Testing Approach
The PoC is served locally and exercised in a browser. The edge integration test separately starts the JSON service on localhost and verifies an unauthorized approval attempt, authenticated approval, deterministic execution, and evidence retrieval. This establishes the computer to edge software contract before Raspberry Pi hardware access is enabled.
8.3 Manual and Safety Validation
Manual review checks that the visible outcome agrees with the evidence, the pressure limit is clear, the stop and abort reasons are understandable, and the safety boundary is not overstated. The Raspberry Pi adapter is not evidence of physical safety. Emergency stop, fuse, relief path, isolated driver, sensor calibration, loss of power, disconnected sensor, and actuator tests remain explicitly deferred to the controlled Phase 3 testbed.
9. Risks, Challenges, and Mitigation
Risk
Impact
Mitigation
Incorrect AI mapping
High
Require source evidence and confidence for every material mapping. Block unresolved units or identity before execution.
Unsafe actuation
High
Keep AI outside the direct output path. Use a deterministic runtime, normally closed valve, independent cutoff, relief path, fuse, and protected driver in Phase 3.
Missing or stale calibration
High
Treat missing calibration as a stop condition and retain certificate identity and validity with the channel claim.
Simplified simulation
Medium
Use the simulator only to prove software behaviour. Calibrate a physical model before using it for engineering prediction.
Hardware or component delay
Medium
Keep every hardware feature available through a simulator path and limit Phase 3 to one controller family.
Scope growth
High
Prioritize one pressure and flow rig, one adapter, four fault classes, and a defined evidence bundle.
Third party service failure
Medium
Support local operation and preserve safe stop behaviour without cloud or AI availability.
Data privacy or intellectual property exposure
High
Use synthetic or approved redacted records, keep secrets outside the browser, and restrict access to stored evidence.
Repository or demo link unavailable
Low
Verify both links before submission and retain a local source archive and report copy.
10. Phase 2 Outcomes and Readiness for Phase 3
Phase 2 has converted the Phase 1 concept into a concrete and testable design. The architecture, requirements, module boundaries, logical data model, browser proof of concept, evidence export, four cases, automated tests, and demonstration plan are complete. The repository also contains a supplementary computer to Raspberry Pi reference that preserves the same configuration, approval, deterministic execution, and evidence boundaries without claiming physical validation.
The project is ready for controlled Phase 3 hardware integration, but it is not ready for unattended hardware control. Readiness means that the interfaces, guardrails, and acceptance behaviour have passed fourteen software tests. It does not mean that the sensor chain, output driver, emergency stop, relief path, enclosure, or physical rig has passed engineering validation.
10.1 Key Inputs Carried Forward
The versioned rig graph and evidence claim model.
The deterministic plan, outcome, finding, and evidence bundle contracts.
The 4.2 bar PoC safety limit and normally closed default output assumption, subject to final component selection and engineering review.
The four repeatable acceptance cases, six browser tests, and eight Python edge and API tests.
The authenticated computer to Raspberry Pi API, configuration hash, separate approval record, and SQLite evidence checksum.
The browser review pattern for confidence, telemetry, findings, and plan status.
The requirement that live code must compile, pass static checks, succeed in simulation, receive approval, and retain rollback before controller deployment.
10.2 Recommended Phase 3 Sequence
Run the mock adapter on both the computer and Raspberry Pi and retain the API and evidence results.
Connect the pressure and flow sensors in read only mode and compare every channel with a traceable reference instrument.
Test GPIO only into a dummy load through a correctly rated isolated driver and verify the normally closed state on startup, shutdown, and loss of power.
Assemble the low energy testbed with independent emergency stop, fuse, relief path, protected output, and separate actuator power.
Perform stale configuration, missing calibration, disconnected sensor, wiring fault, range drift, pressure abort, emergency stop, and power loss tests.
Enable one supervised low energy rig test only after the previous evidence is reviewed and approved.
Reconcile physical results with the simulator baseline, document deviations, and decide whether wider adapter or controller support is justified.
Readiness conclusion: CertaRig is ready to proceed to controlled Phase 3 hardware integration because the Phase 2 design and the first edge software stack are explicit, repeatable, and bounded. Physical output remains conditional on independent hardware safety, competent wiring review, and human approval.
11. Supervisor Review and Approval
Advisor Feedback:
Supervisor Comments:
Recommendations:
Signature: ____________________________
Date: ________________________________

## Phase 3

Study Project Phase 3 Document
Implementation Readiness and Validation
Cover Page
Course Title: Study Project
Project Title: CertaRig: Agentic AI for Automated Commissioning and Revalidation of Engineering Test Rigs
Student Name(s): Chintan Dedhia
Student ID(s): 2023EB03005
Project Advisor / Supervisor: Professor Raj Kumar
Date of Submission: 20 September 2026
Phase 3 validates the control and evidence architecture on a low voltage dry hardware bench. The report includes the frozen course proof of concept and separately identified platform experiments that inform the capstone.
Evidence reviewed through 17 September 2026. Hydraulic commissioning remains outside the Phase 3 scope.
1. Introduction
1.1 Purpose of Phase 3
I implemented the CertaRig control and evidence loop on a Raspberry Pi 3 Model A+ using real analogue inputs, a physical emergency stop, a relay and visible red and green indicators. The tests establish that the bench can acquire signals, inhibit an output when a defined condition is exceeded, require deliberate recovery and preserve evidence of the sequence.
The immediate objective is implementation readiness for a university proof of concept. The potentiometers emulate pressure and flow through voltage scaling. No water pressure, fluid flow, pump, valve or mains load was tested. This boundary follows the scope discussed with Professor Raj Kumar on 7 September. [1]
1.2 Summary of Work Completed So Far
Phase 1 identified the work required to commission and revalidate engineering rigs: understand connected equipment, establish a trusted model, plan bounded checks, diagnose discrepancies and retain evidence for review. The proposed users are commissioning engineers and test technicians, supported by laboratory managers.
Phase 2 converted that problem into an architecture and a local browser proof of concept with four repeatable cases. It separated discovery and planning from deterministic execution, approval and evidence export. A supplementary Python reference introduced hardware adapter boundaries and an authenticated Edge API. That phase demonstrated software behaviour; Phase 3 adds measured electrical inputs and observable physical output. [2]
The current implementation also supports a separate platform experiment on an already mapped rig. Its deterministic Fake provider selects approved procedures through the Edge API. It is supplementary evidence for the future commissioning workflow and is not a claim of autonomous discovery or a benchmark of a live language model.
Architecture overview. The human and agent interface reaches approved procedures through the API; the deterministic controller retains output authority. The supplementary platform extends the same control boundary.
2. Implementation Overview
2.1 Implementation Status
Implementation level
Current state
Implemented and exercised
Pi boot and SSH; ADS1115 acquisition on A0 and A1; software emergency-stop sensing; trip latch and reset/permit sequence; transistor-driven K1; red/green indication; CSV logging and live dashboard.
Partially validated
Repeatable low voltage bench integration and short laboratory runs. Relay and lamp states shown in software are command-derived expectations; physical confirmation comes from operator observation and video.
Supplementary platform
Approved procedure runner, simulator freshness gate, configuration/procedure identity and deterministic agent selection, exercised in an isolated service on the same mapped dry bench.
Planned for capstone
Commissioning interview, reviewed mapping of another supported rig, model comparison and fallback tests, measured contact feedback, and any hydraulic implementation.
2.2 Implemented Features
Two independently adjustable potentiometers produce signals within a 0–3.3 V range. The ADS1115 converts these signals and the Pi reads them over I²C. P1 maps to a 0–10 bar pressure proxy; P2 maps to a 0–20 L/min flow proxy. The configured trip thresholds are 4.2 bar equivalent and 15 L/min equivalent. Returning a signal to its normal range leaves the trip latched until reset and a new permit request.
The controller evaluates actuation authority, requested permission, trip state, emergency-stop state and signal quality before driving GPIO23. The dashboard exposes readings and event reasons. CSV records retain samples and state transitions so the test can be reviewed after execution.
Layer
Technology and purpose
Physical bench
Raspberry Pi 3 Model A+, ADS1115, two potentiometers, dual-NC latching emergency stop, BC547 interface, K1 relay, 1 A fused 5 V indicator branch.
Acquisition and control
Python on Raspberry Pi OS; I²C ADC acquisition; GPIO adapter; deterministic limits, latching and explicit recovery.
Interface and evidence
Web dashboard, authenticated commands, time-series CSV, JSON run/configuration records, checksums and Git version history.
Supplementary platform
Edge API and approved procedure runner; a Fake policy provider for repeatable intent routing; simulator validation before selected hardware procedures.
Circuit and physical allocation
The Pi is powered through PWR IN. This tested single-supply arrangement is limited to the indicator bench. It is not the proposed supply arrangement for a future motor or hydraulic load. [3]
Figure 1. Canonical circuit verified on 12 September. Full-resolution SVG and PDF are linked in Section 9. Physical pin numbers and BCM GPIO names are different numbering systems.
Function
Verified connection
ADS1115
Pi physical 1 → 3.3 V VDD; 3 → SDA; 5 → SCL; 6 → GND; I²C address 0x48.
Potentiometers
P1 wiper → A0, ground → physical 14; P2 wiper → A1, ground → physical 9. Physical 17 supplies only the shared 3.3 V hub.
Emergency stop
NC1: physical 18 / GPIO24 to physical 20 / GND. LOW is released/healthy; HIGH/open is active. NC2 interrupts relay DC+.
Relay interface
Physical 16 / GPIO23 → 1 kΩ → BC547 base; 10 kΩ base-to-emitter; collector → CH1; emitter → common GND. S1 bridges LOW–COM. Lower control COM has no external wire.
Output supply
Physical 2 → 1 A fuse → FUSED_5V. This feeds K1 contact COM before NC2. The 100 µF positive connects to FUSED_5V and negative stripe to common ground.
Indication
K1 NC → 1 kΩ → red; K1 NO → 1 kΩ → green. Both negatives return to ground. CH2 and physical 22 remain unused.
3. System Validation and Testing
3.1 Testing Strategy
Testing progressed from read-only checks to isolated component measurements and then to integrated control. The multimeter established supply and potentiometer terminal behaviour. Pi and I²C checks established reachability and ADC identity. Raw voltage sweeps preceded emergency-stop and relay tests. Output tests were run only after the circuit and safe states were checked.
Software checks covered the logic separately from the physical bench. The recorded integrated revision passed six JavaScript tests, twenty Python tests, the static build and four evidence-bundle checks. These are revision-specific historical results, not a new execution of the test suite for this document. The GPIO adapter regression test addresses pull-up-adjusted logical state versus the actual electrical pin state. [3]
The frozen Phase 3 evidence includes relay actuation and an integrated truth table, followed by a sensor guardrail run with actuation disabled. The separate platform later exercised complete pressure, flow and emergency-stop procedures. The two bodies of evidence are labelled separately below; their counts are not combined into one benchmark.
3.2 Test Cases and Results
Frozen Phase 3 component and integration evidence
Feature tested
Expected behaviour and observed evidence
Status
ADC and two inputs
Address 0x48 detected. Paired sweep acquired 4,457 complete samples. A0 spanned 0–3.302 V and A1 0–3.300 V. [4]
Pass
Safe boot and relay command
1,318 boot samples kept GPIO23 LOW. An 817-sample reset/permit/safe run produced the observed K1 activation and release. [3]
Pass
Integrated indication
3,160 samples over 315.9 s. Three permit/safe cycles produced green permitted and red inhibited indication. [3]
Pass
Emergency stop and recovery
NC2 interrupted board power; software recorded estop_open_forced_safe. Release did not restart K1; permit before reset was rejected. [3]
Pass
Pressure and flow shadow test
7,591 samples over 758.7 s. Pressure 4.31859 and flow 15.16364 crossed their limits; output authority remained disabled. Recovery remained latched. [5]
Pass in monitor mode
Broken NC1 wire injection
Deliberate disconnection was not performed. No pass is inferred from ordinary E-stop tests. [3]
Not tested
Figure 2. Recorded dual-input voltage sweep. This is electrical input evidence, not hydraulic calibration.
Physical view and dashboard from the new recording
Figure 3. Representative permitted state on 17 September: dashboard at screen time 540.00 s and overhead bench at 541.16 s, aligned using the recorded clap. The dashboard shows output HIGH and provider fake; the bench shows the green indicator illuminated. This pairing illustrates the state, not a measured mechanical response time.
Supplementary platform repeat demonstration on 17 September
The video capture used the isolated platform service on the Raspberry Pi, with the same mapped dry bench. The normal-operation recording contains 2,276 samples; the monitor baseline contains 1,633. The five procedure reports below record software checks. Separate operator observations substantiate the normal permit/safe cycle and visible pressure/flow recovery. [6]
Procedure and run suffix
Recorded peak proxy
Checks
Result
Pressure · 092020_334b05
5.11811 bar
6 / 6
Pass
Flow · 092338_911dcc
17.45455 L/min
6 / 6
Pass
E-stop · 092658_d25f26
Not applicable
4 / 4
Pass
Agent pressure · 093119_509b29
4.9788 bar
6 / 6
Pass
Agent flow · 093355_1fc7bc
17.90303 L/min
6 / 6
Pass
Each suffix belongs to run_20260917T followed by the suffix shown. Pressure and flow runs recorded forced-safe events, return to reset-required and rejection of a permit before reset. The E-stop run recorded its open and closed events. Its open-to-closed interval was about 0.4 seconds, so the evidence does not establish a five-second hold.
The agent provider was fake/fake-policy. It selected an approved pressure or flow procedure and reported the returned result. The deployed version waited for the whole run to finish; the supervising assistant supplied intermediate movement instructions after checking the current runner step. Complete autonomous operator coaching is therefore only partially demonstrated.
The requested safe_powerdown procedure was refused because its previous simulator validation was 98.6 hours old, exceeding the 24-hour freshness rule. The six refreshed simulator scenarios had not included this procedure. No gate was bypassed and this attempt was not a successful agent shutdown. A later operating-system halt, if performed, is a separate operation. [6]
3.3 Validation Summary
The evidence demonstrates signal acquisition, bounded output permission, trip latching, deliberate recovery and inspectable records on the defined dry bench. The physical relay/E-stop integration is established by the frozen evidence. The supplementary platform adds approved procedural execution through an API. The product remains dependent on a human-verified rig map, and real language-model selection and fallback reliability remain unvalidated.
4. Performance and Reliability Analysis
Acquisition operated at approximately 10 samples per second in the paired voltage sweep. The 12 September integrated run lasted 315.9 seconds, and the monitor guardrail run lasted 758.7 seconds. These observations support a short demonstration; they do not establish continuous industrial duty or a long-duration endurance claim.
The Pi reported throttled=0x0 after the integrated run at 38.1 °C and after the shadow run at 40.8 °C. During the 17 September capture, an initial undervoltage condition led to a pause and restart. Repeated subsequent checks returned throttled=0x0. CPU and memory utilisation were not comprehensively profiled, and no throughput comparison against another controller is claimed. [3,5,6]
Procedure checks inspect software predicates and recorded events. Their reported millisecond values do not measure mechanical contact movement or load removal. No contact-feedback, optical or current sensor is installed. End-to-end actuation latency requires additional instrumentation and a defined measurement method.
5. Risk Analysis and Mitigation Review
5.1 Identified Risks (Revisited)
Risk
Observed issue or remaining exposure
Response
Wiring and contact faults
A broken connector between physical pin 2 and the fuse holder prevented indicator power.
Repair followed by continuity checks and a repeated truth table; retain the failure in the record.
Signal interpretation
The GPIO library logical value inverted the pull-up input interpretation.
Use raw pin.state and a regression test; preserve physical/BCM mapping.
Stale procedure validation
17 September safe_powerdown validation was older than 24 hours.
Refuse execution; include all intended procedures in the next preflight validation.
AI or API dependency
No evaluated live model/fallback pair; deployed coaching differs from inspected source.
Keep deterministic controller authority and explicit approvals; evaluate model behaviour separately.
Mechanical and field reliability
No relay feedback, wet loop, EMI or endurance evidence.
Restrict the present claim; add instrumentation and staged commissioning in capstone.
5.2 Mitigation Effectiveness
Staged electrical checks and repeated control tests resolved the wiring and polarity defects. The freshness gate prevented an unvalidated procedure from being treated as ready. The trip latch prevented automatic restart after healthy input recovery. These controls reduce specific risks that were exercised; they do not remove the remaining need for calibrated field sensors, independent hardware protection, fault injection and endurance testing.
6. Limitations and Constraints
The demonstrated system uses one known low voltage bench with two potentiometers. The pressure and flow numbers are engineering-scaled voltage proxies. The bench cannot substantiate pressure containment, pump or valve sizing, fluid compatibility, leakage, priming, cavitation or hydraulic performance.
The dashboard reports commanded or expected relay and indicator states. Physical confirmation remains manual. Broken sensing-wire injection, welded relay contacts, mechanical response timing and extended power-interruption testing are not validated. The project is not an industrial safety certification or a replacement for a certified safety system.
The deterministic Fake provider makes the procedure path reproducible without cloud credentials. The saved conversational work demonstrates the API workflow, but no evidence ranks a named live language model against a second candidate for this use case. A live fallback/API outage test is also outstanding. Hardware pass counts must not be described as an AI intelligence benchmark.
The proposed customer benefit is clearer preparation, operation and evidence review for commissioning engineers and test technicians. No customer deployment, measured time saving, market adoption or commercial return is claimed.
7. Future Enhancements and Scope Extension
The capstone will develop a reusable commissioning workflow for supported rigs. A short interview will ask about components, communications protocols, source addresses, signal units and scaling, pin mappings, operating limits and emergency-stop behaviour. It will produce a proposed configuration for an engineer to review and apply. Unknown information must remain unresolved until verified.
The next validation sequence is: test the interview against a second simulated rig; check configuration schema and refusal behaviour; require human application of the map; acquire signals with outputs disabled; validate the exact procedure; then authorise a controlled physical trial. Protocol adapters will be verified individually. A discovered network tag or plausible diagram interpretation alone is insufficient to authorise output. [7]
A model comparison will use the deterministic baseline and two named candidate models with fixed versions and prompts. Cases will test approved procedure selection, requests for missing information, evidence explanation, unsupported requests and bypass attempts. Record correctness, unsafe-action attempts, response time, tool errors and cost. Test unavailable-provider behaviour and uncertain-command recovery before selecting a fallback.
Further hardware work can add isolated contact feedback and a measured load-current channel, followed by another supported physical rig. Hydraulic equipment is a possible capstone validation case after its own component selection and commissioning review. The core capstone objective remains a reusable, reviewed commissioning process.
8. Learning Outcomes and Reflections
This phase taught me to verify a system in layers. A dashboard value is useful only after the electrical signal, scaling, quality and state interpretation are correct. Measuring the potentiometer terminals before connecting them and observing raw GPIO levels made those assumptions explicit.
The wiring corrections were an important lesson in traceability. Physical pin 16 is GPIO23, not ground; pin 17 supplies only the potentiometer hub in the final circuit. The fuse-holder connector failure showed why a healthy-looking software state cannot prove that power reaches an indicator. I retained those faults and the repeated tests as part of the evidence.
I also learned to distinguish a proposed action, a software command and a measured physical result. The controller can log a LOW output command, but independent relay feedback is needed to quantify contact movement. Similarly, a deterministic agent choosing a skill does not establish the quality of a language model. These distinctions make the next development questions more precise.
The missed freshness renewal for safe_powerdown was a practical release lesson. The preflight list must cover every procedure planned for a demonstration, including its exit path. The refusal was preserved so the record remains accurate.
9. Final Deliverables
Source code and Phase 3 evidence: https://github.com/shadybrook/certarig-phase-2-poc
Phase 3 documentation index: https://github.com/shadybrook/certarig-phase-2-poc/tree/main/docs/phase3
Frozen physical evidence: https://github.com/shadybrook/certarig-phase-2-poc/tree/main/phase3_evidence
Full-resolution circuit: https://github.com/shadybrook/certarig-phase-2-poc/blob/main/docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.pdf
Supplementary platform source: https://github.com/shadybrook/certarig-platform
The executable proof of concept runs locally on the Raspberry Pi. It is not presented as a permanently available public live-control endpoint. The repository provides the software and reproduction instructions.
This completed template is accompanied by the evidence register, canonical circuit, raw CSVs, run records and checksum manifests. Seven 17 September CSVs and the five procedure-report directories were copied locally; all seven CSV hashes and all 25 manifest-listed report files matched. The agent transcript is retained separately. [6]
Phase 3 edited demonstration video: final viewing link to be inserted after upload.
Continuous synchronized screen and overhead bench recording: final viewing link to be inserted after upload.
10. Conclusion
CertaRig has reached implementation readiness for the defined Phase 3 low voltage dry bench. Real input voltages, a physical emergency stop, controlled relay indication and recorded decisions operate within an explicit permission and recovery sequence. The evidence supports this bounded laboratory proof and identifies what remains to be validated.
The supplementary platform tests show how an agent interface can invoke approved procedures while the controller retains numerical and output authority. The capstone can build on that foundation by validating a reviewed commissioning interview across supported rigs, comparing live model choices and measuring physical feedback. Completion of those steps will determine readiness beyond the current bench.
Source and evidence register
[1] User-reported meeting with Professor Raj Kumar, 7 September 2026; GBrain projects/certarig-phase3-professor-scope-2026-09-07. Later video feedback requested architecture, circuit, test cases, a live PoC, AI choice/benchmark/fallback and capstone direction.
[2] CertaRig Phase 2 Report Final Submission, 31 August 2026. Source of project title, student identity, advisor and Phase 1/2 continuity. Course scope and identity have been retained.
[3] Repository phase3_evidence/2026-09-12_integrated_bench/README.md and gate2/gate3 CSVs; docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit. Revision 9007c68 identifies the published as-built update.
[4] Repository phase3_evidence/2026-09-10_dual_pot_sweep, including raw paired sweep and analysis. [5] Repository phase3_evidence/2026-09-12_sensor_guardrail_shadow, including CSV, analysis, final state and Pi health.
[6] CertaRig Section 6 Live Test Record, 17 September 2026, and supplementary_platform_20260917: five procedure reports, seven raw CSVs and agent transcript. The requirement checklist accompanying this report records exact local paths and verification status.
[7] Supplementary platform docs/platform-lab/commissioning-interview.md; docs/explainer/2026-09-13-gates-0-to-5-analysis.md; GBrain projects/certarig-platform, projects/certarig-platform-dry-bench-2026-09-12 and projects/certarig-platform-agent-loop-2026-09-13. Historical six-gate results are not relabelled as a new 17 September gate sequence.
11. Supervisor Review and Approval
Advisor Feedback:
Supervisor Comments:
Recommendations:
Signature: ___________________________
Date: _______________________________

