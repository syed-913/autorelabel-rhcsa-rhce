"""Retake: back to the exam's own starting point, or prepared again when the lab no longer has it."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from autorelabel import config, paths
from autorelabel import session as S
from autorelabel.engine import EXAM_START, Engine, starting_point


class FakeLab:
    """The lab's state file and snapshots, without VMs."""

    def __init__(self, names=("utility", "node1", "node2")):
        self.vms = [SimpleNamespace(name=n, domain=f"lab-{n}",
                                    spec=SimpleNamespace(role="utility" if n == "utility" else "node")) for n in names]
        self.snaps = {v.domain: set() for v in self.vms}
        self.hv = SimpleNamespace(snapshots=lambda domain: sorted(self.snaps.get(domain, ())))
        self._state: dict = {}
        self.present = True
        self.reverted: list[str] = []

    def state(self):
        return dict(self._state)

    def save_state(self, **updates):
        self._state.update(updates)

    def exists(self):
        return self.present

    def vm(self, name):
        return next(v for v in self.vms if v.name == name)

    def names(self):
        return [v.name for v in self.vms]

    def revert(self, name, nodes=None):
        self.reverted.append(name)

    def start_all(self):
        pass

    def wait_all(self, names=None, timeout=0):
        return []


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(paths, "SESSIONS", tmp_path / "sessions")
    monkeypatch.setenv("VBOX_USER_HOME", "")
    config.save(config.Settings(provider="libvirt", storage_dir=str(tmp_path), iso_path=str(tmp_path / "x.iso")))
    eng = Engine()
    lab = FakeLab()
    monkeypatch.setattr(eng, "lab", lambda exam: lab)
    prepared: list[str] = []

    def prepare(sess, **_kw):                 # what prepare leaves behind, minus the VM work
        sess.transition(S.PROVISIONING)
        for snaps in lab.snaps.values():
            snaps.add(EXAM_START)
        lab.save_state(exam_start=starting_point(sess))
        prepared.append(sess.id)
        sess.transition(S.READY)

    monkeypatch.setattr(eng, "prepare", prepare)
    return SimpleNamespace(eng=eng, lab=lab, prepared=prepared)


def graded_exam(t, seed=7) -> S.Session:
    sess = t.eng.create("rhcsa", seed=seed)
    t.eng.prepare(sess)
    for state in (S.IN_PROGRESS, S.LOCKED, S.GRADING, S.GRADED):
        sess.transition(state)
    return S.load(sess.id)


def test_a_retake_right_after_the_exam_reverts_to_its_snapshot(engine):
    exam = graded_exam(engine)
    new = engine.eng.retake(exam)
    assert engine.lab.reverted == [EXAM_START]
    assert engine.prepared == [exam.id]              # only the exam itself was prepared
    assert new.state == S.READY and new.tasks == exam.tasks and new.passwords == exam.passwords


def test_a_retake_of_a_retake_still_reverts(engine):
    exam = graded_exam(engine)
    first = engine.eng.retake(exam)
    for state in (S.IN_PROGRESS, S.LOCKED, S.GRADING, S.GRADED):
        first.transition(state)
    engine.eng.retake(S.load(first.id))
    assert engine.lab.reverted == [EXAM_START, EXAM_START] and engine.prepared == [exam.id]


def test_after_another_session_the_retake_is_prepared_again(engine):
    """A practice since then took the lab's one starting point: reverting would start the retake
    from the practice's tasks."""
    exam = graded_exam(engine)
    practice = engine.eng.create("rhcsa", mode="practice", task_ids=["rhcsa.deploy.at-job"], timed=False)
    engine.eng.prepare(practice)
    new = engine.eng.retake(exam)
    assert engine.lab.reverted == []
    assert engine.prepared[-1] == new.id and new.state == S.READY
    assert S.current().id == new.id


@pytest.mark.parametrize("lost", ["vms", "snapshot", "old-state"])
def test_a_lab_without_the_starting_point_is_prepared_again(engine, lost):
    exam = graded_exam(engine)
    if lost == "vms":                                # removed, or the other exam's lab took its place
        engine.lab.present = False
    elif lost == "snapshot":                         # rebuilt: new VMs, no exam-start snapshot
        engine.lab.snaps["lab-node1"].clear()
    else:                                            # a lab prepared before this check existed
        engine.lab._state.pop("exam_start")
    new = engine.eng.retake(exam)
    assert engine.lab.reverted == [] and engine.prepared[-1] == new.id
