import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# 策略检测模块（请确保这些模块存在）
from 日线组合图形.index_主升内 import check_Double_U_主升内    
from 日线组合图形.index_主升外 import check_Double_U_主升外
from 日线组合图形.index_主升六外 import check_Double_U_主升六外

from 入场判断.index import check_Enter_U



# 数据库操作
from database.shape_storage import save_shape_data
from database.db_manager import DuckDBManager

# ✅ 导入 inside_break（基础图形检测）
from slope import inside_break
from slope_all import inside_break_all

# ========== 全局数据库连接（线程安全） ==========
_global_db_manager = None
_db_lock = threading.Lock()

def get_global_db_manager():
    global _global_db_manager
    if _global_db_manager is None:
        # 修正：只向上取一级，得到项目根目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'database', 'market.duckdb')
        _global_db_manager = DuckDBManager(db_path)
    return _global_db_manager

def get_tactics_data_from_db():
    """线程安全地获取 tactics 数据（包含所有列）"""
    with _db_lock:
        manager = get_global_db_manager()
        df = manager.db.execute("""
            SELECT *
            FROM tactics
            WHERE time_type = '日线'
            ORDER BY date
        """).df()
    return df

# ========== K线获取函数（线程安全） ==========
def get_kline_from_db(thscode, start_date, end_date):
    """
    从本地 DuckDB 获取指定股票的 K 线数据，返回 DataFrame
    start_date, end_date: 字符串 "YYYY-MM-DD"
    """
    with _db_lock:
        manager = get_global_db_manager()
        df = manager.query_data(thscode=thscode, start_date=start_date, end_date=end_date, limit=10000)
    
    if df.empty:
        return df
    # 重命名列以匹配策略期望的列名
    df = df.rename(columns={
        'trade_date': 'date',
        'open_price': 'open',
        'high_price': 'high',
        'low_price': 'low',
        'close_price': 'close',
        'pct_chg': 'pctChg'
    })
    df['date'] = pd.to_datetime(df['date'])
    return df


# ================================================================
# ★★★ 入场判断（多线程版）—— 直接调用 shape_storage 实现 ★★★
# ================================================================
def run_entry_check(tactics_df, thscode, lookback_days=300, time_type='日线'):
    
    """
    检测入场判断（包含双U形、双炮台、龙虎突破等）
    df: 包含 date, open, close, high, low, volume, pctChg 的 DataFrame
    symbol: 股票代码（如 "000001.SZ"）
    time_type: 周期类型（如 "日线"）
    gp_row: 可传入股票当前行情数据（用于过滤或记录）
    tactics_df: 基础图形数据（由外部传入，避免重复读取）
    """
    try:
        pd.set_option('future.no_silent_downcasting', True)

        # 1. 获取K线数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        df = get_kline_from_db(thscode, start_date, end_date)
        if df.empty or len(df) < 30:
            print(f"⚠️ {thscode} 数据不足，跳过入场检测")
            return []


        data_entries = []

        # 多线程执行各个策略检测（这里内部又创建了线程池，可能会嵌套，但影响不大）
        with ThreadPoolExecutor() as executor:
            strategies = [
                executor.submit(check_Enter_U, df, thscode, time_type, tactics_df),
            ]

            for future in as_completed(strategies):
                result = future.result()
                if result and isinstance(result, dict) and not all(pd.isnull(v) for v in result.values()):
                    data_entries.append(result)

        if data_entries:
            new_data_df = pd.DataFrame(data_entries).replace('', np.nan)
            filtered_data = new_data_df.dropna(how='all')
            if not filtered_data.empty:
                # 去重并保存
                unique_columns = ['symbol', 'touch_type', 'time_type', 'direction', 
                                  '小的_U形_u_price', '大的_U形_datetime']
                # print('✅ 发现新入场信号：')
                # print(df_unique)
                # 入场信号图形
                df_unique = filtered_data.drop_duplicates(subset=unique_columns, keep='last')
                return df_unique   # 只返回，不保存

        # ✅ 无信号返回空 DataFrame
        return pd.DataFrame()

    except Exception as e:
        print(f"❌ 策略检测出错: {e}")
        return pd.DataFrame()
    


