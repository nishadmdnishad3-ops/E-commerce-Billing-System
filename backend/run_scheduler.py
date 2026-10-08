"""
Native Recurring Billing Scheduler Daemon (Runs without Docker)
Checks the database schedule hourly and executes `manage.py auto_generate_bills`.

Usage:
    python run_scheduler.py

Alternatively, you can configure system-level scheduling:
- Linux / VPS: crontab -e
    0 0 * * * cd /path/to/backend && /path/to/venv/bin/python manage.py auto_generate_bills >> /var/log/billing.log 2>&1
- Windows: Windows Task Scheduler calling `python manage.py auto_generate_bills`
"""

import os
import sys
import time
import subprocess
from datetime import datetime

CHECK_INTERVAL_SECONDS = 3600  # Check hourly


def run_scheduler():
    manage_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manage.py")
    python_exe = sys.executable

    print("=" * 60)
    print("Billing Auto-Generation Native Scheduler Daemon (No Docker)")
    print(f"Polling schedule every {CHECK_INTERVAL_SECONDS // 60} minutes.")
    print("Press Ctrl+C to exit.")
    print("=" * 60)

    while True:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{now_str}] Executing schedule check...")
        try:
            res = subprocess.run(
                [python_exe, manage_py, "auto_generate_bills"],
                capture_output=True,
                text=True,
            )
            if res.stdout:
                print(res.stdout.strip())
            if res.stderr:
                print(f"[{now_str}] STDERR: {res.stderr.strip()}")
        except Exception as ex:
            print(f"[{now_str}] Scheduler invocation error: {ex}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\nScheduler daemon stopped by user.")
