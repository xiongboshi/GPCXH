# 公用方法/获取所有股票代码.py
import requests
import time
from datetime import datetime

API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"
BASE_URL = "https://fuyao.aicubes.cn"
HEADERS = {"X-api-key": API_KEY}


def get_all_tickers(max_retries=3, retry_delay=2):
    """
    获取全市场股票代码列表（带重试机制）
    """
    all_tickers = []
    limit = 100
    offset = 0
    total = None
    attempt = 0
    
    print("📡 开始获取股票代码列表...")
    
    while True:
        url = f"{BASE_URL}/api/a-share/prices/snapshot?limit={limit}&offset={offset}"
        success = False
        
        for retry in range(max_retries):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                data = resp.json()
                
                if data.get("code") != 0:
                    print(f"⚠️ API返回错误 (offset={offset}): {data.get('message')}")
                    if retry < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"❌ 放弃 offset={offset}")
                        break
                
                items = data.get("data", {}).get("item", [])
                if not items:
                    print(f"⚠️ offset={offset} 返回空数据")
                    break
                
                # 更新总数（只在第一次获取时设置）
                if total is None:
                    total = data.get("data", {}).get("total", 0)
                    print(f"📊 总股票数: {total}")
                
                # 添加到列表
                for item in items:
                    all_tickers.append(item["thscode"])
                
                print(f"   ✅ 已获取 {len(all_tickers)}/{total} 只")
                success = True
                break  # 成功获取，跳出重试循环
                
            except Exception as e:
                print(f"❌ 请求异常 (offset={offset}, 重试 {retry+1}/{max_retries}): {e}")
                if retry < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print(f"❌ 放弃 offset={offset}")
        
        if not success:
            # 如果当前页连续失败，记录并尝试跳过（但可能丢失数据）
            print(f"⚠️ 跳过 offset={offset}")
            offset += limit
            continue
        
        # 判断是否完成
        if total is not None and offset + limit >= total:
            print(f"✅ 全部获取完成，共 {len(all_tickers)} 只")
            break
        
        offset += limit
        time.sleep(0.3)  # 控制请求频率
    
    return all_tickers


def get_historical_kline(thscode, start_date, end_date, adjust="forward", max_retries=3):
    """
    获取单只股票的历史K线
    """
    start_ms = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ms = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    url = f"{BASE_URL}/api/a-share/prices/historical"
    params = {
        "thscode": thscode,
        "interval": "1d",
        "start": start_ms,
        "end": end_ms,
        "adjust": adjust,
        "offset": 0
    }
    
    all_bars = []
    
    while True:
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
                data = resp.json()
                
                if data.get("code") != 0:
                    print(f"⚠️ {thscode} API错误 (offset={params['offset']}): {data.get('message')}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        return all_bars if all_bars else []  # 返回已获取的部分
                
                items = data.get("data", {}).get("item", [])
                if not items:
                    return all_bars  # 没有更多数据
                
                all_bars.extend(items)
                
                # 如果返回数量小于5000，说明是最后一页
                if len(items) < 5000:
                    return all_bars
                
                # 继续下一页
                params["offset"] += len(items)
                time.sleep(0.2)  # 分页间隔
                break  # 成功获取，跳出重试循环
                
            except Exception as e:
                print(f"❌ {thscode} 请求异常 (offset={params['offset']}, 尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return all_bars if all_bars else []  # 返回已获取的部分
    
    return all_bars


if __name__ == "__main__":
    # 测试
    tickers = get_all_tickers()
    print(f"共获取 {len(tickers)} 只股票")
    if tickers:
        print("前10只:", tickers[:10])