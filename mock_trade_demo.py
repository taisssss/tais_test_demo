#!/usr/bin/env python3
"""
Mock Trade 做市对敲成交 Demo
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


def generate_hmac_signature(access_key: str, secret_key: str, method: str, path: str, body: str = ""):
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

    return {
        "Decode-MM-Auth-Key": access_key,
        "Decode-MM-Auth-Timestamp": timestamp,
        "Decode-MM-Auth-Signature": signature,
        "Content-Type": "application/json"
    }


def mock_trade(account: dict, symbol_id: str, price: str, quantity: str, side: str, is_spot: bool = True):
    """
    调用 Mock Trade 接口
    """
    path = "/api/v1/private/spot/mockTrade" if is_spot else "/api/v1/private/contract/mockTrade"

    body = {
        "symbolId": symbol_id,
        "price": price,
        "quantity": quantity,
        "side": side,
        "clientId": f"mm-{time.strftime('%Y%m%d')}-{int(time.time() * 1000) % 1000000}"
    }

    headers = generate_hmac_signature(
        account["accessKey"],
        account["secretKey"],
        "POST",
        path,
        json.dumps(body)
    )

    print(f"\n{'='*60}")
    print(f"调用接口: {'现货' if is_spot else '合约'} MockTrade")
    print(f"Path: {path}")
    print(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'Content-Type'}, indent=2)}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print("-" * 60)

    response = requests.post(
        f"{BASE_URL}{path}",
        headers=headers,
        json=body,
        verify=False  # 内网证书
    )

    print(f"Status: {response.status_code}")
    
    # 增强错误处理：打印原始响应内容
    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        return response_data
    except json.JSONDecodeError:
        # 如果不是JSON，打印原始文本
        print(f"Response (非JSON): {response.text}")
        print(f"\n⚠️  错误分析:")
        print(f"  - Status 401 通常表示认证失败")
        print(f"  - 可能原因:")
        print(f"    1. 时钟不同步 (需要NTP校时)")
        print(f"    2. accessKey/secretKey 配置错误")
        print(f"    3. 签名算法不匹配")
        print(f"    4. 请求路径错误")
        print(f"  - 当前时间戳: {int(time.time() * 1000)}")
        return {"error": "JSONDecodeError", "raw_text": response.text, "status_code": response.status_code}


def main():
    """主函数"""
    print("=" * 60)
    print("Mock Trade 做市对敲成交 Demo")
    print("=" * 60)
    print(f"\n⚠️  必须使用 api.bifu.internal (做市商内网DNS)")
    print(f"⚠️  时钟同步: ±30s 窗口, 务必 NTP 校时")
    print(f"⚠️  限频: 10/s/账户")

    # 检查时钟同步
    current_timestamp = int(time.time() * 1000)
    print(f"\n当前时间戳: {current_timestamp}")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ============ 现货测试 ============
    print("\n\n" + "=" * 60)
    print("【现货测试】BTC-USDT")
    print("=" * 60)

    result = mock_trade(
        account=SPOT_ACCOUNT,
        symbol_id="10000001",  # BTC-USDT
        price="67000.5",
        quantity="0.01",
        side="BUY",
        is_spot=True
    )

    # ============ 合约测试 ============
    print("\n\n" + "=" * 60)
    print("【合约测试】BTC-USDT 永续")
    print("=" * 60)

    result2 = mock_trade(
        account=CONTRACT_ACCOUNT,
        symbol_id="10000001",  # BTC-USDT 永续
        price="67000.5",
        quantity="0.01",
        side="BUY",
        is_spot=False
    )

    # ============ 价格保护测试 ============
    print("\n\n" + "=" * 60)
    print("【价格保护测试】故意传低价，看是否被钳制")
    print("=" * 60)

    result3 = mock_trade(
        account=SPOT_ACCOUNT,
        symbol_id="10000001",
        price="67000",  # 低于买一，应被上修
        quantity="0.01",
        side="BUY",
        is_spot=True
    )

    print("\n\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n验证步骤:")
    print("1. 公网行情WS应收到成交推送 (tradeId, executedPrice)")
    print("2. K线应更新 (OHLC + 成交量)")
    print("3. 做市账户应无任何成交/订单/持仓记录")


if __name__ == "__main__":
    main()