def run_entry_check_parallel(stock_list=None, days_after=12, limit_pct=9.8, num_workers=8):
    """
    多线程并行执行入场判断：
    1. 对每只股票执行入场条件的策略检测，生成买入信号并保存到 tactics_enter 表。
    2. 所有线程完成后，从 tactics_enter 表读取数据，进行涨停检测。
    返回所有符合条件的信号列表（字典列表）。
    """

    if stock_list is None:
        with _db_lock:
            manager = get_global_db_manager()
            tactics_df = manager.db.execute("SELECT * FROM tactics_zhtx WHERE time_type='日线'").df()
            stock_list = tactics_df['symbol'].tolist() if not tactics_df.empty else []
    if not stock_list:
        return []

    all_dfs = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(run_entry_check, tactics_df, thscode, 300, '日线'): thscode
            for thscode in stock_list
        }
        for future in as_completed(futures):
            try:
                df = future.result()
                if df is not None and not df.empty:
                    all_dfs.append(df)
            except Exception as e:
                print(f"❌ 处理股票 {futures[future]} 时出错: {e}")

    if not all_dfs:
        return []

    # 合并所有信号
    combined_df = pd.concat(all_dfs, ignore_index=True)
    # 去重（按主键）
    combined_df = combined_df.drop_duplicates(subset=['symbol', 'touch_type', 'time_type', 'direction'], keep='last')

    # 统一保存到 tactics_enter
    save_shape_data(combined_df, 'tactics_enter', 'symbol, time_type, touch_type, direction')

    # ★ 读取并返回（增加 JOIN 获取概念和行业）
    with _db_lock:
        manager = get_global_db_manager()
        df_enter = manager.db.execute("""
            SELECT e.*, sl.concept, sl.industry
            FROM tactics_enter e
            LEFT JOIN stock_list sl ON e.symbol = sl.thscode
            WHERE e.time_type='日线' AND e.direction='买'
        """).df()

    # 将所有日期列转为字符串
    for col in df_enter.select_dtypes(include=['datetime64', 'datetime']).columns:
        df_enter[col] = df_enter[col].dt.strftime('%Y-%m-%d')
    # 将其他可能含有NaT的列也处理（如signal_time）
    for col in df_enter.columns:
        if df_enter[col].dtype == 'object':
            # 检查是否包含Timestamp
            if not df_enter[col].empty and isinstance(df_enter[col].iloc[0], pd.Timestamp):
                df_enter[col] = df_enter[col].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else '')

    # 关闭连接
    global _global_db_manager
    if _global_db_manager is not None:
        _global_db_manager.close()
        _global_db_manager = None
        print("✅ 已关闭全局数据库连接")

    return df_enter.to_dict('records')





#================================================================
#================================================================
# ========== 组合图形策略检测 ==========
def check_touch_type(df, symbol, time_type, gp_row, tactics_df):
    """
    检测组合图形（包含双U形、双炮台、龙虎突破等）
    df: 包含 date, open, close, high, low, volume, pctChg 的 DataFrame
    symbol: 股票代码（如 "000001.SZ"）
    time_type: 周期类型（如 "日线"）
    gp_row: 可传入股票当前行情数据（用于过滤或记录）
    tactics_df: 基础图形数据（由外部传入，避免重复读取）
    """
    try:
        pd.set_option('future.no_silent_downcasting', True)

        # 如果未传入 tactics_df，则从数据库获取（但这里应该都会传入）
        if tactics_df is None:
            tactics_df = get_tactics_data_from_db()
        if tactics_df.empty:
            return pd.DataFrame()

        # 数据类型转换
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(-1).astype(float)
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['date'] = pd.to_datetime(df['date'])

        tactics_df['date'] = pd.to_datetime(tactics_df['date'], errors='coerce')
        tactics_df['u形图形_内突_u_point'] = pd.to_datetime(tactics_df['u形图形_内突_u_point'], errors='coerce')
        tactics_df['u形图形_内突_u_price'] = tactics_df['u形图形_内突_u_price'].astype(float)
        tactics_df['u形图形_内突_u_bot_price'] = tactics_df['u形图形_内突_u_bot_price'].astype(float)
        tactics_df['u形图形_内突_u_k_num'] = tactics_df['u形图形_内突_u_k_num'].astype(float)

        data_entries = []

        # 多线程执行各个策略检测（这里内部又创建了线程池，可能会嵌套，但影响不大）
        with ThreadPoolExecutor() as executor:
            strategies = [
                executor.submit(check_Double_U_主升内, df, symbol, time_type, tactics_df, gp_row),
                executor.submit(check_Double_U_主升外, df, symbol, time_type, tactics_df, gp_row),
                executor.submit(check_Double_U_主升六外, df, symbol, time_type, tactics_df, gp_row),
            ]

            for future in as_completed(strategies):
                result = future.result()
                if result and isinstance(result, dict) and not all(pd.isnull(v) for v in result.values()):
                    data_entries.append(result)

        if data_entries:
            new_data_df = pd.DataFrame(data_entries).replace('', np.nan)
            filtered_data = new_data_df.dropna(how='all')
            if not filtered_data.empty:
                # 去重并保存
                unique_columns = ['symbol', 'touch_type', 'time_type', 'direction', 
                                  '小的_U形_u_price', '大的_U形_datetime']
                df_unique = filtered_data.drop_duplicates(subset=unique_columns, keep='last')
                # print('✅ 发现新形态信号：')
                # print(df_unique)
                # 组合图形
                save_shape_data(df_unique, 'tactics_zhtx', 'symbol, time_type, touch_type')
                # ✅ 返回信号 DataFrame
                return df_unique

        # ✅ 无信号返回空 DataFrame
        return pd.DataFrame()

    except Exception as e:
        print(f"❌ 策略检测出错: {e}")
        return pd.DataFrame()

