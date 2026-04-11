# -*- coding: utf-8 -*-
import requests
import hmac
import hashlib
import time
import sys
import json
sys.path.insert(0, '.')
from config import DEMO_API_KEY, DEMO_API_SECRET, DEMO_BASE_URL

def generate_signature(secret, message):
    """Generate HMAC SHA256 signature"""
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    hash_obj = hmac.new(secret, message, hashlib.sha256)
    return hash_obj.hexdigest()

def make_authenticated_request(method, path, query_params=None):
    """Make authenticated request to Delta Exchange API"""
    timestamp = str(int(time.time()))
    signature_data = method + timestamp + path
    signature = generate_signature(DEMO_API_SECRET, signature_data)
    
    headers = {
        'api-key': DEMO_API_KEY,
        'signature': signature,
        'timestamp': timestamp,
        'Content-Type': 'application/json'
    }
    
    url = f"{DEMO_BASE_URL}{path}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=query_params, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=query_params, timeout=10)
        else:
            response = requests.request(method, url, headers=headers, json=query_params, timeout=10)
        
        return response
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def test_connection():
    """Test connection to Delta Exchange demo API with debugging"""
    
    print("\n" + "="*70)
    print("DELTA EXCHANGE TESTNET CONNECTION TEST")
    print("="*70)
    print(f"Base URL: {DEMO_BASE_URL}")
    print(f"API Key: {DEMO_API_KEY[:10]}... (hidden)")
    
    # TEST 1: List all available products
    print("\n" + "="*70)
    print("TEST 1: Listing all available products from /v2/products")
    print("="*70)
    
    response = make_authenticated_request("GET", "/v2/products")
    
    if response is None:
        print("❌ FAILED: Could not connect to API")
        return
    
    print(f"HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('success'):
                products = data.get('result', [])
                print(f"✅ SUCCESS! Found {len(products)} available products")
                print("\n📋 First 10 symbols:")
                for i, product in enumerate(products[:10], 1):
                    symbol = product.get('symbol', 'N/A')
                    contract_type = product.get('contract_type', 'N/A')
                    state = product.get('state', 'N/A')
                    print(f"  {i}. {symbol:15} | Type: {contract_type:20} | State: {state}")
                
                # Find BTC perpetual
                btc_perp = None
                for product in products:
                    if product.get('symbol') == 'BTCUSD' and product.get('contract_type') == 'perpetual_futures':
                        btc_perp = product
                        break
                
                if btc_perp:
                    print(f"\n🎯 Found BTC Perpetual: BTCUSD")
                else:
                    print(f"\n❌ BTC perpetual (BTCUSD) not found in products list")
                    print("   Available symbols:", [p.get('symbol') for p in products[:5]])
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.text[:200]}")
    else:
        print(f"❌ FAILED with status {response.status_code}")
        print(f"Response: {response.text[:300]}")
    
    # TEST 2: Get BTCUSD ticker price
    print("\n" + "="*70)
    print("TEST 2: Fetching BTCUSD ticker price from /v2/tickers/BTCUSD")
    print("="*70)
    
    response = make_authenticated_request("GET", "/v2/tickers/BTCUSD")
    
    if response is None:
        print("❌ FAILED: Could not connect to API")
        return
    
    print(f"HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('success'):
                ticker = data.get('result', {})
                symbol = ticker.get('symbol', 'N/A')
                mark_price = ticker.get('mark_price', 'N/A')
                close = ticker.get('close', 'N/A')
                high = ticker.get('high', 'N/A')
                low = ticker.get('low', 'N/A')
                
                print(f"\n✅ SUCCESS! BTCUSD Ticker Data:")
                print(f"  Symbol:     {symbol}")
                print(f"  Mark Price: ${mark_price}")
                print(f"  Close:      ${close}")
                print(f"  24h High:   ${high}")
                print(f"  24h Low:    ${low}")
                return True
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.text[:200]}")
    else:
        print(f"❌ FAILED with status {response.status_code}")
        print(f"Response: {response.text[:300]}")
    
    return False

if __name__ == "__main__":
    success = test_connection()
    print("\n" + "="*70)
    if success:
        print("✅ CONNECTION TEST PASSED - Ready to deploy bot!")
    else:
        print("❌ CONNECTION TEST FAILED - Fix errors above before deploying")
    print("="*70)
