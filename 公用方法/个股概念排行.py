import time
import akshare as ak
import pandas as pd
import ast
import os
import pickle
from collections import Counter
from datetime import datetime, timedelta

# 缓存文件路径
CACHE_FILE = 'stock_concept_cache.csv'
CONCEPT_MAP_PICKLE = 'stock_concept_map_internal.pkl'
CONCEPT_NAMES_PICKLE = 'concept_names_em_cache.pkl'  # ← 新增：概念名称缓存
CACHE_EXPIRE_DAYS = 1


def _get_concept_names_cached():
    """安全获取东方财富概念名称列表（带缓存）"""
    if os.path.exists(CONCEPT_NAMES_PICKLE):
        try:
            with open(CONCEPT_NAMES_PICKLE, 'rb') as f:
                data = pickle.load(f)
                if datetime.now() - data['update_time'] <= timedelta(days=CACHE_EXPIRE_DAYS):
                    return data['df']
        except Exception as e:
            print(f"⚠️ 概念名称缓存损坏: {e}")

    try:
        print(999999999)
        df = ak.stock_board_concept_name_em()
        print('获取东方财富全部概念板块名称===',df)
        with open(CONCEPT_NAMES_PICKLE, 'wb') as f:
            pickle.dump({'update_time': datetime.now(), 'df': df}, f)
        return df
    except Exception as e:
        print(f"❌ 获取概念名称失败: {e}")
        raise


def fetch_concept_cons_with_retry(name: str, max_retries: int = 3) -> pd.DataFrame:
    for attempt in range(max_retries):
        try:
            df = ak.stock_board_concept_cons_em(symbol=name)
            print('获取东方财富全部概念板块成分股===',df)
            return df
        except Exception as e:
            wait_sec = 2 + attempt * 2
            print(f"    ⚠️ {name} 第 {attempt + 1} 次失败: {e}，{wait_sec}秒后重试...")
            time.sleep(wait_sec)
    raise RuntimeError(f"获取概念 '{name}' 成分股最终失败")


def _build_full_concept_map():
    """构建映射，支持从上次中断处继续"""
    stock_to_concepts = {}

    # 尝试加载已有映射（即使过期也保留已有数据）
    if os.path.exists(CONCEPT_MAP_PICKLE):
        try:
            with open(CONCEPT_MAP_PICKLE, 'rb') as f:
                data = pickle.load(f)
                stock_to_concepts = data.get('map', {})
                last_update = data.get('update_time', datetime.min)
                if datetime.now() - last_update <= timedelta(days=CACHE_EXPIRE_DAYS):
                    print("✅ 使用有效内部概念映射缓存")
                    return stock_to_concepts
                else:
                    print("🔄 缓存已过期，将在已有基础上增量更新...")
        except Exception as e:
            print(f"⚠️ 映射缓存损坏，将重建: {e}")

    # 获取概念名称（使用独立缓存）
    try:
        concept_names_df = _get_concept_names_cached()
    except Exception:
        print("❌ 无法获取概念列表，跳过构建")
        return stock_to_concepts or {}

    total = len(concept_names_df)
    processed = 0
    failed_list = []

    # 只处理尚未获取的概念（避免重复）
    existing_concepts = set()
    for concepts in stock_to_concepts.values():
        existing_concepts.update(concepts)

    print(f"🔄 开始构建/更新概念映射（共 {total} 个概念，已有 {len(existing_concepts)} 个）...")

    for idx, row in concept_names_df.iterrows():
        name = row['板块名称']
        if name in existing_concepts:
            continue  # 已处理过，跳过

        print(f"  ({idx + 1}/{total}) 获取概念: {name}")
        try:
            cons_df = fetch_concept_cons_with_retry(name)
            if '代码' in cons_df.columns:
                codes = cons_df['代码'].astype(str).str.zfill(6).tolist()
                for code in codes:
                    stock_to_concepts.setdefault(code, []).append(name)
            processed += 1
            time.sleep(1.5)
        except Exception as e:
            failed_list.append(name)
            print(f"    ❌ 跳过概念 '{name}': {e}")
            continue

    # 保存（无论是否完整）
    with open(CONCEPT_MAP_PICKLE, 'wb') as f:
        pickle.dump({'update_time': datetime.now(), 'map': stock_to_concepts}, f)

    print(f"✅ 本次新增 {processed} 个概念，累计覆盖 {len(stock_to_concepts)} 只股票。")
    if failed_list:
        print(f"⚠️ 以下概念本次未成功获取（下次可重试）: {failed_list[:5]}{'...' if len(failed_list) > 5 else ''}")

    return stock_to_concepts


