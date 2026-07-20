"""
连板天梯数据封装
文档参考: https://fuyao.aicubes.cn/docs/mcp/tools/get_a_share_special_data_limit_up_ladder/
"""
import requests
import pandas as pd
from typing import Optional, Dict, List, Any


class LimitUpLadder:
    """连板天梯数据获取与解析"""

    BASE_URL = "https://fuyao.aicubes.cn"
    ENDPOINT = "/api/a-share/special-data/limit-up-ladder"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-api-key": api_key,
            "Content-Type": "application/json"
        })

    def fetch_raw(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{self.ENDPOINT}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()


    def to_dataframe(self, raw_data: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        if raw_data is None:
            raw_data = self.fetch_raw()

        if raw_data.get("code") != 0:
            raise ValueError(f"API 错误: {raw_data.get('message')}")

        data = raw_data.get("data", {})
        items = data.get("item", [])

        rows = []
        board_map = {
            "two_board": 2,
            "three_board": 3,
            "four_board": 4,
            "five_board": 5,
            "six_board": 6,
            "seven_over": 7
        }

        for day_item in items:
            date_str = day_item.get("date", "")
            boards = day_item.get("boards", {})
            for board_key, stock_list in boards.items():
                # 优先用数据中的 board_num，没有则用映射
                for stock in stock_list:
                    board_num = stock.get("board_num")
                    if board_num is None:
                        board_num = board_map.get(board_key)
                    if board_num is None:
                        continue
                    rows.append({
                        "date": date_str,
                        "board_num": board_num,
                        "thscode": stock.get("thscode"),
                        "ticker": stock.get("ticker"),
                        "name": stock.get("name"),
                        "seal_nextday": stock.get("seal_nextday"),
                        "sign_level": stock.get("sign_level"),
                    })

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
        return df




    def get_ladder_summary(self) -> pd.DataFrame:
        raw = self.fetch_raw()
        if raw.get("code") != 0:
            raise ValueError(f"API 错误: {raw.get('message')}")

        items = raw.get("data", {}).get("item", [])
        rows = []

        for day_item in items:
            row = {"date": day_item.get("date")}
            boards = day_item.get("boards", {})
            # ★ 动态读取所有板位，而不是硬编码
            for board_key, stock_list in boards.items():
                row[board_key] = len(stock_list)
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
            df = df.sort_values("date", ascending=False)
        return df

    # ★ 新增：按日期查询连板梯队
    def get_ladder_by_date(self, date_str: str) -> Dict[str, List[Dict]]:
        raw = self.fetch_raw()
        if raw.get("code") != 0:
            raise ValueError(f"API 错误: {raw.get('message')}")

        # 标准化：去除所有 '-'，同时保留原始格式用于比较
        target = date_str.replace("-", "")
        items = raw.get("data", {}).get("item", [])
        for day_item in items:
            api_date = day_item.get("date", "")
            # 尝试两种格式匹配
            if api_date == target or api_date == date_str:
                boards = day_item.get("boards", {})
                result = {}
                board_map = {
                    "two_board": "2",
                    "three_board": "3",
                    "four_board": "4",
                    "five_board": "5",
                    "six_board": "6",
                    "seven_over": "7"
                }
                for board_key, stocks in boards.items():
                    mapped_key = board_map.get(board_key, board_key)
                    result[mapped_key] = stocks
                return result
        return {}


# ========== 便捷函数 ==========
def get_limit_up_ladder(api_key: str, as_dataframe: bool = True):
    client = LimitUpLadder(api_key)
    if as_dataframe:
        return client.to_dataframe()
    return client.fetch_raw()


def get_ladder_summary(api_key: str) -> pd.DataFrame:
    client = LimitUpLadder(api_key)
    return client.get_ladder_summary()



# API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"

# # 方式1：获取 DataFrame
# df = get_limit_up_ladder(API_KEY, as_dataframe=True)
# print("连板天梯数据（全部）:")
# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# print(df)

# # 方式2：获取汇总统计
# summary = get_ladder_summary(API_KEY)
# print("\n连板天梯汇总（每日各板位数量）:")
# print(summary)  # 打印全部

# # 方式3：指定日期查询
# client = LimitUpLadder(API_KEY)
# ladder = client.get_ladder_by_date("2026-07-20")  # 改为今天
# print("\n2026-07-20 连板梯队:")
# for board, stocks in ladder.items():
#     print(f"  {board}板: {len(stocks)} 只")
#     for s in stocks:
#         print(f"    {s.get('name')} ({s.get('thscode')})")





# # 获取连板天梯数据
# df = get_limit_up_ladder(API_KEY, as_dataframe=True)

# # 添加概念和行业板块
# df_enriched = enrich_ladder_data(df, API_KEY)

# # 查看结果
# print(df_enriched[['name', 'board_num', 'concept', 'industry']].head(10))