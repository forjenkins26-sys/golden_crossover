#!/usr/bin/env python3
"""Test script to find how to get/set leverage on Delta Exchange"""

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

def make_request(method, path, body=None, params=None):
    """Make API request with proper authentication"""
    timestamp = get_timestamp()
    
    body_str = json.dumps(body) if body else ""
    signature = create_signature(timestamp, method, path, body_str)
    
    headers = {
        "api-key": API_KEY,
        "signature": signature,
        "timestamp": str(timestamp),
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=body, headers=headers, timeout=10)
        else:
            return None
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

# Test getting account info to see leverage settings
print("\n[TEST 1] Get account info")
resp = make_request("GET", "/v2/account")
if resp:
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"Error: {resp.text[:500]}")

print("\n\n[TEST 2] Get positions to see leverage")
resp = make_request("GET", "/v2/positions")
if resp:
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2)[:1500])
    else:
        print(f"Error: {resp.text[:500]}")

print("\n\n[TEST 3] Try simpler position query with product_id in path")
resp = make_request("GET", f"/v2/positions/{PRODUCT_ID}")
if resp:
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2)[:1500])
    else:
        print(f"Error: {resp.text[:500]}")

print("\n\n[TEST 4] Get all products and find leverage settings for BTCUSD")
resp = make_request("GET", "/v2/products")
if resp and resp.status_code == 200:
    data = resp.json()
    products = data.get('result', [])
    # Find BTCUSD
    for p in products:
        if p.get('symbol') == 'BTCUSD':
            print(f"Found BTCUSD: ")
            print(json.dumps(p, indent=2)[:2000])
            break
