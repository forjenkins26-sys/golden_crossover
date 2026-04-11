#!/usr/bin/env python3
"""Test script to find correct Delta Exchange leverage endpoint"""

import requests
import hmac
import hashlib
import time
from datetime import datetime
import json
import sys

# Config
API_KEY = "aMpcVoWFDJNpGGb2QYJKp2ZrljalU4"
API_SECRET = "ypj0WNDEOaQ4WNyx4fLidxde0Ba0Uo4iKI5HYes7Q46XtkPSDs1Wami1zDIH"
BASE_URL = "https://cdn-ind.testnet.deltaex.org"
PRODUCT_ID = 27

def get_timestamp():
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)

def create_signature(timestamp, method, path, body_str=""):
    """Create HMAC SHA256 signature for Delta Exchange API"""
    message = f"t={timestamp}\nm={method}\np={path}\nb={body_str}"
    signature = hmac.new(
        API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

def make_request(method, path, body=None):
    """Make API request with proper authentication"""
    timestamp = get_timestamp()
    url = f"{BASE_URL}{path}"
    
    body_str = json.dumps(body) if body else ""
    signature = create_signature(timestamp, method, path, body_str)
    
    headers = {
        "api-key": API_KEY,
        "signature": signature,
        "timestamp": str(timestamp),
        "Content-Type": "application/json"
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: {method} {path}")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    if body:
        print(f"Body: {json.dumps(body, indent=2)}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=body, headers=headers, timeout=10)
        else:
            print(f"Unsupported method: {method}")
            return None
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

# Test different endpoints
print("\n[TEST 1] Original endpoint - /v2/products/{PRODUCT_ID}/orders/leverage")
make_request("POST", f"/v2/products/{PRODUCT_ID}/orders/leverage", {"leverage": "10"})

print("\n\n[TEST 2] Alternative - /v2/orders/leverage with product_id in body")
make_request("POST", "/v2/orders/leverage", {"product_id": PRODUCT_ID, "leverage": "10"})

print("\n\n[TEST 3] Alternative - /v2/products/{PRODUCT_ID}/leverage")
make_request("POST", f"/v2/products/{PRODUCT_ID}/leverage", {"leverage": "10"})

print("\n\n[TEST 4] Get products to verify PRODUCT_ID")
make_request("GET", "/v2/products")

print("\n\n[TEST 5] Get positions to verify product_id format")
make_request("GET", "/v2/positions", {"product_id": PRODUCT_ID})
