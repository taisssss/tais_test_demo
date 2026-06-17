#!/usr/bin/env python3
"""
Mock Trade 简单下单脚本
支持自定义参数：价格、数量、方向、合约/现货

运行方式:
    python3 mock_trade_simple.py --price 400 --quantity 1.0 --side BUY --type spot
    python3 mock_trade_simple.py --price 400 --quantity 1.0 --side BUY --type contract
    
    # 合约现货一起下单
    python3 mock_trade_simple.py --price 400 --quantity 1.0 --side BUY --type both
"""

import hashlib
import hmac
import time
import requests
import json
import argparse

# ============ 配置 ============
BASE_URL = "https://api.bifu.internal"

# 现货做市商账号
SPOT_ACCOUNT = {
    "accountId": 759059903846286328,
    "userId": 120959881308071,
    "accessKey": "spot_BCHUSDT_120959881308071",
    "secretKey": "gpffu3mb316XCbG0C438XmqwIiAPUEJ",
    "accountType": 1
}

# 合约做市商账号
CONTRACT_ACCOUNT = {
    "accountId": 759060249113002370,
    "userId": 110453576777325,
    "accessKey": "contract_110453576777325",
    "secretKey": "OIX7owApfUIwvb2v4V1PVTO2739sUXV",
    "accountType": 0
}


def generate_hmac_signature(access_key: str, secret_key: str, path: str):
    """生成 HMAC 签名"""
    timestamp = str(int(time.time() * 1000))
    sign_message = f"{path}|{timestamp}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        sign_message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return timestamp, signature


def mock_trade(account: dict, symbol_id: str, price: str, quantity: str, side: str, is_spot: bool = True):
    """调用 Mock Trade 接口"""
    path = "/api/v1/private/spot/mockTrade" if is_spot else "/api/v1/private/contract/mockTrade"
    ts, sig = generate_hmac_signature(account["accessKey"], account["secretKey"], path)

    body = {
        "symbolId": symbol_id,
        "price": price,
        "quantity": quantity,
        "side": side,
        "clientId": f"mm-{time.strftime('%Y%m%d')}-{int(time.time() * 1000) % 1000000}"
    }

    headers = {
        "Content-Type": "application/json",
        "Decode-MM-Auth-Access-Key": account["accessKey"],
        "Decode-MM-Auth-Timestamp": ts,
        "Decode-MM-Auth-Signature": sig,
    }

    # 打印请求信息
    print(f"\n{'='*60}")
    print(f"📌 {'现货' if is_spot else '合约'} MockTrade")
    print(f"{'='*60}")
    print(f"URL: {BASE_URL}{path}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print("-" * 60)
    
    # 生成 CURL 命令
    curl_cmd = (
        f"curl -sS -X POST '{BASE_URL}{path}' "
        f"-H 'Content-Type: application/json' "
        f"-H 'Decode-MM-Auth-Access-Key: {account['accessKey']}' "
        f"-H 'Decode-MM-Auth-Timestamp: {ts}' "
        f"-H 'Decode-MM-Auth-Signature: {sig}' "
        f"-d '{json.dumps(body)}' "
        f"-k"
    )
    print(f"[CURL]:\n{curl_cmd}")
    print("-" * 60)

    # 发送请求
    try:
        response = requests.post(
            f"{BASE_URL}{path}",
            headers=headers,
            json=body,
            verify=False,
            timeout=10
        )
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("code") == "SUCCESS":
                data = result.get("data", {})
                print(f"\n✅ {'现货' if is_spot else '合约'}成交成功!")
                print(f"   tradeId: {data.get('tradeId', 'N/A')}")
                print(f"   价格: {data.get('executedPrice', price)}")
                print(f"   数量: {data.get('quantity', quantity)}")
                print(f"   方向: {data.get('side', side)}")
                return result
            else:
                print(f"\n❌ 业务错误: {result.get('code')} - {result.get('msg')}")
                return result
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"   {response.text}")
            return {"error": f"HTTP {response.status_code}", "text": response.text}
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        print(f"\n请使用上方 CURL 命令在服务器上手动执行测试")
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Mock Trade 简单下单脚本")
    parser.add_argument("--price", "-p", required=True, help="价格")
    parser.add_argument("--quantity", "-q", required=True, help="数量")
    parser.add_argument("--side", "-s", required=True, choices=["BUY", "SELL"], help="方向: BUY 或 SELL")
    parser.add_argument("--type", "-t", required=True, choices=["spot", "contract", "both"], 
                        help="类型: spot(现货) / contract(合约) / both(合约+现货)")
    
    args = parser.parse_args()
    
    print(f"\n{'#'*60}")
    print(f"# Mock Trade 下单参数")
    print(f"{'#'*60}")
    print(f"  价格: {args.price}")
    print(f"  数量: {args.quantity}")
    print(f"  方向: {args.side}")
    print(f"  类型: {args.type}")
    print(f"{'#'*60}")
    
    if args.type == "spot":
        # 现货: BCH/USDT -> 90000013
        print(f"\n📍 执行现货下单 (symbolId: 90000013)")
        mock_trade(SPOT_ACCOUNT, "90000013", args.price, args.quantity, args.side, is_spot=True)
        
    elif args.type == "contract":
        # 合约: BCH/USDT -> 10000011
        print(f"\n📍 执行合约下单 (symbolId: 10000011)")
        mock_trade(CONTRACT_ACCOUNT, "10000011", args.price, args.quantity, args.side, is_spot=False)
        
    elif args.type == "both":
        # 合约 + 现货
        print(f"\n📍 执行合约+现货下单")
        print(f"\n{'='*60}")
        print(f"🔵 第一笔: 合约 (symbolId: 10000011)")
        print(f"{'='*60}")
        result1 = mock_trade(CONTRACT_ACCOUNT, "10000011", args.price, args.quantity, args.side, is_spot=False)
        
        print(f"\n{'='*60}")
        print(f"🟢 第二笔: 现货 (symbolId: 90000013)")
        print(f"{'='*60}")
        result2 = mock_trade(SPOT_ACCOUNT, "90000013", args.price, args.quantity, args.side, is_spot=True)
        
        # 汇总
        print(f"\n{'='*60}")
        print(f"📊 下单汇总")
        print(f"{'='*60}")
        print(f"  合约: {'✅ 成功' if result1.get('code') == 'SUCCESS' else '❌ 失败'}")
        print(f"  现货: {'✅ 成功' if result2.get('code') == 'SUCCESS' else '❌ 失败'}")
        
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
