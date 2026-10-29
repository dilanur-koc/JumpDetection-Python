"""Donanimdan bagimsiz deney saati ve denetlenebilir kayitlar."""

from contextlib import ExitStack
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path


class TrialClock:
    def __init__(self, duration=20.0, preparation=5.0, preparation_limit=20.0):
        self.duration = duration
        self.preparation = preparation
        self.preparation_limit = preparation_limit
        self.phase = "idle"
        self.active_at = None

    def start(self, now):
        self.started_at = now
        self.active_at = None
        self.phase = "prepare"

    def advance(self, now, ready):
        if self.phase == "prepare":
            if now - self.started_at >= self.preparation_limit:
                self.phase = "no_baseline"
            elif now - self.started_at >= self.preparation and ready:
                self.phase = "active"
                self.active_at = now
        if self.phase == "active" and now - self.active_at >= self.duration:
            self.phase = "done"
        return self.phase

    def remaining(self, now):
        if self.phase == "prepare":
            return max(0.0, self.preparation - (now - self.started_at))
        if self.phase == "active":
            return max(0.0, self.duration - (now - self.active_at))
        return 0.0


class TrialRecorder:
    def __init__(self, output, label, settings, port, baud, duration):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        self.base = output / datetime.now().strftime("%Y%m%d_%H%M%S_%f_trial")
        self.summary_path = self.base.with_suffix(".summary.json")
        self.summary = {
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "label": label, "port": port, "baud": baud,
            "test_duration_s": duration, "settings": asdict(settings),
            "count_semantics": "Experimental movement candidates; not verified jumps",
            "timestamp_semantics": "Host receive time; frame uses its final chunk time",
            "reported_jump_count": None, "frames": 0, "candidate_events": 0,
            "active_frames": 0, "single_target_active_frames": 0,
            "finish_reason": "in_progress",
        }
        self.stack = ExitStack()
        try:
            self.raw = self.stack.enter_context(self.base.with_suffix(".jsonl").open("x", encoding="utf-8"))
            self.csv_file = self.stack.enter_context(self.base.with_suffix(".csv").open("x", newline="", encoding="utf-8"))
            self.events = self.stack.enter_context(self.base.with_suffix(".events.jsonl").open("x", encoding="utf-8"))
            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(["utc", "elapsed_s", "phase", "label", "frame", "slot", "present",
                                  "x_mm", "y_mm", "speed_cm_s", "resolution_mm", "candidate_count", "status"])
            self.save_summary()
        except BaseException:
            self.stack.close()
            raise

    def chunk(self, elapsed, data, phase):
        record = {"elapsed_s": elapsed, "utc": datetime.now(timezone.utc).isoformat(),
                  "hex": data.hex(), "phase": phase, "label": self.summary["label"]}
        self.raw.write(json.dumps(record) + "\n")
        return record

    def frame(self, record, targets, count, status):
        self.summary["frames"] += 1
        if record["phase"] == "active":
            self.summary["active_frames"] += 1
            if sum(target.present for target in targets) == 1:
                self.summary["single_target_active_frames"] += 1
        for target in targets:
            self.writer.writerow([record["utc"], record["elapsed_s"], record["phase"], self.summary["label"],
                                  self.summary["frames"], target.slot, int(target.present), target.x_mm,
                                  target.y_mm, target.speed_cm_s, target.resolution_mm, count, status])

    def event(self, record, count, details=None):
        self.summary["candidate_events"] += 1
        self.events.write(json.dumps({"elapsed_s": record["elapsed_s"], "utc": record["utc"],
                                      "count": count, "details": details}) + "\n")

    def save_summary(self):
        self.summary_path.write_text(json.dumps(self.summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def finish(self, reason, count, discarded, trailing):
        self.summary.update(finish_reason=reason, candidate_count=count,
                            ended_utc=datetime.now(timezone.utc).isoformat(),
                            discarded_bytes=discarded, trailing_bytes=trailing)
        self.stack.close()
        self.save_summary()

    def report_actual(self, count):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Gercek sayi sifir veya pozitif bir tam sayi olmali")
        self.summary["reported_jump_count"] = count
        self.save_summary()
