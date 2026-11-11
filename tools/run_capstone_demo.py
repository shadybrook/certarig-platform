"""Reproduce the simulator milestone; approval is explicitly a fixture, never a human claim."""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from certarig.edge.bootstrap import DEFAULT_SKILLS_ROOT, NodeSettings, build_node
from certarig.edge.client import EdgeApiError, InProcessClient
from certarig.edge.evidence_cli import verify_zip
from certarig.edge.revalidation import model_revision

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True, help='new private runtime directory')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--automated-approval-fixture', action='store_true', required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    args.out.mkdir(parents=True, exist_ok=True)
    config = args.work / 'rig.json'
    shutil.copy2(ROOT / 'config/rig.thermal.capstone.json', config)
    settings = NodeSettings(config, ROOT / 'config/capabilities.capstone.json', args.work / 'evidence', None,
                            'fixture-operator-key-local', 'fixture-agent-key-local', None, True, DEFAULT_SKILLS_ROOT)
    node = build_node(settings)
    node.start()
    op = InProcessClient(node, operator_key=settings.operator_key, principal_name='automated-demo-fixture')
    try:
        deadline = time.monotonic() + 5
        while node.runtime.state()['status'] != 'ok' and time.monotonic() < deadline:
            time.sleep(.01)
        interview = op.create_interview()
        blocked_draft = op.propose_interview(interview['interview_id'])
        assert blocked_draft['status'] == 'needs_evidence'
        document = op.get('/v1/commissioning/templates')['templates']['thermal']
        document['rig_id'] = 'capstone-interview-thermal-demo'
        answers = {'equipment': 'Deterministic thermal simulator fixture', 'safe_state': 'deenergized',
                   'procedures': ['thermal_soak'], 'document': document,
                   'calibration_records': [{'calibration_id': c['calibration_id'], 'reference': 'SIMULATION_FIXTURE: synthetic scaling'} for c in document['channels']]}
        op.answer_interview(interview['interview_id'], 0, answers, {k: 'Automated fixture specification; not physical evidence' for k in answers})
        proposal = op.propose_interview(interview['interview_id'])
        if proposal['status'] != 'proposed':
            raise RuntimeError(proposal)
        op.post('/v1/rig/apply', {'document': document, 'expected_current_hash': proposal['proposal']['current_hash'],
                                'interview_id': interview['interview_id'], 'interview_revision': 1})
        op.refresh_contract()
        readiness_refused = False
        try:
            op.run_procedure('thermal_soak')
        except EdgeApiError:
            readiness_refused = True
        assert readiness_refused
        op.post('/v1/commissioning/review', {'expected_config_hash': op.rig()['config_hash'], 'procedure_ids':['thermal_soak']})
        denied = op.request_approval('run_procedure', {'procedure_id':'thermal_soak'}, 'Automated deliberate denial fixture')
        op.deny(denied['approval_id'])
        denial_refused = False
        try:
            op.run_procedure('thermal_soak', approval_id=denied['approval_id'])
        except EdgeApiError:
            denial_refused = True
        assert denial_refused
        grant = op.request_approval('run_procedure', {'procedure_id':'thermal_soak'}, 'Automated fixture; not a real human approval')
        op.grant(grant['approval_id'])
        run = op.run_procedure('thermal_soak', approval_id=grant['approval_id'])
        deadline = time.monotonic() + 15
        while not op.procedure_run(run['run_id'])['terminal'] and time.monotonic() < deadline:
            time.sleep(.02)
        result = op.procedure_run(run['run_id'])
        if result['status'] != 'passed':
            raise RuntimeError(f"demo run did not pass: {result['status']}")
        rehearsal_id = run['run_id']
        grant = op.request_approval('run_procedure', {'procedure_id':'thermal_soak'}, 'Automated execution after exact-profile rehearsal')
        op.grant(grant['approval_id'])
        run = op.run_procedure('thermal_soak', approval_id=grant['approval_id'])
        deadline = time.monotonic() + 15
        while not op.procedure_run(run['run_id'])['terminal'] and time.monotonic() < deadline:
            time.sleep(.02)
        result = op.procedure_run(run['run_id'])
        if result['status'] != 'passed':
            raise RuntimeError(f"execution did not pass: {result['status']}")
        exported = op.export_evidence(run['run_id'])
        archive = args.out / 'CertaRig_thermal_simulator_evidence.zip'
        archive.write_bytes(op.download(exported['path']))
        verification = verify_zip(archive)
        if not verification['ok']:
            raise RuntimeError(f'invalid exported evidence: {verification}')
        record = json.loads((settings.evidence_dir / 'procedure_runs' / run['run_id'] / 'sample_analysis.json').read_text())
        receipt = {
            'evidence_kind':'simulated', 'provider':'fake/no live inference',
            'approval_actor':'automated demo fixture, not a human operator', 'physical_commissioned':False,
            'run_id':run['run_id'], 'status':result['status'], 'config_hash':result['config_hash'],
            'procedure_hash':result['procedure_hash'], 'raw_analysis':record,
            'archive_sha256':exported['sha256'], 'offline_verified':True,
            'interview_id': interview['interview_id'], 'incomplete_interview_blocked': True,
            'unreviewed_start_blocked': readiness_refused, 'denied_approval_blocked': denial_refused,
            'model_revision': model_revision(node.config), 'rehearsal_run_id': rehearsal_id,
        }
        (args.out / 'demo-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2))
    finally:
        node.close()


if __name__ == '__main__':
    main()
