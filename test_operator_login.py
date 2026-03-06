import asyncio
import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError

API_URL = "https://sendmax11-production.up.railway.app"

def test_login():
    url = f"{API_URL}/auth/operator/login"
    data = {"email": "jeimary@gmail.com", "password": "Jeima3067"}
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            print(f"SUCCESS: {body}")
            return json.loads(body)["access_token"]
    except HTTPError as e:
        print(f"ERROR: {e.code} - {e.read().decode('utf-8')}")
def test_wallet(token):
    print("\n--- Testing Wallet Summary ---")
    req = urllib.request.Request(f"{API_URL}/api/operators/wallet/summary", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"WALLET OK: {resp.read().decode('utf-8')[:200]}")
    except HTTPError as e:
        print(f"WALLET ERROR: {e.code} - {e.read().decode('utf-8')}")
        
    print("\n--- Testing Wallet Withdrawals ---")
    req = urllib.request.Request(f"{API_URL}/api/operators/wallet/withdrawals", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"WITHDRAWALS OK: {resp.read().decode('utf-8')[:200]}")
    except HTTPError as e:
        print(f"WITHDRAWALS ERROR: {e.code} - {e.read().decode('utf-8')}")

def test_orders(token):
    print("\n--- Testing Orders ---")
    req = urllib.request.Request(f"{API_URL}/api/operators/orders?limit=10", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"ORDERS OK: {resp.read().decode('utf-8')[:200]}")
    except HTTPError as e:
        print(f"ORDERS ERROR: {e.code} - {e.read().decode('utf-8')}")

if __name__ == "__main__":
    token = test_login()
    if token:
        test_wallet(token)
        test_orders(token)
