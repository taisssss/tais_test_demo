#!/usr/bin/env python3
"""
Mock Trade 做市对敲成交 Demo1
接入入口: api.bifu.internal (做市商内网DNS)
"""

import hashlib
import hmac
import time
import requests
import json

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
    """
    生成 HMAC 签名
    signMessage = <requestURI> + "|" + <timestamp>
    signature = HMAC_SHA256(key=secretKey, message=signMessage) // 输出小写 hex
    """
    timestamp = str(int(time.time() * 1000))
    sign_message = f"{path}|{timestamp}"

    signature = hmac.new(
        secret_key.encode('utf-8'),
        sign_message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return timestamp, signature


def mock_trade(account: dict, symbol_id: str, price: str, quantity: str, side: str, is_spot: bool = True):
    """
    调用 Mock Trade 接口
    """
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

    # 打印 curl 命令
    curl_cmd = (
        f"curl -sS -X POST '{BASE_URL}{path}' "
        f"-H 'Content-Type: application/json' "
        f"-H 'Decode-MM-Auth-Access-Key: {account[\"accessKey\"]}' "
        f"-H 'Decode-MM-Auth-Timestamp: {ts}' "
        f"-H 'Decode-MM-Auth-Signature: {sig}' "
        f"-d '{json.dumps(body)}' "
        f"-k"
    )

    print(f"\n{'='*60}")
    print(f"调用接口: {'现货' if is_spot else '合约'} MockTrade")
    print(f"Path: {path}")
    print(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'Content-Type'}, indent=2)}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print("-" * 60)
    print(f"\n[CURL 命令]:")
    print(curl_cmd)
    print("-" * 60)

    response = requests.post(
        f"{BASE_URL}{path}",
        headers=headers,
        json=body,
        verify=False,  # 内网证书
        timeout=10
    )

    print(f"\nStatus: {response.status_code}")

    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        return response_data
    except json.JSONDecodeError:
        print(f"Response (非JSON): {response.text}")
        return {"error": "JSONDecodeError", "raw_text": response.text, "status_code": response.status_code}


def main():
    """主函数"""
    print("=" * 60)
    print("Mock Trade 做市对敲成交 - BCH/USDT")
    print("=" * 60)
    print(f"\n⚠️  必须使用 api.bifu.internal (做市商内网DNS)")
    print(f"⚠️  时钟同步: ±30s 窗口, 务必 NTP 校时")
    print(f"⚠️  限频: 10/s/账户")

    current_timestamp = int(time.time() * 1000)
    print(f"\n当前时间戳: {current_timestamp}")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ============ 现货测试 BCH/USDT ============
    result = mock_trade(
        account=SPOT_ACCOUNT,
        symbol_id="90000013",
        price="400",
        quantity="0.100",
        side="BUY",
        is_spot=True
    )

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