# --- 以下函数保持不变 ---
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        df = pd.read_csv(CACHE_FILE, dtype={'code': str})
        cache = {}
        now = datetime.now()
        for _, row in df.iterrows():
            code = row['code']
            concept_str = row.get('concept_list', '')
            update_date = row.get('update_date')
            if pd.notna(update_date):
                try:
                    update_time = datetime.strptime(str(update_date), '%Y-%m-%d')
                    if now - update_time > timedelta(days=CACHE_EXPIRE_DAYS):
                        continue
                except Exception:
                    pass
            try:
                concept_list = ast.literal_eval(concept_str) if concept_str else []
            except Exception:
                concept_list = []
            if isinstance(concept_list, list):
                cache[code] = concept_list
        return cache
    except Exception as e:
        print(f"⚠️ 缓存读取失败: {e}")
        return {}


def save_to_cache(code, concept_list):
    code = str(code).zfill(6)
    today = datetime.now().strftime('%Y-%m-%d')
    concept_str = str(concept_list)
    if os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE, dtype={'code': str})
        except Exception:
            df = pd.DataFrame(columns=['code', 'concept_list', 'update_date'])
    else:
        df = pd.DataFrame(columns=['code', 'concept_list', 'update_date'])
    if code in df['code'].values:
        df.loc[df['code'] == code, ['concept_list', 'update_date']] = [concept_str, today]
    else:
        new_row = pd.DataFrame([{'code': code, 'concept_list': concept_str, 'update_date': today}])
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CACHE_FILE, index=False, encoding='utf-8-sig')




def find_gp_concept(stock_code):
    """
    使用 ak.stock_individual_info_em 直接获取个股所属概念（推荐方式）
    返回: list of str, e.g. ['华为汽车', '智能驾驶']
    """
    stock_code = str(stock_code).replace('sh', '').replace('sz', '').zfill(6)

    # 1. 先查本地缓存
    cache = load_cache()
    if stock_code in cache:
        cached_concepts = cache[stock_code]
        if isinstance(cached_concepts, list) and len(cached_concepts) > 0:
            print(f"✅ 从缓存获取 {stock_code} => {cached_concepts}")
            return cached_concepts
        else:
            print(f"⚠️ 缓存中 {stock_code} 的概念为空，将重新查询...")

    # 2. 调用 akshare 个股信息接口（稳定！）
    try:
        print(f"📡 查询个股信息: {stock_code}")
        info_df = ak.stock_individual_info_em(symbol=stock_code)
        # 转为 dict
        info_dict = dict(zip(info_df['item'], info_df['value']))
        concept_str = info_dict.get('所属概念', '')
        if concept_str and concept_str != '--':
            concept_list = [c.strip() for c in concept_str.split(',') if c.strip()]
        else:
            concept_list = []
        
        # 3. 保存缓存
        save_to_cache(stock_code, concept_list)
        if concept_list:
            print(f"💾 已缓存 {stock_code} => {concept_list}")
        else:
            print(f"ℹ️ {stock_code} 无所属概念，已缓存空列表")
        return concept_list

    except Exception as e:
        print(f'❌ find_gp_concept({stock_code}) 调用 ak.stock_individual_info_em 失败: {e}')
        # 即使失败也缓存空值，避免反复重试
        save_to_cache(stock_code, [])
        return []


def is_hot_concept(stock_code, date, gp_zt_arr, gp_zt_concept_arr):
    try:
        if not gp_zt_concept_arr and gp_zt_arr:
            concept_counter = Counter()
            for gp_code in gp_zt_arr:
                concepts = find_gp_concept(gp_code)
                concept_counter.update(concepts)
            top_10_concepts = [c for c, _ in concept_counter.most_common(10)]
            gp_zt_concept_arr.extend(top_10_concepts)
            print("🔥 涨停数前10概念:", gp_zt_concept_arr)

        my_concepts = find_gp_concept(stock_code)
        is_hot = any(c in gp_zt_concept_arr for c in my_concepts)
        print(f"🔍 {stock_code} 所属概念 {my_concepts} 是否热门: {is_hot}")
        return is_hot
    except Exception as e:
        print('is_hot_concept()=>err:', str(e))
        return False