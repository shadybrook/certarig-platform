"""Capstone acceptance tests use only local simulated equipment and fixture AI."""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
import zipfile
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from certarig.agent.orchestrator import AgentSession, OrchestratorError
from certarig.agent.policy import RuleBasedPolicy
from certarig.agent.providers.base import ProviderError
from certarig.agent.providers.fake import FakeProvider
from certarig.agent.skills import SkillIndex
from certarig.agent.tools import ToolRegistry
from certarig.agent.transcript import Transcript
from certarig.edge.approvals import ApprovalError, ApprovalRegistry
from certarig.edge.bootstrap import NodeSettings, build_node
from certarig.edge.client import EdgeApiError, InProcessClient
from certarig.edge.evidence_cli import verify_directory, verify_zip
from certarig.edge.runtime.model import Procedure
from tests.support import AGENT_KEY, CONFIG_DIR, OPERATOR_KEY, SKILLS_DIR, wait_until


@pytest.fixture
def capstone(tmp_path):  # type: ignore[no-untyped-def]
    config = tmp_path / 'rig.json'
    shutil.copy2(CONFIG_DIR / 'rig.thermal.capstone.json', config)
    settings = NodeSettings(config, CONFIG_DIR / 'capabilities.capstone.json', tmp_path / 'evidence', None,
                            OPERATOR_KEY, AGENT_KEY, None, True, SKILLS_DIR)
    node = build_node(settings)
    node.start()
    op = InProcessClient(node, operator_key=OPERATOR_KEY, principal_name='reviewer')
    agent = InProcessClient(node, agent_key=AGENT_KEY, principal_name='fixture-agent')
    assert wait_until(lambda: node.runtime.state()['status'] == 'ok')
    yield node, op, agent, settings
    node.close()


def review(op):  # type: ignore[no-untyped-def]
    return op.post('/v1/commissioning/review', {
        'expected_config_hash': op.rig()['config_hash'], 'procedure_ids': ['thermal_soak'],
    })


def approve(requester, operator, args=None):  # type: ignore[no-untyped-def]
    args = args or {'procedure_id': 'thermal_soak'}
    approval = requester.request_approval('run_procedure', args, 'fixture qualification')
    operator.grant(approval['approval_id'])
    return approval['approval_id']


def finish(node, op, approval_id):  # type: ignore[no-untyped-def]
    run = op.run_procedure('thermal_soak', approval_id=approval_id)
    assert wait_until(lambda: op.procedure_run(run['run_id'])['terminal'])
    result = op.procedure_run(run['run_id'])
    assert result['status'] == 'passed', result
    return run['run_id']


def test_review_approve_run_and_independently_verify(capstone, tmp_path):  # type: ignore[no-untyped-def]
    node, op, agent, settings = capstone
    with pytest.raises(EdgeApiError) as exc:
        op.run_procedure('thermal_soak')
    assert exc.value.code == 'commissioning_required'
    assert review(op)['status'] == 'simulation_ready'
    with pytest.raises(EdgeApiError) as exc:
        op.run_procedure('thermal_soak')
    assert exc.value.code == 'approval_required'
    run_id = finish(node, op, approve(op, op))
    export = op.export_evidence(run_id)
    path = tmp_path / 'run.zip'
    path.write_bytes(op.download(export['path']))
    assert verify_zip(path)['ok']
    folder = settings.evidence_dir / 'procedure_runs' / run_id
    run = json.loads((folder / 'run.json').read_text())
    for required in ['config.json', 'procedure.json', 'commissioning.json', 'approval.json', 'sample_analysis.json', run['recording']['filename']]:
        assert (folder / required).is_file()
    assert json.loads((folder / 'approval.json').read_text())['status'] == 'consumed'
    assert json.loads((folder / 'sample_analysis.json').read_text())['rows'] == run['recording']['samples']
    assert node.runtime.hardware.output is False
    # Offline verification still works after the service has closed.
    node.close()
    assert verify_zip(path)['ok']
    (folder / run['recording']['filename']).unlink()
    assert not verify_directory(folder)['ok']
    with pytest.raises(EdgeApiError) as exc:
        op.export_evidence(run_id)
    assert exc.value.code == 'incomplete_evidence'


def test_approval_identity_revision_denial_replay_and_expiry(capstone):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    review(op)
    aid = approve(agent, op)
    other = InProcessClient(node, agent_key=AGENT_KEY, principal_name='other-agent')
    with pytest.raises(EdgeApiError) as exc:
        other.run_procedure('thermal_soak', approval_id=aid)
    assert 'principal' in str(exc.value)
    with pytest.raises(EdgeApiError):
        op.run_procedure('thermal_soak', approval_id=aid)
    with pytest.raises(EdgeApiError):
        agent.run_procedure('thermal_soak', label='changed arguments', approval_id=aid)
    service = node.extensions['procedures']
    original = service.library.get('thermal_soak')
    changed = dict(original.raw, version=2)
    service.library.add(Procedure.from_dict(changed, approved=True))
    review(op)
    with pytest.raises(EdgeApiError) as exc:
        agent.run_procedure('thermal_soak', approval_id=aid)
    assert exc.value.code == 'approval_invalid'
    denied = agent.request_approval('run_procedure', {'procedure_id': 'thermal_soak'}, 'deny this')
    op.deny(denied['approval_id'])
    with pytest.raises(EdgeApiError):
        agent.run_procedure('thermal_soak', approval_id=denied['approval_id'])
    granted = approve(op, op)
    finish(node, op, granted)
    with pytest.raises(EdgeApiError):
        op.run_procedure('thermal_soak', approval_id=granted)
    expired = approve(agent, op)
    node.approvals.get(expired).expires_at = time.time() - 1
    with pytest.raises(EdgeApiError):
        agent.run_procedure('thermal_soak', approval_id=expired)


