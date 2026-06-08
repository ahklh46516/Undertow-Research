"""Re-run the pipeline on an interval so ``web/data.json`` stays fresh.

Run with ``python -m engine.live_update``. On a transient failure it keeps the last
good snapshot and retries next cycle. For production, prefer the scheduled GitHub
Action (``.github/workflows/refresh-data.yml``) over a long-lived local loop.
"""

import time
import datetime
import traceback

from .pipeline import run

INTERVAL = 120  # seconds between refreshes


def main():
    while True:
        started = time.time()
        try:
            d = run()
            print("[%s UTC] index=%s regime=%s rho=%.2f"
                  % (datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
                     d["index"], d["regime"], d["rho_bar"]), flush=True)
        except Exception:  # noqa: BLE001 - keep the loop alive across failures
            print("[%s UTC] update failed:" % datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
                  flush=True)
            traceback.print_exc()
        time.sleep(max(5, INTERVAL - (time.time() - started)))


if __name__ == "__main__":
    main()
