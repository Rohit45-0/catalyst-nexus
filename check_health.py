
import requests
import time

def check_health():
    url = "http://localhost:8000/docs"
    try:
        print(f"Pinging {url}...")
        resp = requests.get(url, timeout=5)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("Backend is UP.")
        else:
            print("Backend is ERROR.")
    except Exception as e:
        print(f"Backend is DOWN. Error: {e}")

if __name__ == "__main__":
    check_health()
