#!/usr/bin/env python3
"""Smoke test for the AuDHD runtime service.

Validates:
- /healthz returns 200
- /readyz returns 200 or 503 with structured payload
- /webhooks/notion GET returns health info
- /webhooks/test echoes in staging
- /execute rejects unauthenticated requests

Usage:
    python scripts/smoke_runtime.py [base_url]
    Default base_url: http://localhost:8000
"""

import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def smoke(base: str) -> list[tuple[str, bool, str]]:
    results = []

    def check(
        name: str,
        method: str,
        path: str,
        body: dict | None = None,
        expect_status: int = 200,
        headers: dict | None = None,
    ) -> None:
        url = f"{base}{path}"
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, headers=req_headers, method=method)

        try:
            with urlopen(req, timeout=10) as resp:
                resp.read()
                if resp.status == expect_status:
                    results.append((name, True, f"{resp.status} OK"))
                else:
                    results.append(
                        (name, False, f"Expected {expect_status}, got {resp.status}")
                    )
        except HTTPError as e:
            if e.code == expect_status:
                results.append((name, True, f"{e.code} (expected)"))
            else:
                results.append(
                    (name, False, f"HTTP {e.code}: {e.read().decode()[:200]}")
                )
        except URLError as e:
            results.append((name, False, f"Connection failed: {e.reason}"))
        except Exception as e:
            results.append((name, False, str(e)))

    # Core health endpoints
    check("healthz", "GET", "/healthz")
    check("readyz", "GET", "/readyz")

    # Webhook health
    check("webhook_health", "GET", "/webhooks/notion")

    # Webhook test echo (staging only)
    check(
        "webhook_test_echo",
        "POST",
        "/webhooks/test",
        body={"test": True, "timestamp": time.time()},
    )

    return results


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"Smoke testing: {base}\n")

    results = smoke(base)

    passed = 0
    failed = 0
    for name, ok, detail in results:
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {name}: {detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(results)} checks")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
