"""
Run TraceHealth's periodic jobs in their own process (production).

Every JOBS_INTERVAL_SECONDS it sends due payouts, expires M-Pesa requests that
never got a result, and retries push/SMS deliveries left PENDING.

In development the API runs these jobs itself (BACKGROUND_JOBS_ENABLED=true).
In production the API runs several worker processes, so the jobs are switched
off there and run ONCE, here, so that two processes never pick up the same
delivery at the same moment (decision D46).

    python -m scripts.run_jobs
"""

import logging
import signal
import sys
import threading

from app.core.background import get_payout_processor
from app.core.config import get_settings

log = logging.getLogger("tracehealth.jobs")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    interval = get_settings().JOBS_INTERVAL_SECONDS
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    log.info("Periodic jobs started (every %s s)", interval)
    while not stop.is_set():
        try:
            get_payout_processor().run_periodic_jobs()
        except Exception:
            log.exception("Periodic jobs failed; will try again")
        stop.wait(interval)
    log.info("Periodic jobs stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
