# Signed missions, rubric and acceptance mapping

Baseline: CertaRig_Phase3_DocumentSigned.pdf, pages 18–19, seven future missions; signed approval on page 21. Mission summaries below are paraphrases. User-approved plan selects a water loop as the physical extension and defers live-provider qualification. Institutional files supply report/presentation requirements, not authorization to operate equipment.

| Signed mission | Implemented software / validation | Submission evidence / remaining gate |
|---|---|---|
| Conversational commissioning | Persistent interview; provider-neutral tool; bounded deterministic routing; source and unit/calibration blockers; operator apply | Interview contract/browser tests; live model interpretation unqualified |
| Distinct second plant | Seeded first-order thermal model and five RC scenarios; generic legacy simulator preserved | Two configuration-only browser journeys; recorded RC parameters/revision |
| Complete evidence | Interview/history/calibration/revalidation/rehearsal/approval/raw CSV/check reproduction | Reproducible ZIP and corrupt/missing-artifact refusals; no claim of external certification |
| Measured feedback and timing | Separate electrical feedback, required-feedback latch, pulse/current/temp adapter foundations; sampled transition intervals | Software fixtures only; physical voltage/current/response measurement pending |
| AI/model qualification | Fixture routing, refusal, approval and provider-failure cases | Explicitly deferred candidate-provider comparison; no live-run metrics |
| Broader rig integration | Actual broker-backed observe-only MQTT with strict source quality; legacy fixture retained | Local Mosquitto integration test; real external equipment qualification pending |
| Calibrated sensing and protected actuation | Mixed source validation and staged physical attestation/receipt gates | Purchase/design holds; physical E-stop/pump/valve/flow calibration and 60-minute session pending |

| Assessment | Marks | Evidence to submit |
|---|---:|---|
| Continuous evaluation | 20 | Actual dated progress, signed Phase 3 baseline, genuine weekly supervisor feedback; new remarks remain blank |
| Implementation | 30 | Reviewable source commits, configuration-only onboarding, agent/operator boundaries, thermal model, broker and feedback architecture |
| Testing | 15 | Current lint/type/90% coverage gate, property/scenario, browser and broker logs; later calibration and attended physical results with uncertainty |
| Documentation | 20 | Six-chapter PDF, 200–300 word abstract, front matter, references, user/installation guides, source and actual demo link |
| Presentation/demo/viva | 15 | University ten-slide sequence, 15-minute script with five-minute success/refusal demo; actual rehearsal and narrated recording remain student work |

Required acceptance is covered by tests/contract/test_capstone_workflow.py, test_commissioning_extension.py, test_mqtt_broker.py; tests/agent/test_policy.py and provider-failure tests; tests/scenario and property; studio/e2e/zz_capstone.spec.js and zz_commissioning_interview.spec.js. Test fixtures do not prove real wiring, pressure protection, calibration or E-stop power removal.

The software checkpoint date is 20 November 2026. Final university deadline, academic year and current submission instructions require confirmation. The approved report's advisor is historical evidence; no new supervisor interaction is invented.
