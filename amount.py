import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 策略检测模块（请确保这些模块存在）
from 日线组合图形.index_双U形 import check_Double_U_双U形
# from 日线组合图形.index_双炮台 import check_bowl_shaped_双炮台
# from 日线组合图形.index_仙人指路 import check_bowl_shaped_仙人指路
# from 日线组合图形.index_突破即回调 import check_bowl_shaped_突破即回调
# from 日线组合图形.index_碗形 import check_bowl_shaped_碗形
# from 日线组合图形.index_龙虎突破 import check_Double_U_龙虎突破

# 数据库操作
from database.shape_storage import get_tactics_data, save_shape_data
from database.db_manager import DuckDBManager

# ✅ 导入 inside_break（基础图形检测）
from slope import inside_break
from slope_all import inside_break_all


def get_kline_from_db(thscode, start_date, end_date):
    """
    从本地 DuckDB 获取指定股票的 K 线数据，返回 DataFrame
    start_date, end_date: 字符串 "YYYY-MM-DD"
    """
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'market.duckdb')
    manager = DuckDBManager(db_path)  # 传入正确的路径
    
    manager = DuckDBManager()
    # 使用 query_data 获取数据（注意列名与策略要求一致）
    # 策略需要列：date, open, close, high, low, volume, pctChg 等
    # 我们数据库列名：trade_date, open_price, high_price, low_price, close_price, volume, pct_chg
    df = manager.query_data(thscode=thscode, start_date=start_date, end_date=end_date, limit=10000)
    manager.close()
    if df.empty:
        return df
    # 重命名列以匹配策略期望的列名
    df = df.rename(columns={
        'trade_date': 'date',
        'open_price': 'open',
        'high_price': 'high',
        'low_price': 'low',
        'close_price': 'close',
        'pct_chg': 'pctChg'   # 策略中可能用到 pctChg
    })
    # 确保日期为 datetime 类型
    df['date'] = pd.to_datetime(df['date'])
    return df


