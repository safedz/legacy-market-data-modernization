
from fault_injection import FAULTS, inject_faults, run_fault_injection


def test_every_injected_fault_is_rejected_for_the_right_reason(tmp_path, sim_files):
    msg, _ = sim_files
    result = run_fault_injection(msg, work_dir=tmp_path / "w", per_fault=3)
    assert result["injected"] == 3 * len(FAULTS)
    assert result["missed_faults"] == []
    assert result["unexpected_rejections"] == []
    assert result["wrong_reason"] == []
    assert result["reconciliation_pass"] is True
    assert result["pass"] is True


def test_original_file_is_not_modified(tmp_path, sim_files):
    msg, _ = sim_files
    before = msg.read_bytes()
    inject_faults(msg, tmp_path / "copy.csv")
    assert msg.read_bytes() == before
    assert (tmp_path / "copy.csv").read_bytes() != before


def test_injection_is_deterministic(tmp_path, sim_files):
    msg, _ = sim_files
    a = inject_faults(msg, tmp_path / "a.csv", seed=1)
    b = inject_faults(msg, tmp_path / "b.csv", seed=1)
    assert a == b
