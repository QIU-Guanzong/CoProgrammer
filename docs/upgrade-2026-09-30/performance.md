# Manager snapshot performance — 2026-09-30

The upgrade removes the second collaboration-history replay performed by a combined Manager snapshot. `collaboration.sync` and `collaboration.directory` now share the result already validated for that exact event sequence. The standalone task board still validates collaboration history independently.

## Reproduce

From a checkout with Python 3.10 or newer:

```bash
python3 eval/benchmark_manager.py --messages 10000 --repeats 11
```

Defaults are `--messages 10000 --repeats 7`. A short execution check is:

```bash
python3 eval/benchmark_manager.py --messages 100 --repeats 1
```

The script writes only an automatically removed temporary event log and prints JSON. It does not modify repository Manager state. No network or third-party benchmark package is required.

The baseline reproduces the previous call sequence: reconstruct collaboration state, then call the independently validated task board, which reconstructs that state again. It uses the current unchanged reducers, rather than vendoring a previous package or third-party implementation. Both paths are warmed; their complete return values must compare equal; execution order alternates each round. Timing excludes fixture construction, output comparison, instrumentation and JSON printing. Validation-call counts are measured separately.

## Measured result

- Environment: macOS 26.6, arm64, Python 3.14.7.
- Workload: 2 registered sessions, 10,000 unacknowledged messages; 10,002 events and 4,359,893 bytes. No task history is added to this message-heavy workload.
- Each body contains `Benchmark message ` followed by 100 `x` characters.
- 11 measured rounds per path after warmup. Times below are medians, in milliseconds.
- `sync` includes locked file loading, validation and the returned 50-message page; `directory` starts from an already loaded event list.

| Operation | Before wall | After wall | Wall reduction | Before CPU | After CPU | CPU reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sync` | 274.044 | 200.937 | 26.68% | 230.317 | 171.892 | 25.37% |
| `directory` | 142.680 | 73.230 | 48.68% | 121.702 | 63.962 | 47.44% |

| Collaboration event validation calls | Before | After |
| --- | ---: | ---: |
| `sync` | 30,006 | 20,004 |
| `directory` | 20,004 | 10,002 |

The exact work reduction is independent of timing: directory validation halves, while sync retains storage validation and removes one of its two collaboration replays. Both operations returned equal results in the benchmark.

### Raw samples

Samples are milliseconds in chronological order for each path.

```json
{
  "sync": {
    "before": {
      "wall_ms": [
        508.044,
        280.18,
        226.635,
        226.875,
        292.606,
        221.896,
        251.852,
        274.044,
        206.585,
        291.848,
        336.655
      ],
      "cpu_ms": [
        299.56,
        224.551,
        210.881,
        204.555,
        248.135,
        204.68,
        230.317,
        243.639,
        196.527,
        244.946,
        271.803
      ]
    },
    "after": {
      "wall_ms": [
        472.299,
        312.79,
        174.804,
        260.664,
        223.4,
        213.51,
        141.283,
        164.068,
        144.07,
        163.186,
        200.937
      ],
      "cpu_ms": [
        236.12,
        231.274,
        166.35,
        208.339,
        186.749,
        177.962,
        135.008,
        156.508,
        139.931,
        156.458,
        171.892
      ]
    }
  },
  "directory": {
    "before": {
      "wall_ms": [
        142.68,
        273.292,
        133.513,
        116.243,
        241.484,
        168.615,
        125.614,
        100.02,
        101.089,
        194.184,
        321.32
      ],
      "cpu_ms": [
        127.225,
        226.592,
        121.702,
        109.824,
        146.701,
        137.013,
        114.473,
        97.646,
        98.598,
        113.192,
        175.52
      ]
    },
    "after": {
      "wall_ms": [
        73.23,
        74.038,
        79.088,
        69.035,
        57.681,
        92.05,
        61.313,
        83.032,
        49.977,
        49.375,
        95.538
      ],
      "cpu_ms": [
        69.185,
        66.957,
        69.632,
        63.962,
        52.463,
        75.39,
        52.741,
        60.929,
        49.172,
        48.896,
        73.698
      ]
    }
  }
}
```

## Correctness and scope

Regression tests count collaboration-validation work and cover malformed collaboration/task histories, standalone board validation, pending writes in nested transactions, rollback isolation, and lease/session expiry without appended events. Existing focused tests also cover concurrent task claiming, delayed delivery during waits, multithreaded writers and multiprocess lease competition.

Combined consumers can pass one fixed `now` to the private snapshot helper so owner freshness and lease expiry use the same instant. Task history still validates each transition against its original event timestamp. Normal snapshots continue to recompute current expiry; no event or derived-state cache persists across transactions.

The result applies to this local, message-heavy workload. It is not a hosted-service throughput promise, a universal percentage improvement or a measured end-to-end wait benchmark. File parsing, task replay, path overlap checks and atomic writes remain workload-dependent; large task or lease histories need separate measurement. A preceding isolated-copy cross-check gave 29.4% lower sync wall time and 47.6% lower directory wall time; the primary table records the checked-in reproducible script run, not the fastest observed run.

No event format, public snapshot return shape, mutation authority, file lock or commit mechanism changes. This optimization removes duplicate work within one snapshot; it does not replace the full-log storage model.