def test_restart_expires_authority_and_preserves_history(capstone):  # type: ignore[no-untyped-def]
    node, op, agent, settings = capstone
    review(op)
    aid = approve(agent, op)
    pending = agent.request_approval('run_procedure', {'procedure_id': 'thermal_soak'}, 'pending')
    node.close()
    restarted = build_node(settings)
    try:
        assert restarted.approvals.get(aid).status == 'expired'
        assert restarted.approvals.get(pending['approval_id']).status == 'expired'
        assert restarted.approvals.get(aid).history[-1]['event'] == 'invalidated_after_restart'
        assert restarted.runtime.hardware.output is False
        assert restarted.runtime.guardrail.trip_latched
    finally:
        restarted.close()


def test_config_change_revokes_review_and_grants(capstone):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    review(op)
    aid = approve(agent, op)
    current = op.rig()
    document = current['document']
    document['channels'][0]['channel_id'] = 'reactor_temperature'
    preview = op.post('/v1/rig/propose', {'document': document})
    applied = op.post('/v1/rig/apply', {'document': document, 'expected_current_hash': preview['current_hash']})
    assert applied['restart_required'] is False
    assert node.runtime.config.config_hash == node.extensions['procedures'].runner.config.config_hash
    assert node.approvals.get(aid).status == 'expired'
    assert not op.get('/v1/commissioning')['ready']
    assert review(op)['ready']
    assert node.runtime.state()['samples'][0]['channel_id'] == 'reactor_temperature'
    finish(node, op, approve(op, op))


@pytest.mark.parametrize('fault', ['dropout', 'bad_quality', 'saturate'])
def test_bad_observations_block_readiness_and_execution(capstone, fault):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    review(op)
    op.post('/v1/sim/fault', {'kind': fault, 'channel': 'temperature'})
    assert wait_until(lambda: not op.get('/v1/commissioning')['ready'])
    with pytest.raises(EdgeApiError):
        op.post('/v1/commissioning/review', {'expected_config_hash': node.config.config_hash, 'procedure_ids': ['thermal_soak']})
    assert node.runtime.hardware.output is False
    op.post('/v1/sim/clear', {})
    assert wait_until(lambda: op.get('/v1/commissioning')['ready'])
    assert node.runtime.guardrail.trip_latched


def test_unit_mismatch_and_stale_acquisition_block(capstone):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    review(op)
    node.runtime._stop.set()
    node.runtime._thread.join()
    node.runtime._last_sample_monotonic = time.monotonic() - 5
    assert not op.get('/v1/commissioning')['ready']
    with pytest.raises(EdgeApiError):
        op.run_procedure('thermal_soak')
    snapshot = node.runtime.hardware.snapshot()
    sample = snapshot.samples[0]
    guard = node.runtime.guardrail
    result = guard.observe(replace(snapshot, samples=(replace(sample, unit='bar'),)))
    assert not result.process_healthy
    result = guard.observe(replace(snapshot, samples=(replace(sample, captured_at=(datetime.fromisoformat(snapshot.captured_at) - timedelta(seconds=5)).isoformat()),)))
    assert not result.process_healthy
    doc = op.rig()['document']
    doc['channels'][0]['unit'] = 'K'
    preview = op.post('/v1/rig/propose', {'document': doc})
    op.post('/v1/rig/apply', {'document': doc, 'expected_current_hash': preview['current_hash']})
    assert any('unit' in b for b in op.get('/v1/commissioning')['blockers'])


def test_fixture_agent_waits_for_human_and_exports_source_linked_results(capstone, tmp_path):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    review(op)
    skills = SkillIndex.load(SKILLS_DIR)
    registry = ToolRegistry(agent, skills, poll_s=0.01)
    session = AgentSession(FakeProvider(policy=RuleBasedPolicy(skills)), registry, Transcript(tmp_path / 'fixture.jsonl'))
    results = []
    thread = threading.Thread(target=lambda: results.append(session.send('run the thermal soak')))
    thread.start()
    assert wait_until(lambda: bool(op.approvals('pending')))
    assert node.extensions['procedures'].runner.active is None
    op.grant(op.approvals('pending')[0]['approval_id'])
    thread.join(timeout=15)
    assert not thread.is_alive()
    assert 'PASSED' in results[0].text and 'Evidence CSV' in results[0].text
    assert session.provider.name == 'fake'
    forbidden = registry.execute('bypass_interlock', {})
    assert not forbidden.ok
    assert not registry.execute('ack_operator_step', {'run_id': 'x', 'step_id': 'x'}).ok
    session.close()


