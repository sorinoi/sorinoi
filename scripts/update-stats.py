
from datetime import datetime, timezone

GITHUB_USERNAME = "sorinoi"

def main():
    print(f"Updating GitHub stats for {GITHUB_USERNAME}")
    print(f"UTC: {datetime.now(timezone.utc).isoformat()}")

if __name__ == "__main__":
    main()
