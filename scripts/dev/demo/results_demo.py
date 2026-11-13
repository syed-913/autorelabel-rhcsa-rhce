"""A workspace with made-up graded attempts, for the website's recordings of the results dashboard.

    PYTHONPATH=src python scripts/dev/demo/results_demo.py <empty folder>

Nothing here is a real result. The attempts are drawn by the real generator from the real banks,
and every check description is rendered with the task's own parameters and a sample lab, so the
pages read like they will for you. A candidate improves over five weeks, with SELinux and storage
as the weak spots and two answers lost in a reboot along the way.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

from autorelabel import labfacts
from autorelabel.bank import load_bank, render
from autorelabel.bank.select import generate

WEAK = {"rhcsa.security": 0.55, "rhcsa.storage": 0.7, "rhcsa.filesystems": 0.85, "rhce.content": 0.6}
# (exam, mode, days ago, skill): the candidate gets better, with a dip in the middle
PLAN = [("rhcsa", "exam", 36, 0.48), ("rhcsa", "practice", 33, 0.6), ("rhcsa", "exam", 30, 0.62),
        ("rhcsa", "exam", 26, 0.6), ("rhce", "exam", 24, 0.5), ("rhcsa", "practice", 21, 0.72),
        ("rhcsa", "exam", 18, 0.72), ("rhce", "exam", 15, 0.62), ("rhcsa", "exam", 12, 0.8),
        ("rhcsa", "practice", 9, 0.86), ("rhce", "exam", 7, 0.72), ("rhcsa", "exam", 5, 0.86),
        ("rhce", "exam", 3, 0.8), ("rhcsa", "exam", 1, 0.93)]


def main(root: Path) -> None:
    (root / "sessions").mkdir(parents=True, exist_ok=False)
    rng = random.Random(1300)
    now = time.time()
    lines = []
    for n, (exam, mode, days, skill) in enumerate(PLAN):
        bank = load_bank(exam)
        facts = labfacts.sample(exam)
        picked = generate(bank, 4100 + n)
        if mode == "practice":
            picked = rng.sample(picked, 6)
        tasks, score, possible = [], 0.0, 0
        for s in picked:
            t = s.task
            ctx = {**s.params, "lab": facts}
            p_ok = min(0.98, skill * WEAK.get(".".join(t.id.split(".")[:2]), 1.0) + 0.12)
            pre, post, lost = [], [], []
            for c in t.checks:
                try:
                    desc = render.render(c.desc, ctx)
                except render.RenderError:
                    desc = c.desc
                ok = rng.random() < p_ok
                ok_before = ok or rng.random() < 0.06          # now and then an answer dies in the reboot
                node = t.node
                base = {"id": c.id, "desc": desc, "node": node, "weight": c.weight, "covers": list(c.covers),
                        "guard": c.guard}
                pre.append({**base, "status": "pass" if ok_before else "fail", "detail": ""})
                post.append({**base, "status": "pass" if ok else "fail",
                             "detail": "" if ok else ("gone after the reboot" if ok_before else "not as asked")})
                if ok_before and not ok:
                    lost.append(c.id)
            own = [c for c in post if not c["guard"]]
            share = sum(1 for c in own if c["status"] == "pass") / len(own) if own else 0
            pts = round(s.points * share, 1)
            score += pts
            possible += s.points
            tasks.append({"number": s.number, "task_id": t.id, "title": render.render(t.title, ctx) if "{{" in t.title
                          else t.title, "difficulty": t.difficulty, "domain": t.domain,
                          "objectives": list(t.objectives), "points_possible": s.points, "points": pts,
                          "pre": pre, "post": post, "not_persistent": lost})
        scaled = round(score * 300 / possible, 1)
        sid = f"2026{n:02d}-demo"
        graded = now - days * 86400 - rng.randint(0, 5) * 3600

        def by(key: str, tasks: list = tasks) -> dict:
            return {k: {"points": round(sum(t["points"] for t in tasks if t[key] == k), 1),
                        "possible": sum(t["points_possible"] for t in tasks if t[key] == k)}
                    for k in dict.fromkeys(t[key] for t in tasks)}

        results = {"session": sid, "exam": exam, "mode": mode, "scoring": "partial", "score": score,
                   "possible": possible, "scaled_score": scaled, "total_points": 300, "pass_mark": 210,
                   "passed": scaled >= 210, "by_difficulty": by("difficulty"), "by_domain": by("domain"),
                   "tasks": tasks, "incidents": [], "seed": 4100 + n,
                   "elapsed_s": rng.randint(8200, bank.blueprint.duration_minutes * 60) if mode == "exam" else 0,
                   "duration_s": bank.blueprint.duration_minutes * 60, "graded_at": graded}
        (root / "sessions" / sid).mkdir()
        (root / "sessions" / sid / "results.json").write_text(json.dumps(results))
        lines.append({"session": sid, "exam": exam, "mode": mode, "score": scaled, "passed": scaled >= 210,
                      "graded_at": graded,
                      "objectives": {o: t["points"] / t["points_possible"] for t in tasks for o in t["objectives"]},
                      "tasks": {t["task_id"]: t["points"] / t["points_possible"] for t in tasks},
                      "by_difficulty": results["by_difficulty"]})
    (root / "history.jsonl").write_text("".join(json.dumps(line, sort_keys=True) + "\n" for line in lines))
    print(f"{len(lines)} made-up attempts in {root}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