def test_provider_failure_cannot_grant_authority_or_stop_recording(capstone, tmp_path):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    class Broken(FakeProvider):
        def complete(self, system, messages, tools):  # type: ignore[no-untyped-def]
            raise ProviderError('fixture network failure')
    skills = SkillIndex.load(SKILLS_DIR)
    session = AgentSession(Broken(), ToolRegistry(agent, skills), Transcript(tmp_path / 'broken.jsonl'))
    op.start_recording('failure-proof')
    before = node.runtime.state()['sample_index']
    with pytest.raises(OrchestratorError, match='fixture network failure'):
        session.send('run thermal soak')
    assert node.runtime.state()['recording']['active']
    assert wait_until(lambda: node.runtime.state()['sample_index'] > before)
    assert op.approvals('granted') == []
    op.stop_recording()
    session.close()


def test_corrupt_store_and_hostile_archives_fail_closed(tmp_path):  # type: ignore[no-untyped-def]
    path = tmp_path / 'approvals.json'
    registry = ApprovalRegistry(path=path)
    approval = registry.request('reset_trip', {}, 'test', 'contract')
    registry.decide(approval.approval_id, True, 'reviewer')
    with pytest.raises(ApprovalError):
        registry.consume(approval.approval_id, 'shutdown', {}, 'contract')
    path.write_text('broken')
    with pytest.raises(ValueError):
        ApprovalRegistry(path=path)
    archive = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as out:
        out.writestr('../escape', b'bad')
        out.writestr('SHA256SUMS.txt', hashlib.sha256(b'bad').hexdigest() + '  ../escape\n')
    assert not verify_zip(archive)['ok']
    archive.write_bytes(b'corrupt')
    assert not verify_zip(archive)['ok']


def test_review_rejects_stale_unknown_and_read_only_requests(capstone):  # type: ignore[no-untyped-def]
    node, op, agent, settings = capstone
    with pytest.raises(EdgeApiError):
        agent.post('/v1/commissioning/review', {'expected_config_hash':node.config.config_hash,'procedure_ids':['thermal_soak']})
    with pytest.raises(EdgeApiError):
        op.post('/v1/commissioning/review', {'expected_config_hash':'old','procedure_ids':['thermal_soak']})
    for ids in [[], ['unknown'], 'thermal_soak']:
        with pytest.raises(EdgeApiError):
            op.post('/v1/commissioning/review', {'expected_config_hash':node.config.config_hash,'procedure_ids':ids})
    op.start_recording('do-not-reconfigure-active-recorder')
    with pytest.raises(EdgeApiError):
        op.post('/v1/rig/apply', {'document':op.rig()['document'],'expected_current_hash':node.config.config_hash})
    op.stop_recording()
    # An on-disk edit is not automatically accepted by a running process.
    raw = json.loads(settings.config_path.read_text())
    raw['revision'] = 'external-edit'
    settings.config_path.write_text(json.dumps(raw))
    assert any('disk' in b for b in op.get('/v1/commissioning')['blockers'])


def test_source_clock_progress_and_malformed_samples_fail_safe(capstone):  # type: ignore[no-untyped-def]
    node, op, agent, _ = capstone
    node.runtime._stop.set()
    node.runtime._thread.join()
    snapshot = node.runtime.hardware.snapshot()
    guard = node.runtime.guardrail
    sample = snapshot.samples[0]
    guard._source_progress[sample.channel_id] = (sample.captured_at, time.monotonic()-5)
    assert not guard.observe(snapshot).process_healthy
    assert not guard.observe(replace(snapshot, samples=(replace(sample,captured_at='not-a-time'),))).process_healthy
    assert not guard.observe(replace(snapshot, samples=())).process_healthy
    assert not guard.observe(replace(snapshot, samples=(replace(sample,value=float('nan')),))).drive_high
    # A real adapter's old source timestamp cannot be made fresh by HTTP receipt.
    guard.config = replace(guard.config, hardware=replace(guard.config.hardware,mode='raspberry_pi'))
    assert not guard.observe(snapshot).process_healthy


def test_offline_verifier_recomputes_analysis_and_rejects_symlinks(capstone, tmp_path):  # type: ignore[no-untyped-def]
    node, op, agent, settings = capstone
    review(op)
    run_id = finish(node,op,approve(op,op))
    folder = settings.evidence_dir/'procedure_runs'/run_id
    summary = folder/'sample_analysis.json'
    summary.write_text('{"rows": 999}')
    # Verification must reject the changed summary before or during semantic reproduction.
    result = verify_directory(folder)
    assert not result['ok']
    assert any('does not reproduce' in error for error in result['errors'])
    link = tmp_path/'evidence-link'
    link.symlink_to(folder/'run.json')
    assert not verify_directory(tmp_path)['ok']
    empty = tmp_path/'empty.zip'
    with zipfile.ZipFile(empty,'w') as archive:
        archive.writestr('SHA256SUMS.txt','')
    assert not verify_zip(empty)['ok']
