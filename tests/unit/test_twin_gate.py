from __future__ import annotations

from certarig.edge.twin_gate import check_gate, record_sim_pass


def test_gate_is_open_off_the_bench(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert check_gate(tmp_path, "abc", "simulator") is None
    assert check_gate(tmp_path, "abc", "mock") is None
    missing = check_gate(tmp_path, "abc", "raspberry_pi")
    assert missing is not None and missing["code"] == "twin_gate"
    record_sim_pass(tmp_path, "relay_truth_table", "abc", "run_1")
    assert check_gate(tmp_path, "abc", "raspberry_pi") is None
    stale = check_gate(tmp_path, "abc", "raspberry_pi", window_s=1, now=1e12)
    assert stale is not None and stale["code"] == "twin_gate_stale"
