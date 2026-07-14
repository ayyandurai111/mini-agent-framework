import subprocess
import sys


def install_browser():
    try:
        import playwright
    except ImportError:
        print("playwright not found. Install: pip install mini_agent[browser]")
        sys.exit(1)
    print("Installing Playwright Chromium browser...")
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("Chromium installed successfully.")
    else:
        print(f"Failed:\n{result.stderr}")
        sys.exit(1)
