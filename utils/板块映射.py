"""
全市场股票板块映射构建（概念 + 行业）
"""
import requests
import pandas as pd
import time
from typing import Dict, List, Tuple

class StockSectorBuilder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-api-key": api_key})

    def _fetch_sector_list(self, tag: str) -> List[Dict]:
        """获取板块列表 tag: cn_concept 或 industry"""
        url = f"https://fuyao.aicubes.cn/api/a-share-index/catalog/ths-index-list?tag={tag}"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"获取板块列表失败: {data.get('message')}")
        return data.get("data", {}).get("item", [])

    def _fetch_constituents(self, sector_thscode: str) -> List[str]:
        """获取板块成分股 thscode 列表"""
        url = f"https://fuyao.aicubes.cn/api/a-share-index/constituents/ths-stock-list?thscode={sector_thscode}"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            return []
        items = data.get("data", {}).get("item", [])
        return [item.get("thscode") for item in items]

    def build_full_mapping(self) -> Dict[str, Tuple[str, str]]:
        """
        返回映射: {thscode: (concept_str, industry_str)}
        """
        # 1. 获取所有概念板块
        concept_sectors = self._fetch_sector_list("cn_concept")
        concept_mapping = {code: [] for code in ...}  # 略，先构建空字典
        # 2. 遍历概念板块，填充映射
        concept_mapping = {}
        for sector in concept_sectors:
            code = sector['thscode']
            name = sector['name']
            constituents = self._fetch_constituents(code)
            for stock in constituents:
                concept_mapping.setdefault(stock, []).append(name)
            time.sleep(0.05)

        # 3. 获取所有行业板块（申万行业）
        industry_sectors = self._fetch_sector_list("industry")
        industry_mapping = {}
        for sector in industry_sectors:
            code = sector['thscode']
            name = sector['name']
            constituents = self._fetch_constituents(code)
            for stock in constituents:
                industry_mapping.setdefault(stock, []).append(name)
            time.sleep(0.05)

        # 4. 合并结果
        all_stocks = set(concept_mapping.keys()) | set(industry_mapping.keys())
        result = {}
        for stock in all_stocks:
            concepts = concept_mapping.get(stock, [])
            industries = industry_mapping.get(stock, [])
            result[stock] = (', '.join(concepts), ', '.join(industries))
        return result