def check_touch_type(df, symbol, time_type, gp_row):
    """
    检测组合图形（包含双U形、双炮台、龙虎突破等）
    df: 包含 date, open, close, high, low, volume, pctChg 的 DataFrame
    symbol: 股票代码（如 "000001.SZ"）
    time_type: 周期类型（如 "日线"）
    gp_row: 可传入股票当前行情数据（用于过滤或记录）
    """
    try:
        pd.set_option('future.no_silent_downcasting', True)

        # 获取模板数据（策略参数）
        tactics_df = get_tactics_data('tactics', '日线')
        if tactics_df.empty:
            return

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

        # 多线程执行各个策略检测
        with ThreadPoolExecutor() as executor:
            strategies = [
                executor.submit(check_Double_U_双U形, df, symbol, time_type, tactics_df, gp_row),
                # 如需启用其他策略，取消注释：
                # executor.submit(check_bowl_shaped_双炮台, df, symbol, time_type, tactics_df, gp_row),
                # executor.submit(check_Double_U_龙虎突破, df, symbol, time_type, tactics_df, gp_row),
                # executor.submit(check_bowl_shaped_突破即回调, df, symbol, time_type, tactics_df, gp_row),
                # executor.submit(check_bowl_shaped_碗形, df, symbol, time_type, tactics_df, gp_row),
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
                print('✅ 发现新形态信号：')
                print(df_unique)
                save_shape_data(df_unique, '组合图形', 'symbol, time_type, touch_type')

    except Exception as e:
        print(f"❌ 策略检测出错: {e}")


def check_touch_type_pure(df, symbol, time_type, gp_row):
    """
    检测纯K线图形（专用双炮台、仙人指路）
    """
    try:
        pd.set_option('future.no_silent_downcasting', True)

        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(-1).astype(float)
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['date'] = pd.to_datetime(df['date'])

        data_entries = []
        with ThreadPoolExecutor() as executor:
            strategies = [
                # executor.submit(check_bowl_shaped_仙人指路, df, symbol, time_type, df, gp_row),
                executor.submit(check_Double_U_双U形, df, symbol, time_type, df, gp_row),
            ]
            for future in as_completed(strategies):
                result = future.result()
                if result and isinstance(result, dict) and not all(pd.isnull(v) for v in result.values()):
                    data_entries.append(result)

        if data_entries:
            new_data_df = pd.DataFrame(data_entries).replace('', np.nan)
            filtered_data = new_data_df.dropna(how='all')
            if not filtered_data.empty:
                unique_columns = ['symbol', 'touch_type', 'time_type', 'direction']
                df_unique = filtered_data.drop_duplicates(subset=unique_columns, keep='last')
                print('✅ 发现纯K线信号：')
                print(df_unique)
                save_shape_data(df_unique, '组合图形', 'symbol, time_type, touch_type')

    except Exception as e:
        print(f"❌ 纯K线检测出错: {e}")


    

#===== 对单只股票执行策略检测 =====
def run_strategy_on_stock(thscode, lookback_days=300, strategy_type='full'):
    """
    对单只股票执行策略检测
    1. 先运行 inside_break 生成基础图形数据（保存到 tactics 表）
    2. 再运行高级形态检测
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    # 从本地数据库获取K线
    df = get_kline_from_db(thscode, start_date, end_date)
    if df.empty or len(df) < 30:
        print(f"⚠️ {thscode} 数据不足")
        return pd.DataFrame()  # 返回空DataFrame

    # ✅ 添加 code 列（inside_break 需要）
    df['code'] = thscode

    # ✅ 执行基础图形检测（保存到 tactics 表）
    inside_break(df, '日线')
    print(f"✅ {thscode} 基础图形检测完成")

    # 构建 gp_row（用于高级策略）
    gp_row = {
        'now': df.iloc[-1]['close'],
        'stock_code': thscode.split('.')[0]
    }

    # 执行高级策略
    if strategy_type == 'full':
        return check_touch_type(df, thscode, '日线', gp_row)
    elif strategy_type == 'pure':
        return check_touch_type_pure(df, thscode, '日线', gp_row)
    else:
        return pd.DataFrame()



#===== 对多只股票批量执行策略检测 =====
def run_strategy_on_stock_list(thscode_list, lookback_days=300, strategy_type='full'):
    """
    对多只股票批量执行策略检测，返回检测到的信号DataFrame
    """
    all_signals = []
    for thscode in thscode_list:
        signals = run_strategy_on_stock(thscode, lookback_days, strategy_type)
        if signals is not None and not signals.empty:
            all_signals.append(signals)
    if all_signals:
        return pd.concat(all_signals, ignore_index=True)
    else:
        return pd.DataFrame()
    





from concurrent.futures import ThreadPoolExecutor

# 原有的 run_strategy_on_stock_all 保持不变（它调用 inside_break_all）
def run_strategy_on_stock_parallel(thscode, lookback_days=300, strategy_type='full'):
    """单只股票策略检测的包装函数（用于多线程）"""
    return run_strategy_on_stock_all(thscode, lookback_days, strategy_type)

def run_strategy_on_stock_list_parallel(thscode_list, lookback_days=300, strategy_type='full', num_workers=8):
    """
    多线程并行执行策略检测，返回检测到的信号DataFrame
    使用 ThreadPoolExecutor 避免进程级文件锁冲突
    """
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(run_strategy_on_stock_parallel, thscode, lookback_days, strategy_type): thscode
            for thscode in thscode_list
        }
        results = []
        for future in futures:
            try:
                res = future.result(timeout=60)  # 单只股票超时60秒
                if res is not None and not res.empty:
                    results.append(res)
            except Exception as e:
                print(f"❌ 处理股票 {futures[future]} 时出错: {e}")
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()
    


#===== 对单只股票执行策略检测 多线程 =====
def run_strategy_on_stock_all(thscode, lookback_days=300, strategy_type='full'):
    """
    对单只股票执行策略检测
    1. 先运行 inside_break 生成基础图形数据（保存到 tactics 表）
    2. 再运行高级形态检测
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    # 从本地数据库获取K线
    df = get_kline_from_db(thscode, start_date, end_date)
    if df.empty or len(df) < 30:
        print(f"⚠️ {thscode} 数据不足")
        return pd.DataFrame()  # 返回空DataFrame

    # ✅ 添加 code 列（inside_break 需要）
    df['code'] = thscode

    # ✅ 执行基础图形检测（保存到 tactics 表）
    inside_break_all(df, '日线')
    print(f"✅ {thscode} 基础图形检测完成")

    # 构建 gp_row（用于高级策略）
    gp_row = {
        'now': df.iloc[-1]['close'],
        'stock_code': thscode.split('.')[0]
    }

    # 执行高级策略
    if strategy_type == 'full':
        return check_touch_type(df, thscode, '日线', gp_row)
    elif strategy_type == 'pure':
        return check_touch_type_pure(df, thscode, '日线', gp_row)
    else:
        return pd.DataFrame()