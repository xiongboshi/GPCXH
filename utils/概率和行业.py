"""
板块归属模块 - 为连板天梯股票添加概念板块和行业板块，并提供全市场映射构建
"""
import requests
import pandas as pd
from typing import List, Dict, Optional, Union
import time
import os
import pickle


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


# ========== 全市场映射构建（带缓存和重试） ==========
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
SECTOR_CACHE_PATH = os.path.join(CACHE_DIR, 'sector_mapping.pkl')

def build_full_market_mapping(api_key: str, include_concept: bool = True, include_industry: bool = True, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
    """
    构建全市场股票的概念和行业板块映射（带缓存）
    若缓存存在且未强制刷新，直接读取缓存。
    若需刷新，则请求API并保存缓存。
    返回: {thscode: {'concept': '概念1,概念2', 'industry': '行业1,行业2'}}

    Args:
        api_key: 同花顺 API Key
        include_concept: 是否包含概念板块
        include_industry: 是否包含行业板块
        force_refresh: 是否强制刷新缓存
    """
    # 检查缓存
    if not force_refresh and os.path.exists(SECTOR_CACHE_PATH):
        try:
            with open(SECTOR_CACHE_PATH, 'rb') as f:
                cached = pickle.load(f)
            print(f"✅ 从缓存加载板块映射，共 {len(cached)} 只股票")
            return cached
        except Exception as e:
            print(f"⚠️ 缓存读取失败: {e}，将重新请求")

    session = requests.Session()
    session.headers.update({"X-api-key": api_key})

    def fetch_sector_list(tag, retries=5):
        url = f"https://fuyao.aicubes.cn/api/a-share-index/catalog/ths-index-list?tag={tag}"
        for attempt in range(retries):
            try:
                resp = session.get(url)
                if resp.status_code == 429:
                    wait = min((attempt + 1) * 3, 15)  # 3s, 6s, 9s, 12s, 15s
                    print(f"⏳ 触发限流 (429)，等待 {wait}s 后重试...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    raise ValueError(f"API错误: {data.get('message')}")
                return data.get("data", {}).get("item", [])
            except requests.exceptions.RequestException as e:
                print(f"⚠️ 请求失败 (尝试 {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    raise
        raise Exception(f"获取板块列表失败，已重试 {retries} 次")

    def fetch_constituents(sector_code, retries=5):
        url = f"https://fuyao.aicubes.cn/api/a-share-index/constituents/ths-stock-list?thscode={sector_code}"
        for attempt in range(retries):
            try:
                resp = session.get(url)
                if resp.status_code == 429:
                    wait = min((attempt + 1) * 3, 15)
                    print(f"⏳ 触发限流 (429)，等待 {wait}s 后重试...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    return []
                items = data.get("data", {}).get("item", [])
                return [item.get("thscode") for item in items]
            except requests.exceptions.RequestException as e:
                print(f"⚠️ 请求成分股失败 (尝试 {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    raise
        return []

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
            time.sleep(0.3)  # 限流保护
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
            time.sleep(0.3)
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
    else:
        # 只有概念
        final_mapping = {code: {'concept': ', '.join(vals), 'industry': ''} for code, vals in mapping.items()}

    # 保存缓存
    try:
        with open(SECTOR_CACHE_PATH, 'wb') as f:
            pickle.dump(final_mapping, f)
        print(f"✅ 板块映射已缓存至 {SECTOR_CACHE_PATH}")
    except Exception as e:
        print(f"⚠️ 缓存保存失败: {e}")

    return final_mapping


# ========== 便捷函数（连板天梯专用） ==========
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




# 在 utils/概率和行业.py 底部添加
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
SECTOR_CACHE_PATH = os.path.join(CACHE_DIR, 'sector_mapping.pkl')