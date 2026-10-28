"""Независимые ожидания: транспортный ACK не превращается в свидетельство воздействия."""
LEVELS = [2, 3, 3, 2, 3, 2]

def assess(data):
    checks = []
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
    check("six consumed inputs", data.get("consumption") == [
        dict(raw=p, active=p & 1, neighbour=1, samples=i+1) for i, p in enumerate(LEVELS)])
    check("RO refused before transport", data.get("refusal") == {"code": "write_denied", "callbacks": 0})
    check("reason does not grant access", data.get("reason_refusal") == {"code": "write_denied", "callbacks": 0})
    check("override needs reason", data.get("missing_reason", {}).get("callbacks") == 0
          and data.get("missing_reason", {}).get("refused") is True)
    ack = data.get("ack", {})
    check("ACK without verification", ack.get("acknowledged") is True and ack.get("verified") is False)
    check("one ignored write", data.get("override_callbacks") == [dict(
        direction="W", width=4, offset=0, value=3, before=2, after=2, generation=1, ignored=True)])
    callbacks = data.get("cpu_callbacks", [])
    check("one peripheral read per firmware sample", len(callbacks) == 6 and all(
        rows == [dict(direction="R", width=4, offset=0, value=pins, before=pins, after=pins,
                      generation=i+1, ignored=False)] for i, (rows, pins) in enumerate(zip(callbacks, LEVELS))))
    check("override reason captured", data.get("override_audit") is True)
    check("whole snapshot", data.get("snapshot", {}).get("bytes") == 16)
    check("intended exception", data.get("interruption") == "intentional interruption before resume")
    check("readback unchanged", data.get("readback") == 2)
    check("false claim stays FAIL", data.get("negative_control") == {
        "status": "FAIL", "claim": "override forces input high", "expected": 1, "actual": 0})
    check("normal restoration", data.get("restoration") == {"memory": True, "input": True})
    check("exception restoration", data.get("exception_restoration") == {"memory": True, "input": True})
    check("model boundary", data.get("scope") == "modeled-gpio-not-electrical")
    return checks
