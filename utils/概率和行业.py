"""
板块归属模块 - 为连板天梯股票添加概念板块和行业板块，并提供全市场映射构建
"""
import requests
import pandas as pd
from typing import List, Dict, Optional, Union
import time


class StockSectorMatcher:
    """股票板块匹配器，支持概念板块和行业板块"""
    def __init__(self, api_key: str, sector_type: str = 'concept'):
        """
        Args:
            api_key: 同花顺 API Key
            sector_type: 'concept'(概念板块) | 'industry'(申万行业)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-api-key": api_key})
        self.sector_type = sector_type
        self._sector_cache = None

    def _fetch_all_sectors(self) -> pd.DataFrame:
        """获取所有板块列表（根据 sector_type 决定）"""
        tag = 'cn_concept' if self.sector_type == 'concept' else 'industry'
        url = f"https://fuyao.aicubes.cn/api/a-share-index/catalog/ths-index-list?tag={tag}"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"获取板块列表失败: {data.get('message')}")
        items = data.get("data", {}).get("item", [])
        return pd.DataFrame(items)

    def _fetch_sector_constituents(self, sector_thscode: str) -> List[str]:
        """获取单个板块的成分股 thscode 列表"""
        url = f"https://fuyao.aicubes.cn/api/a-share-index/constituents/ths-stock-list?thscode={sector_thscode}"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            return []
        items = data.get("data", {}).get("item", [])
        return [item.get("thscode") for item in items]

    def get_sector_mapping(self, stock_list: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """获取股票到板块的映射"""
        if self._sector_cache is not None:
            if stock_list is None:
                return self._sector_cache
            else:
                return {code: self._sector_cache.get(code, []) for code in stock_list}

        sectors_df = self._fetch_all_sectors()
        mapping = {}
        for _, row in sectors_df.iterrows():
            sector_code = row['thscode']
            sector_name = row['name']
            constituents = self._fetch_sector_constituents(sector_code)
            for stock in constituents:
                if stock not in mapping:
                    mapping[stock] = []
                mapping[stock].append(sector_name)
            time.sleep(0.05)  # 避免请求过频
        self._sector_cache = mapping
        if stock_list is None:
            return mapping
        else:
            return {code: mapping.get(code, []) for code in stock_list}


# ========== 全市场映射构建（新增） ==========
def build_full_market_mapping(api_key: str, include_concept: bool = True, include_industry: bool = True) -> Dict[str, Dict[str, str]]:
    """
    构建全市场股票的概念和行业板块映射
    返回: {thscode: {'concept': '概念1,概念2', 'industry': '行业1,行业2'}}

    Args:
        api_key: 同花顺 API Key
        include_concept: 是否包含概念板块
        include_industry: 是否包含行业板块
    """
    session = requests.Session()
    session.headers.update({"X-api-key": api_key})

    def fetch_sector_list(tag):
        url = f"https://fuyao.aicubes.cn/api/a-share-index/catalog/ths-index-list?tag={tag}"
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"获取板块列表失败: {data.get('message')}")
        return data.get("data", {}).get("item", [])

    def fetch_constituents(sector_code):
        url = f"https://fuyao.aicubes.cn/api/a-share-index/constituents/ths-stock-list?thscode={sector_code}"
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            return []
        items = data.get("data", {}).get("item", [])
        return [item.get("thscode") for item in items]

    mapping = {}

    # 处理概念板块
    if include_concept:
        concept_sectors = fetch_sector_list("cn_concept")
        print(f"🔍 处理概念板块: {len(concept_sectors)} 个")
        concept_dict = {}
        for i, sector in enumerate(concept_sectors):
            code = sector['thscode']
            name = sector['name']
            constituents = fetch_constituents(code)
            for stock in constituents:
                concept_dict.setdefault(stock, []).append(name)
            time.sleep(0.05)
            if (i + 1) % 50 == 0:
                print(f"   已处理 {i+1}/{len(concept_sectors)}")
        mapping = concept_dict
        print(f"✅ 概念板块映射完成，涉及 {len(mapping)} 只股票")

    # 处理行业板块（申万行业）
    if include_industry:
        industry_sectors = fetch_sector_list("industry")
        print(f"🔍 处理行业板块: {len(industry_sectors)} 个")
        industry_dict = {}
        for i, sector in enumerate(industry_sectors):
            code = sector['thscode']
            name = sector['name']
            constituents = fetch_constituents(code)
            for stock in constituents:
                industry_dict.setdefault(stock, []).append(name)
            time.sleep(0.05)
            if (i + 1) % 50 == 0:
                print(f"   已处理 {i+1}/{len(industry_sectors)}")
        print(f"✅ 行业板块映射完成，涉及 {len(industry_dict)} 只股票")

        # 合并概念和行业
        all_stocks = set(mapping.keys()) | set(industry_dict.keys())
        final_mapping = {}
        for stock in all_stocks:
            final_mapping[stock] = {
                'concept': ', '.join(mapping.get(stock, [])),
                'industry': ', '.join(industry_dict.get(stock, []))
            }
        return final_mapping
    else:
        # 只有概念
        return {code: {'concept': ', '.join(vals), 'industry': ''} for code, vals in mapping.items()}


# ========== 便捷函数（连板天梯专用） ==========
# ========== 新增：从数据库查询板块信息（快速） ==========
def enrich_ladder_data_from_db(df: pd.DataFrame, db_manager) -> pd.DataFrame:
    """
    为连板天梯 DataFrame 添加概念板块和行业板块两列（从本地数据库 stock_list 表查询）
    """
    if df.empty:
        return df

    stock_codes = df['thscode'].unique().tolist()
    if not stock_codes:
        return df

    # 构建 SQL 查询，使用参数化
    placeholders = ', '.join(['?'] * len(stock_codes))
    sql = f"""
        SELECT thscode, concept, industry
        FROM stock_list
        WHERE thscode IN ({placeholders})
    """
    try:
        # 直接使用 db_manager.db.execute 并传入参数
        result_df = db_manager.db.execute(sql, stock_codes).df()
    except AttributeError:
        # 如果 db_manager 没有 db 属性，尝试使用 execute 方法
        result_df = db_manager.execute(sql, stock_codes).df()

    if result_df.empty:
        result = df.copy()
        result['concept'] = ''
        result['industry'] = ''
        return result

    concept_map = dict(zip(result_df['thscode'], result_df['concept']))
    industry_map = dict(zip(result_df['thscode'], result_df['industry']))

    result = df.copy()
    result['concept'] = result['thscode'].map(concept_map).fillna('')
    result['industry'] = result['thscode'].map(industry_map).fillna('')
    return result