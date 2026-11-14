# CertaRig

CertaRig is a user-deployable test-operations platform. A person speaks in language. Deterministic code compares numbers, enforces limits, and owns the output. The agent reaches the rig only through the Edge API, filtered by a capability manifest.

The public voice, from the marketing branch `cursor/certarig-marketing-site-a496`, is:

> People speak English. Rigs speak numbers.
>
> CertaRig is the bridge. Speak English to any mapped test bench; it answers in numbers. Output turns on only when every check passes.
>
> The agent may ask. Only the kernel may say yes. The zip is the proof.

That marketing site is an open draft pull request. It is not merged, and it is not a live URL. Do not send people to a production domain. Send them to the repository: https://github.com/shadybrook/certarig-platform

## Who it is for

The first audience is a person who already has, or can assemble, a mapped bench and wants a record of what the bench did.

- A student or hobby lab using the cheap reference bench. The physical reference bench stays under ₹3,000.
- A university instrumentation, mechatronics, or test-engineering course that can run the simulator before any hardware.
- A small test shop or lab lead who needs a checksummed bundle, not a screenshot.
- Later, a reader who already runs a machine controller. The only exercised controller path is OctoPrint 1.11.8 with its bundled VIRTUAL printer. Physical machines are a later milestone.

The customer journey in the 11 November 2026 capstone note is: describe a supported rig, resolve missing information, review a configuration, rehearse a procedure, approve execution, and export the results with raw evidence. Completed demonstrations use simulated plants and deterministic agent fixtures.

## What an agent may say

Cite the file and the date. If a later note in the same file updates an earlier one, use the later note and name its date.

Proven and citable:

- The kernel compares numbers to limits, owns GPIO23 on the mapped Pi bench, refuses a new permit until reset, ends a run safe, and writes the evidence files. The language model chooses an approved procedure and may call `force_safe`. It does not compare the measurements. `bypass_interlock` and `override_limits` are not tools.
- A stranger can run the simulator with `make install`, `make check`, and `python -m certarig sim serve`, or with `deploy/docker-compose.yml`. Studio is served by that Edge node. The documented path is in the repository README.
- MQTT and Modbus TCP exist as observe-mode adapters.
- The 12 September 2026 dry bench, Gates 0 through 5, is a mapped Raspberry Pi sidecar on port 8081. After one failed observation run, six hardware runs passed, with 3,422 samples and 34 of 34 evaluated checks. Pressure trips were recorded at 4.83 bar and 4.34 bar against a 4.2 bar guardrail. Flow trips were recorded at 15.41 L/min and 15.21 L/min against a 15.0 L/min guardrail. The emergency stop forced safe, required reset after release, and rejected a permit before reset. The plotted times of 0.608 ms, 0.801 ms, and 0.867 ms are kernel changes to the commanded GPIO state. They are not relay-contact or load-removal times. Raw physical CSV recordings were not inside the pulled zip bundles. Say that when you cite the lab.
- The 11 November 2026 capstone receipt records 283 software tests, eight browser tests, two loopback broker tests, and 90.40 percent coverage. That receipt is a dated checkpoint. It is not a test run of later sandbox work. CR-EXT-R1 is a module and interface drawing. Supplier schematics, exact articles, fabrication, calibration, and attended trials are still ahead.
- The 13 November 2026 sandbox publication update records a fresh local `make check` at 90.33 percent coverage, a passing soak, and ten passing Studio browser tests. Real-container qualification and a Codex Cloud run were still outstanding in that note.
- The machine-control lab checks 12 integration outcomes against OctoPrint's VIRTUAL printer, including approval refusals. Request builders for Moonraker, GRBL, and SDCP are format tests. No physical machine is in those runs. The test harness uses `FakeProvider`.
- The local customer-agent lifecycle on `product/agent-lifecycle-2026-11-13` is a loopback proof: organization sessions, simulator enrollment, immutable agent versions, a five-case evaluation, independent review, and a checksummed evidence zip. Public hosting and physical execution are outside that increment. A live Dex login, the seven real-container sandbox cases, a managed Codex sign-in, and the five-minute demonstration were still acceptance gates in `docs/product/AGENT_LIFECYCLE.md`.

## What an agent must not say

- That CertaRig is a safety certificate, a SIL system, or a prediction that a physical load turned off.
- That the agent discovered an unknown bench from a photo or a diagram. The commissioning interview is a design. A human applies any `rig.json`. Nothing is energized from a guessed map.
- That Anthropic, OpenAI, or Codex has been qualified on a live key for this tree. The default agent in the platform README is Fake. Adapters exist. Live qualification is a separate gate.
- That CR-EXT-R1 has been built, calibrated, or released for fabrication.
- That the marketing site, `/try`, or a Vercel or Netlify URL is live. `/try` on the marketing branch is a static classroom bench with no operator keys, no simulator, and no Pi.
- That OPC-UA, CAN, NI-DAQ, PLC, SSO, or billing exist.
- A user count, a revenue number, a price other than the published reference-bench ceiling of ₹3,000, or a latency other than the three kernel command times above.
- Any instruction to run `deploy/install_pi.sh` on the Phase 3 submission Pi, or to write platform evidence into `phase3_evidence/`. The frozen course tree is https://github.com/shadybrook/certarig-phase-2-poc and stays frozen.

## Voice

Write the way the repository writes. Short sentences. Name the bench, the check, and the file. Prefer "mapped rig", "simulator", and "kernel" to slogans that skip the boundary. One concrete path is better than a list of futures. If a sentence needs a fact that is not in this file or in the repository, leave the sentence out.

The person who owns the repository publishes and sends. Agents draft.
