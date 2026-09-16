# CapCut shot list

Import order is the timeline order. Ken-Burns every still: 105% scale, slow pan, 4 to 8 seconds unless noted. Captions from [`captions.srt`](captions.srt). Bed music under −20 dB, duck under voiceover.

Clip names assume files in a folder called `CertaRig_P3_film_raw/`. Rename to match what you actually record.

| In | Out | Dur | Visual | Audio | Caption / overlay |
| --- | --- | --- | --- | --- | --- |
| 00:00 | 00:20 | 20s | `stills/00_title.png` | Silent 0–3s, then VO Title | What is CertaRig? / Presented by Chintan Dedhia |
| 00:20 | 00:48 | 28s | `stills/01_problem_operator.png` | VO Problem, first half | Work begins at the bench |
| 00:48 | 01:05 | 17s | Stock: industrial test cell or hydraulic cart | VO continues | People speak English. Rigs speak numbers. |
| 01:05 | 01:18 | 13s | Stock: pressure gauge close-up, then PLC cabinet | VO continues | 4.2 bar is not a vibe |
| 01:18 | 01:30 | 12s | `stills/02_problem_relay.png` | VO last two sentences | Who is allowed to energize the output? |
| 01:30 | 01:42 | 12s | Architecture figure, Operator + Studio only | VO What CertaRig is | Agent interprets |
| 01:42 | 01:55 | 13s | Add Agent block | VO continues | Agent interprets. Kernel decides. |
| 01:55 | 02:08 | 13s | Add Kernel block | VO continues | Kernel owns GPIO23 |
| 02:08 | 02:20 | 12s | Full `07_product_architecture.png` | VO last two sentences | The agent can ask. Only the kernel can say yes. |
| 02:20 | 02:50 | 30s | `stills/03_customer.png` | VO customer | End customer: the person who owns the bench |
| 02:50 | 03:20 | 30s | `stills/04_industries_hint.png` | VO tomorrow / mapped rig | Mapped rigs. Not unknown machines. |
| 03:20 | 04:20 | 60s | `stills/05_protocol_strip.png` plus optional stock HMI / CAN bench | VO industries | Same kernel. Different rig.json. Observe first. |
| 04:20 | 04:45 | 25s | `stills/06_ai_stack.png` column 1 highlight | VO Grok 4.6 | Build-time AI: Grok 4.6 |
| 04:45 | 05:15 | 30s | Same still, column 2 | VO Fake | Runtime default: Fake |
| 05:15 | 05:40 | 25s | `stills/07_ai_benchmark.png` | VO Claude / OpenAI / benchmark | Benchmark: skill routing, not chat quality |
| 05:40 | 06:10 | 30s | `01_gate_ladder.png` | VO gates 0–2 | Observe before actuation |
| 06:10 | 06:25 | 15s | Overhead bench B-roll if you have it, else stay on ladder | VO gates 3–5 | Twin, then arm, then restore |
| 06:25 | 06:45 | 20s | `02_hardware_peaks.png` | VO peaks and E-stop | 4.83 bar · 15.41 L/min |
| 06:45 | 07:00 | 15s | `stills/08_output_equation.png` | VO five conditions | OUTPUT = enabled AND permit AND … |
| 07:00 | 07:45 | 45s | `P3_dashboard_8080.mp4` | VO Phase 3 dashboard | Phase 3 dashboard · port 8080 · observe only |
| 07:45 | 08:15 | 30s | `studio_live.mp4` | VO Live | Studio · Live · simulator (or sidecar) |
| 08:15 | 08:35 | 20s | `studio_onboard_author.mp4` | VO Onboard / Author | Human applies the map |
| 08:35 | 09:10 | 35s | `studio_agent_pressure_start.mp4` | VO Agent Fake / type 4.2 bar | Fake agent selects the skill. Kernel compares the number. |
| 09:10 | 09:45 | 35s | `studio_pressure_trip.mp4` plus optional pot close-up | VO raise pressure / latch | 4.2 bar · kernel trip · output latched safe |
| 09:45 | 10:15 | 30s | `studio_flow_trip.mp4` | VO 15 L/min | 15 L/min · independent trip · same output |
| 10:15 | 10:35 | 20s | `studio_shutdown_approval.mp4` | VO shutdown | Shutdown needs a human |
| 10:35 | 11:00 | 25s | `studio_evidence.mp4` | VO evidence / do not mix claims | Checksummed evidence is the output |
| 11:00 | 11:08 | 8s | `stills/09_mission_1.png` | VO mission one | Commissioning interview |
| 11:08 | 11:16 | 8s | `stills/10_mission_2.png` | VO mission two | Second simulated plant |
| 11:16 | 11:24 | 8s | `stills/11_mission_3.png` | VO mission three | Relay contact feedback |
| 11:24 | 11:32 | 8s | `stills/12_mission_4.png` | VO mission four | Live bus, then hydraulic capstone |
| 11:32 | 11:40 | 8s | `stills/13_missions_summary.png` | VO last sentence of missions | Four missions. Kernel keeps authority. |
| 11:40 | 12:10 | 30s | `stills/14_close.png` | VO close | The AI can ask. Only the kernel can say yes. |

## Assembly notes

1. Put captions on a dedicated track. Curastra uses a dark rounded pill, white sans-serif, lower centre.
2. Crossfade stills 8 to 12 frames. Hard-cut into screen recordings so the UI does not ghost.
3. If a demo take overruns, extend the shot and let VO breathe. Do not speed the operator up.
4. If the Pi is off, the Studio block is still valid. Keep the `simulator` overlay on for the whole block.
5. If you already have Gate 4 hardware footage, you may insert 8 seconds under the peaks figure. Label it `12 Sep hardware · Raspberry Pi`.
