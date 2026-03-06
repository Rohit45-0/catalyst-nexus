
import requests
import sys

def check():
    try:
        resp = requests.get("http://localhost:8000/docs", timeout=10)
        status = f"UP ({resp.status_code})"
    except Exception as e:
        status = f"DOWN ({e})"
    
    with open("health_status.txt", "w") as f:
        f.write(status)

if __name__ == "__main__":
    check()
