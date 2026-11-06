import {
  Card, CardBody, CardHeader, Divider, Grid, H1, H2, Link,
  Pill, Row, Stack, Stat, Table, Text, useState,
} from "cursor/canvas";

type Family = "All" | "Filament" | "CNC" | "Resin";
const routes: { family: Family; name: string; path: string; proof: string; condition: string; url: string }[] = [
  { family: "Filament", name: "OctoPrint", path: "HTTP job and file APIs", proof: "Real controller + VIRTUAL printer passed", condition: "Physical compatibility pending", url: "https://docs.octoprint.org/en/main/api/job.html" },
  { family: "Filament", name: "Klipper / Moonraker", path: "HTTP / JSON-RPC", proof: "Request builders tested", condition: "Commission objects, macros and firmware", url: "https://moonraker.readthedocs.io/en/latest/external_api/printer/" },
  { family: "Filament", name: "PrusaLink", path: "Manufacturer OpenAPI", proof: "Documented route", condition: "Verify model and API version", url: "https://github.com/prusa3d/Prusa-Link-Web/blob/master/spec/openapi.yaml" },
  { family: "Filament", name: "Bambu Fleet Hub", path: "Published local HTTP API", proof: "Documented route, May 2026", condition: "Hub, activation and client certificates", url: "https://portal.bblmw.com/fleet-hub/wb76oog4i8k/files/Bambu%20Fleet%20Hub%20HTTP%20API%20EN%20v1.0.0.pdf" },
  { family: "CNC", name: "GRBL", path: "Serial protocol", proof: "Status / hold / resume bytes tested", condition: "Sender, alarms, homing and setup validation pending", url: "https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md" },
  { family: "CNC", name: "LinuxCNC", path: "Python NML via local service", proof: "Documented route", condition: "Exact machine profile and Linux controller host", url: "https://linuxcnc.org/docs/stable/html/config/python-interface.html" },
  { family: "CNC", name: "FANUC / Siemens", path: "FOCAS2 / Access MyMachine OPC UA", proof: "Vendor interfaces documented", condition: "OEM options and permitted operations vary", url: "https://www.fanucamerica.com/products/software/cnc/focas2-library" },
  { family: "Resin", name: "SDCP 3.0", path: "WebSocket + device-specific files", proof: "Control message construction tested", condition: "Exact device capabilities and sliced format", url: "https://github.com/cbd-tech/SDCP-Smart-Device-Control-Protocol-V3.0.0" },
  { family: "Resin", name: "Formlabs", path: "PreForm API + Dashboard APIs", proof: "Official preparation and job route", condition: "Supported software, printer and account", url: "https://developer.formlabs.com/getting-started/quickstart/" },
];

export default function MachineControlFeasibility() {
  const [family, setFamily] = useState<Family>("All");
  const selected = routes.filter(r => family === "All" || r.family === family);
  return <Stack gap={22}>
    <Stack gap={8}>
      <Text size="small" tone="secondary">CertaRig research · 7 November 2026</Text>
      <H1>Machine control is feasible through existing controllers</H1>
      <Text>The first verified result is a complete virtual printer job lifecycle through real OctoPrint and CertaRig's existing agent tool loop.</Text>
    </Stack>
    <Grid columns={3} gap={16}>
      <Stat label="Gateway and existing agent tests" value="52 passed" />
      <Stat label="Real controller integration checks" value="12 passed" />
      <Stat label="Short virtual job completion" value="100%" />
    </Grid>
    <Text size="small" tone="secondary">Source: isolated research checkout, unit and agent test output, and evidence/machine-control/octoprint-virtual-final/result.json. These counts are tests and software checks, not physical production trials.</Text>
    <Card>
      <CardHeader>What the experiment establishes</CardHeader>
      <CardBody><Stack gap={8}>
        <Text>Start with approval → Printing → Pause → Paused → Resume with fresh approval → Printing → Cancel → Operational.</Text>
        <Text>Unapproved start and resume were refused. A second short job completed. The test used OctoPrint 1.11.8 and its bundled VIRTUAL printer, a scripted provider and approvals issued by the automated test harness.</Text>
        <Text tone="secondary">No physical motion or live LLM inference was tested. Controller acknowledgements were followed by observed state confirmation.</Text>
      </Stack></CardBody>
    </Card>
    <Stack gap={10}>
      <H2>Choose an integration route</H2>
      <Row gap={8} wrap>{(["All", "Filament", "CNC", "Resin"] as Family[]).map(f =>
        <span key={f}><Pill active={family === f} onClick={() => setFamily(f)}>{f}</Pill></span>)}</Row>
      <Table headers={["Machine ecosystem", "Interface", "Evidence today", "Condition for deployment"]}
        rows={selected.map(r => [<span key={r.name}><Link href={r.url}>{r.name}</Link></span>, r.path, r.proof, r.condition])}
        striped />
      <Text size="small" tone="secondary">Sources: upstream project and manufacturer documentation, reviewed 7 November 2026. Protocol availability does not prove compatibility with every model or firmware.</Text>
    </Stack>
    <Divider />
    <Grid columns={2} gap={24}>
      <Stack gap={10}>
        <H2>Architecture to carry forward</H2>
        <Text>Operator request → model proposes a typed action → machine policy validates authority, state and job → adapter calls the existing controller → controller executes → observed outcome becomes evidence.</Text>
        <Text>Reuse AgentSession, provider adapters, approvals, procedures and evidence. Add a machine job contract; the current binary valve abstraction is too narrow for CNC and printers.</Text>
        <Text>CAD, CAM or slicing prepare the artifact. Geometry checks and part inspection close the engineering loop. Model reasoning belongs above the controller's motion and emergency functions.</Text>
      </Stack>
      <Stack gap={10}>
        <H2>Milestones still required</H2>
        <Text>1. One physical filament printer: commissioned profile, approved lifecycle, interrupted-job recovery and inspected part.</Text>
        <Text>2. One GRBL or LinuxCNC machine: supervised air motion, then a defined cutting task with verified setup.</Text>
        <Text>3. One resin printer: compatible sliced job, material and local readiness checks, lifecycle and final inspection.</Text>
        <Text>4. Live model evaluations and a repeatable customer workflow. Expand OEM coverage after these results exist.</Text>
      </Stack>
    </Grid>
    <Stack gap={8}>
      <H2>Practical product direction</H2>
      <Text>A common commissioning, approval, execution and evidence workflow for specific supported machines. Natural-language printer tools already exist; repeatable setup, recovery and inspectable part outcomes are the stronger opportunity.</Text>
      <Text tone="secondary">Open issues: stale firmware telemetry, artifact mutation, concurrent clients, durable recovery state and machine-specific pause/stop effects. MTConnect supplies observation, not actuation.</Text>
    </Stack>
  </Stack>;
}
