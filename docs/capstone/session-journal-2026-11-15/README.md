# Session Journal capstone draft pack

Prepared 15 November 2026. These are review drafts, not a final submission or supervisor approval.

- `CertaRig_Report_Draft_2026-11-15.pdf` and `.docx`: six supplied chapters, 238-word abstract, Times New Roman 12-point body/14-point headings, 1.5 spacing, one-inch margins and bottom-centred page numbers. Declaration/signature, roll number, institutional metadata, actual demo link and remaining qualification evidence require completion. Introduction occupies two pages; implementation and testing receive the most detail.
- `CertaRig_Demo_Draft_2026-11-15.pptx`: ten slides following the supplied institutional sequence, with native editable architecture diagram and speaker notes. Notes plan 15 minutes including a five-minute live demo; an actual attended rehearsal is still required.
- `report-metadata.json`, `presentation-validation-2026-11-15.json`, `deck-timing.json`: artifact checks and planned timing. Structural/import checks are not native PowerPoint verification or proof of factual claims.
- `source/`: editable content/build sources and the fixture screenshot used in the report. Do not execute submitted experiment code on the host; these are fixed document authoring scripts.

For regeneration, load Codex workspace dependencies and read the installed Documents/Presentations skills first. Run Python builders with the bundled Python. Link `source/node_modules` to the loaded bundled Node packages, set `RUNTIME_NODE_MODULES`, `CERTARIG_ARTIFACT_PYTHON`, `CERTARIG_PRESENTATIONS_SKILL` and `CERTARIG_CAPSTONE_TEMPLATE` to their verified local locations, then run the deck builder with the bundled Node. Output goes to a sibling `files/` folder. Use a new output/receipt filename per revision. Render and inspect changed output before delivery; source paths and template must be available in that environment.

The [current qualification ledger](../../product/validation/session-journal/README.md) is authoritative for implemented versus unverified claims. No new supervisor response or physical result has been invented. The supervisor-update draft is in the parent capstone directory and has not been sent.
