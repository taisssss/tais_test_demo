#!/usr/bin/env python3
"""
Mock Trade 做市对敲成交 Demo - pytest 格式
接入入口: api.bifu.internal (做市商内网DNS)

运行方式:
    pytest mock_trade_demo.py -v
    pytest mock_trade_demo.py -v -s  # 显示 print 输出
    pytest mock_trade_demo.py -v -k "spot"  # 只运行现货测试
    pytest mock_trade_demo.py -v -k "contract"  # 只运行合约测试
"""

import hashlib
import hmac
import time
import requests
import json
import pytest

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
    access_key = account["accessKey"]
    curl_cmd = (
        f"curl -sS -X POST '{BASE_URL}{path}' "
        f"-H 'Content-Type: application/json' "
        f"-H 'Decode-MM-Auth-Access-Key: {access_key}' "
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

    try:
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
    except Exception as e:
        print(f"\n⚠️  请求失败: {e}")
        print(f"⚠️  请使用上方 CURL 命令在服务器上执行")
        return {"error": str(e)}


# ============ Pytest Fixtures ============

@pytest.fixture(scope="session")
def base_url():
    """基础 URL fixture"""
    return BASE_URL


@pytest.fixture(scope="session")
def spot_account():
    """现货账户 fixture"""
    return SPOT_ACCOUNT


@pytest.fixture(scope="session")
def contract_account():
    """合约账户 fixture"""
    return CONTRACT_ACCOUNT


@pytest.fixture(scope="session", autouse=True)
def print_test_header():
    """自动打u额印测试开始信息"""
    print("\n" + "=" * 60)
    print("Mock Trade 做市对敲成交 - BCH/USDT Pytest 测试")
    print("=" * 60)
    print(f"\n⚠️  必须使用 api.bifu.internal (做市商内网DNS)")
    print(f"⚠️  时钟同步: ±30s 窗口, 务必 NTP 校时")
    print(f"⚠️  限频: 10/s/账户")
    current_timestamp = int(time.time() * 1000)
    print(f"\n当前时间戳: {current_timestamp}")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")


# ============ 合约真实下单 ============

def create_contract_order(account: dict, symbol: str, contract_id: str, price: str, size: str, side: str, position_side: str = "LONG"):
    """
    调用合约真实下单接口
    """
    path = "/api/v1/private/contract/order/createOrder"
    ts, sig = generate_hmac_signature(account["accessKey"], account["secretKey"], path)

    body = {
        "price": price,
        "size": size,
        "type": "LIMIT",
        "timeInForce": "GOOD_TIL_CANCEL",
        "reduceOnly": False,
        "isPositionTpsl": False,
        "accountId": str(account["accountId"]),
        "contractId": contract_id,
        "side": side,
        "triggerPrice": "",
        "triggerPriceType": "LAST_PRICE",
        "extraType": "",
        "extraDataJson": "",
        "symbol": symbol,
        "marginMode": "SHARED",
        "separatedMode": "COMBINED",
        "separatedOpenOrderId": "0",
        "positionSide": position_side,
        "clientOrderId": str(int(time.time() * 1000)),
        "isSetOpenTp": False,
        "isSetOpenSl": False,
        "orderSide": side,
        "orderSource": "WEB"
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
        f"-H 'Decode-MM-Auth-Access-Key: {account['accessKey']}' "
        f"-H 'Decode-MM-Auth-Timestamp: {ts}' "
        f"-H 'Decode-MM-Auth-Signature: {sig}' "
        f"-d '{json.dumps(body)}' "
        f"-k"
    )

    print(f"\n{'='*60}")
    print(f"调用接口: 合约真实下单")
    print(f"Path: {path}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print("-" * 60)
    print(f"\n[CURL 命令]:")
    print(curl_cmd)
    print("-" * 60)

    try:
        response = requests.post(
            f"{BASE_URL}{path}",
            headers=headers,
            json=body,
            verify=False,
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
    except Exception as e:
        print(f"\n⚠️  请求失败: {e}")
        return {"error": str(e)}


# ============ Pytest 测试用例 ============

class TestMockTrade:
    """Mock Trade 测试类"""

    def test_spot_mock_trade_buy(self, spot_account, base_url):
        """
        测试现货买入
        symbol: BCH/USDT (90000013)
        """
        result = mock_trade(
            account=spot_account,
            symbol_id="90000013",
            price="400",
            quantity="0.100",
            side="BUY",
            is_spot=True
        )

        # 断言：检查返回结果
        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("statusCode") == 0, f"业务状态码错误: {result.get('statusCode')}"

    def test_spot_mock_trade_sell(self, spot_account, base_url):
        """
        测试现货卖出
        symbol: BCH/USDT (90000013)
        """
        result = mock_trade(
            account=spot_account,
            symbol_id="90000013",
            price="400",
            quantity="0.100",
            side="SELL",
            is_spot=True
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("statusCode") == 0, f"业务状态码错误: {result.get('statusCode')}"

    def test_contract_mock_trade_buy(self, contract_account, base_url):
        """
        测试合约买入
        symbol: BCH/USDT
        """
        result = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price="400",
            quantity="0.100",
            side="BUY",
            is_spot=False
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("statusCode") == 0, f"业务状态码错误: {result.get('statusCode')}"

    def test_contract_mock_trade_sell(self, contract_account, base_url):
        """
        测试合约卖出
        symbol: BCH/USDT
        """
        result = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price="400",
            quantity="0.100",
            side="SELL",
            is_spot=False
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("statusCode") == 0, f"业务状态码错误: {result.get('statusCode')}"

    def test_signature_generation(self):
        """测试签名生成是否正确"""
        ts, sig = generate_hmac_signature("test_key", "test_secret", "/test/path")
        
        assert ts is not None and len(ts) > 0, "时间戳不能为空"
        assert sig is not None and len(sig) == 64, "签名长度应该为64位(hex)"


class TestContractRealOrder:
    """合约真实下单测试类"""

    def test_contract_create_order_buy_long(self, contract_account, base_url):
        """
        测试合约真实下单 - 买入做多
        symbol: BCHUSDT, contractId: 10000011
        """
        result = create_contract_order(
            account=contract_account,
            symbol="BCHUSDT",
            contract_id="10000011",
            price="400.00",
            size="1.000",
            side="BUY",
            position_side="LONG"
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("statusCode") == 0, f"业务状态码错误: {result.get('statusCode')}"

    def test_contract_create_order_sell_short(self, contract_account, base_url):
        """
        测试合约真实下单 - 卖出做空
        symbol: BCHUSDT, contractId: 10000011
        """
        result = create_contract_order(
            account=contract_account,
            symbol="BCHUSDT",
            contract_id="10000011",
            price="400.00",
            size="1.000",
            side="SELL",
            position_side="SHORT"
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("statusCode") == 0, f"业务状态码错误: {result.get('statusCode')}"


# ============ 便捷运行入口 ============


if __name__ == "__main__":
    import sys
    # 如果直接运行，调用 pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))
