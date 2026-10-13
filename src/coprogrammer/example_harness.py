"""Deterministic protocol fixture, not an AI model or production coding agent.

Use only in a disposable project with a task covering docs/**. Real harnesses
replace this program while keeping the stdin/response contract.
"""
import json
import sys
from pathlib import Path


def main():
    # JSON bytes are UTF-8 regardless of the client's Windows/terminal locale.
    packet = json.load(sys.stdin.buffer)
    if packet.get("format") != "coprogrammer.harness-task.v1":
        raise SystemExit("Expected a harness protocol fixture packet")
    if packet["kind"] == "inbox":
        print(json.dumps({"status": "received", "summary": "Fixture received the delivered message records",
                          "acknowledge": [message["id"] for message in packet["messages"]]}))
        return
    directory = Path("docs")
    directory.mkdir(exist_ok=True)
    (directory / "runner-fixture.txt").write_text("Deterministic harness protocol fixture. No AI model was invoked.\n", encoding="utf-8")
    print(json.dumps({"status": "done", "summary": "Created the deterministic docs fixture"}))


if __name__ == "__main__":
    main()
