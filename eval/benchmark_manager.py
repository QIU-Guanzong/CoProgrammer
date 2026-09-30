"""Compare Manager snapshots with the previous duplicate-replay call sequence.

Run from the checkout: python eval/benchmark_manager.py --messages 10000 --repeats 7
Only a temporary event log is written; no repository Manager state is touched.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter, process_time
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coprogrammer import cli, collaboration as co, scheduler


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def previous_snapshot(events: list[dict]) -> tuple[dict, dict, dict]:
    """Reproduce the old sequence using the current, unchanged reducers.

    Previously sync/directory reconstructed collaboration state, then called
    the standalone task board, which reconstructed collaboration again.
    """
    sessions, messages = co.reconstruct(events)
    return sessions, messages, scheduler.board(events)


def benchmark(messages: int, repeats: int) -> dict:
    optimized_snapshot = co._snapshot
    snapshots = {"before": previous_snapshot, "after": optimized_snapshot}
    with tempfile.TemporaryDirectory(prefix="coprogrammer-benchmark-") as temporary:
        root = Path(temporary).resolve()
        path = root / "events.jsonl"
        co.register(path, root, "sender", "codex", "perf")
        co.register(path, root, "receiver", "claude", "perf")
        events = cli.load_events(path)
        for index in range(messages):
            message = {"id": f"msg_{index}", "sender": "sender", "recipient": "receiver",
                       "task": "perf", "kind": "update", "body": "Benchmark message " + "x" * 100,
                       "reply_to": "", "key": ""}
            events.append(cli.make_event("message.sent", "sender", "task:perf", {"message": message}))
        path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        result = {"format": "coprogrammer.snapshot-benchmark.v1",
                  "environment": {"python": platform.python_version(), "platform": platform.platform(),
                                  "machine": platform.machine()},
                  "workload": {"messages": messages, "events": len(events),
                               "bytes": path.stat().st_size, "repeats": repeats},
                  "baseline": "Previous call sequence: collaboration replay plus standalone task board",
                  "measurements": {}, "validation_calls": {}}
        actions = {"sync": lambda: co.sync(path, "receiver", limit=50),
                   "directory": lambda: co.directory(events)}
        for name, action in actions.items():
            outputs = {}
            measurements = {label: {"wall_ms": [], "cpu_ms": []} for label in snapshots}
            # Warm both paths and verify complete outputs outside the timed area.
            for label, snapshot in snapshots.items():
                with mock.patch.object(co, "_snapshot", snapshot):
                    outputs[label] = action()
            if outputs["before"] != outputs["after"]:
                raise RuntimeError(f"{name} snapshot outputs differ")
            for sample in range(repeats):
                order = list(snapshots.items())
                if sample % 2:
                    order.reverse()
                for label, snapshot in order:
                    with mock.patch.object(co, "_snapshot", snapshot):
                        wall_start, cpu_start = perf_counter(), process_time()
                        action()
                        measurements[label]["wall_ms"].append((perf_counter() - wall_start) * 1000)
                        measurements[label]["cpu_ms"].append((process_time() - cpu_start) * 1000)
            medians = {label: {clock: round(statistics.median(values), 3)
                               for clock, values in clocks.items()}
                       for label, clocks in measurements.items()}
            result["measurements"][name] = {
                "median": medians,
                "reduction_percent": {clock: round(100 * (1 - medians["after"][clock]
                                                          / medians["before"][clock]), 2)
                                      for clock in medians["before"]},
                "samples": {label: {clock: [round(value, 3) for value in values]
                                     for clock, values in clocks.items()}
                            for label, clocks in measurements.items()},
                "outputs_equal": True,
            }
            counts = {}
            for label, snapshot in snapshots.items():
                with mock.patch.object(co, "_snapshot", snapshot):
                    with mock.patch.object(co, "validate_event", wraps=co.validate_event) as validate:
                        action()
                        counts[label] = validate.call_count
            result["validation_calls"][name] = counts
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--messages", type=positive, default=10000)
    parser.add_argument("--repeats", type=positive, default=7)
    arguments = parser.parse_args()
    print(json.dumps(benchmark(arguments.messages, arguments.repeats), indent=2))


if __name__ == "__main__":
    main()
