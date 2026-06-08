# Re-runs the P0 engine on an interval so data.json stays fresh (real-time-ish).
import subprocess, sys, time, datetime, os

INTERVAL = 120  # seconds between refreshes
HERE = os.path.dirname(os.path.abspath(__file__))

while True:
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "build_data.py"], cwd=HERE,
                           capture_output=True, text=True, timeout=110)
        tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        print("[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), tail), flush=True)
        if r.returncode != 0:
            print("  stderr:", (r.stderr or "")[-300:], flush=True)
    except Exception as e:
        print("[%s] update error: %r" % (datetime.datetime.now().strftime("%H:%M:%S"), e), flush=True)
    dt = time.time() - t0
    time.sleep(max(5, INTERVAL - dt))