# ========== 基础策略检测（单线程版） ==========
def run_strategy_on_stock(thscode, lookback_days=300, strategy_type='full'):
    """
    对单只股票执行基础策略检测（单线程版）
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    df = get_kline_from_db(thscode, start_date, end_date)
    if df.empty or len(df) < 30:
        print(f"⚠️ {thscode} 数据不足")
        return pd.DataFrame()

    df['code'] = thscode
    inside_break(df, '日线')
    # print(f"✅ {thscode} 基础图形检测完成")

def run_strategy_on_stock_list(thscode_list, lookback_days=300, strategy_type='full'):
    """
    对多只股票批量执行基础策略检测（单线程串行）
    """
    for thscode in thscode_list:
        run_strategy_on_stock(thscode, lookback_days, strategy_type)
    return pd.DataFrame()  # 此函数原意可能返回信号，但当前实现不返回，为兼容保留

# ========== 基础策略检测（多线程版） ==========
def run_strategy_on_stock_parallel(thscode, lookback_days=300, strategy_type='full'):
    """单只股票基础策略检测的包装函数（用于多线程）"""
    return run_strategy_on_stock_all(thscode, lookback_days, strategy_type)

def run_strategy_on_stock_list_parallel(thscode_list, lookback_days=300, strategy_type='full', num_workers=8):
    """
    多线程并行执行基础策略检测
    """
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(run_strategy_on_stock_parallel, thscode, lookback_days, strategy_type): thscode
            for thscode in thscode_list
        }
        results = []
        for future in futures:
            try:
                res = future.result(timeout=60)
                if res is not None and not res.empty:
                    results.append(res)
            except Exception as e:
                print(f"❌ 处理股票 {futures[future]} 时出错: {e}")
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()

def run_strategy_on_stock_all(thscode, lookback_days=300, strategy_type='full'):
    """
    对单只股票执行基础策略检测（多线程实际调用）
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    df = get_kline_from_db(thscode, start_date, end_date)
    if df.empty or len(df) < 30:
        print(f"⚠️ {thscode} 数据不足")
        return pd.DataFrame()

    df['code'] = thscode
    inside_break_all(df, '日线')
    # print(f"✅ {thscode} 基础图形检测完成")
    return pd.DataFrame()  # 返回空，因为只保存数据，不返回信号

# ========== 组合图形检测（多线程版） ==========
def run_combined_strategy_on_stock_parallel(thscode, lookback_days, strategy_type, tactics_df):
    """单只股票组合图形检测（传入 tactics_df 避免重复读取）"""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        df = get_kline_from_db(thscode, start_date, end_date)
        if df.empty or len(df) < 30:
            return None
        gp_row = {'now': df.iloc[-1]['close'], 'stock_code': thscode.split('.')[0]}
        if strategy_type == 'full':
            signals = check_touch_type(df, thscode, '日线', gp_row, tactics_df)
        else:
            # 如果有其他策略类型，可添加，当前只有 full
            signals = None
        return signals if signals is not None and not signals.empty else None
    except Exception as e:
        print(f"❌ 组合图形检测 {thscode} 失败: {e}")
        return None




def run_combined_strategy_on_stock_list_parallel(thscode_list, lookback_days=300, strategy_type='full', num_workers=8):
    """
    多线程并行执行组合图形策略，执行完毕后关闭数据库连接
    """
    try:
        # 使用全局连接获取 tactics_df（线程安全）
        tactics_df = get_tactics_data_from_db()
        if tactics_df.empty:
            print("⚠️ 无基础图形数据，跳过组合图形检测")
            return pd.DataFrame()

        all_signals = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(run_combined_strategy_on_stock_parallel, thscode, lookback_days, strategy_type, tactics_df): thscode
                for thscode in thscode_list
            }
            for future in as_completed(futures):
                try:
                    signals = future.result(timeout=60)
                    if signals is not None and not signals.empty:
                        all_signals.append(signals)
                except Exception as e:
                    print(f"❌ 处理股票 {futures[future]} 组合图形时出错: {e}")
        if all_signals:
            return pd.concat(all_signals, ignore_index=True)
        else:
            return pd.DataFrame()
    finally:
        # 关闭全局数据库连接并置空，以便下次重新创建
        global _global_db_manager
        if _global_db_manager is not None:
            _global_db_manager.close()
            _global_db_manager = None
            print("✅ 已关闭全局数据库连接")