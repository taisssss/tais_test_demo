#!/usr/bin/env python3
"""
Mock Trade 做市对敲成交 Demo - pytest 格式
接入入口: api.bifu.internal (做市商内网DNS)
注意：本文件所有请求都需要用mock_trade 方法

运行方式:
    cd tais/tais_test_demo/ && git pull
    pytest mock_trade_demo.py -vvvvv -s
    pytest mock_trade_demo.py -vvvvv -s  # 显示 print 输出
    pytest mock_trade_demo.py -vvvvv -k "spot"  # 只运行现货测试
    pytest mock_trade_demo.py -vvvvv -k "contract"  # 只运行合约测试
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
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"

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
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"

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
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"

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
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"

    def test_signature_generation(self):
        """测试签名生成是否正确"""
        ts, sig = generate_hmac_signature("test_key", "test_secret", "/test/path")
        
        assert ts is not None and len(ts) > 0, "时间戳不能为空"
        assert sig is not None and len(sig) == 64, "签名长度应该为64位(hex)"


class TestContractRealOrder:
    """合约成交测试类 - 使用 mock_trade 接口"""

    def test_contract_mock_trade_buy_long(self, contract_account, base_url):
        """
        测试合约成交 - 买入做多
        symbol: BCH/USDT (90000013)
        """
        result = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price="400",
            quantity="1.000",
            side="BUY",
            is_spot=False
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"

    def test_contract_mock_trade_sell_short(self, contract_account, base_url):
        """
        测试合约成交 - 卖出做空
        symbol: BCH/USDT (90000013)
        """
        result = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price="400",
            quantity="1.000",
            side="SELL",
            is_spot=False
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"

    def test_contract_mock_trade_buy_then_sell(self, contract_account, base_url):
        """
        测试合约成交 - 先买入(400)再卖出(410)
        symbol: BCH/USDT (90000013)
        """
        # 第一笔：买入，价格 400
        print("\n" + "=" * 60)
        print("📌 第一笔：买入 @ 400")
        print("=" * 60)
        
        result1 = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price="400",
            quantity="1.000",
            side="BUY",
            is_spot=False
        )

        assert "error" not in result1, f"第一笔买入失败: {result1.get('error')}"
        assert result1.get("code") == "SUCCESS", f"第一笔买入业务状态码错误: {result1.get('code')}"
        
        # 提取第一笔成交信息
        trade1 = result1.get("data", {})
        trade1_id = trade1.get("tradeId", "N/A")
        print(f"\n✅ 第一笔买入成交成功! tradeId: {trade1_id}")

        # 第二笔：卖出，价格 410
        print("\n" + "=" * 60)
        print("📌 第二笔：卖出 @ 410")
        print("=" * 60)
        
        result2 = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price="410",
            quantity="1.000",
            side="SELL",
            is_spot=False
        )

        assert "error" not in result2, f"第二笔卖出失败: {result2.get('error')}"
        assert result2.get("code") == "SUCCESS", f"第二笔卖出业务状态码错误: {result2.get('code')}"
        
        # 提取第二笔成交信息
        trade2 = result2.get("data", {})
        trade2_id = trade2.get("tradeId", "N/A")
        print(f"\n✅ 第二笔卖出成交成功! tradeId: {trade2_id}")

        # 汇总
        print("\n" + "=" * 60)
        print("📊 合约成交汇总")
        print("=" * 60)
        print(f"第一笔买入: tradeId={trade1_id}, 价格=400, 方向=BUY")
        print(f"第二笔卖出: tradeId={trade2_id}, 价格=410, 方向=SELL")
        print(f"预期收益: (410 - 400) * 1.000 = 10 USDT")
        print("=" * 60)

    @pytest.mark.parametrize("price,side", [
        ("400", "BUY"),
        ("400", "SELL"),
        ("410", "BUY"),
        ("410", "SELL"),
        ("420", "BUY"),
        ("420", "SELL"),
        ("430", "BUY"),
        ("430", "SELL"),
        ("440", "BUY"),
        ("440", "SELL"),
    ], ids=[
        "p400_buy",
        "p400_sell",
        "p410_buy",
        "p410_sell",
        "p420_buy",
        "p420_sell",
        "p430_buy",
        "p430_sell",
        "p440_buy",
        "p440_sell",
    ])
    def test_contract_order_with_price(self, contract_account, base_url, price, side):
        """
        测试合约成交 - 支持价格传参，方便单独调试
        
        运行示例:
            # 运行所有参数组合
            python3 -m pytest mock_trade_demo.py::TestContractRealOrder::test_contract_order_with_price -vvvvv -s
            
            # 只运行 420 价格的测试
            python3 -m pytest mock_trade_demo.py::TestContractRealOrder::test_contract_order_with_price -vvvvv -s -k "p420"
            
            # 只运行 430 价格的测试
            python3 -m pytest mock_trade_demo.py::TestContractRealOrder::test_contract_order_with_price -vvvvv -s -k "p430"
            
            # 只运行所有卖出单
            python3 -m pytest mock_trade_demo.py::TestContractRealOrder::test_contract_order_with_price -vvvvv -s -k "sell"
            
            # 同时指定价格和方向: 430 + 卖出
            python3 -m pytest mock_trade_demo.py::TestContractRealOrder::test_contract_order_with_price -vvvvv -s -k "p430 and sell"
            
            # 指定价格 420 的所有测试
            python3 -m pytest mock_trade_demo.py::TestContractRealOrder::test_contract_order_with_price -vvvvv -s -k "p420"
        """
        print("\n" + "=" * 60)
        print(f"📌 测试合约成交 - 价格: {price}, 方向: {side}")
        print("=" * 60)
        
        result = mock_trade(
            account=contract_account,
            symbol_id="90000013",
            price=price,
            quantity="1.000",
            side=side,
            is_spot=False
        )

        assert "error" not in result, f"请求失败: {result.get('error')}"
        assert result.get("code") == "SUCCESS", f"业务状态码错误: {result.get('code')}"
        
        # 提取成交信息
        data = result.get("data", {})
        trade_id = data.get("tradeId", "N/A")
        executed_price = data.get("executedPrice", price)
        
        print(f"\n✅ 合约成交成功!")
        print(f"   tradeId: {trade_id}")
        print(f"   价格: {executed_price}")
        print(f"   方向: {side}")
        print("=" * 60)


# ============ 便捷运行入口 ============


if __name__ == "__main__":
    import sys
    # 如果直接运行，调用 pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))
