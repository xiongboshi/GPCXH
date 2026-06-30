import pandas as pd
from datetime import datetime, timedelta  



touch_to_save = {
    'now_time': '',
    'gp_name': '',
    'date': '',
    'symbol': '',
    'touch_type': '',
    'time_type': '',
    'direction': '',
    'sell_u形图形_u_price': '',
    'sell_u形图形_u_n_price': '',
    'sell_u形图形_datetime': '',
    'sell_u形图形_point_datetime': '',
    'buy_u形图形_u_price': '',
    'buy_u形图形_u_n_price': '',
    'buy_u形图形_datetime': '',
    'buy_u形图形_point_datetime': '',
}

def check_bowl_shaped_双炮台(df, symbol, time_type, tactics_df, gp_row):
    '''
    检测 双炮台 图形  同级别查看同级别的图形
    '''
    try:
        tactics_name = ['双炮台']
        
        all_process_arr = []
        
        process_arr = process_false_breakout(tactics_df, df, tactics_name,time_type, gp_row)
        all_process_arr.extend(process_arr)  #合并
            
        
        if len(all_process_arr) > 0:
            # all_process_df = pd.DataFrame(all_process_arr)
            # return all_process_df
            return all_process_arr[0]
    
        # return touch_to_save
        
        return {}
                
    except Exception as e:
        print(f"计算策略函数（check_bowl_shaped_双炮台）出错: {e}")
        




def process_false_breakout(tactics_df, df, tactics_name, time_type, gp_row):
    '''
    检测 双炮台 图形：基于最近一次涨停后的价格波动范围是否收敛
    条件：
      1. 过去8天内（不含今天）有至少一个涨停（pctChg >= 9.8）
      2. 找到最近一次涨停日
      3. 从涨停次日到今天：
          a) 实体上沿 <= 涨停收盘 * 1.05
          b) 实体下沿 >= 涨停前日收盘 * 0.95
          c) 所有收盘价 ∈ [涨停收盘 * 0.95, 涨停收盘]  ← 新增！
    '''
    try:
        双炮台_process_arr = []

        required_cols = ['code', 'date', 'open', 'close', 'high', 'low', 'pctChg']
        for col in required_cols:
            if col not in df.columns:
                return 双炮台_process_arr

        df = df.copy()
        for col in ['open', 'close', 'high', 'low', 'pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        recent_df = df.tail(15).reset_index(drop=True)
        if len(recent_df) < 3:
            return 双炮台_process_arr

        # 排除今天，找历史涨停
        historical = recent_df.iloc[:-1]
        zt_days = historical[historical['pctChg'] >= 9.8]

        if zt_days.empty:
            return 双炮台_process_arr

        last_zt_idx = zt_days.index[-1]
        if last_zt_idx == 0:
            return 双炮台_process_arr

        zt_close = recent_df.loc[last_zt_idx, 'close']
        prev_close = recent_df.loc[last_zt_idx - 1, 'close']

        # 边界1：实体波动范围 单位是0.01代表涨幅10%
        upper_bound = zt_close * 1.05  #最高价格
        lower_bound = prev_close * 0.95  #最低价格
        cd_bound = prev_close * 1.04 #触底价格

        after_zt_df = recent_df.loc[last_zt_idx + 1:].copy()
        if after_zt_df.empty:
            return 双炮台_process_arr

        # === 实体上下沿 ===
        after_zt_df['实体上沿'] = after_zt_df.apply(
            lambda r: r['close'] if r['close'] >= r['open'] else r['open'], axis=1
            # lambda r: r['high'] if r['close'] >= r['open'] else r['high'], axis=1
        )
        after_zt_df['实体下沿'] = after_zt_df.apply(
            lambda r: r['open'] if r['close'] >= r['open'] else r['close'], axis=1
        )
        after_zt_df['实体最低价'] = after_zt_df.apply(
            lambda r: r['low'] if r['close'] >= r['open'] else r['low'], axis=1
        )

        # ==================条件1：上下 实体不破边界  不过山
        cond1 = (after_zt_df['实体上沿'] <= upper_bound).all()
        cond2 = (after_zt_df['实体下沿'] >= lower_bound).all()
        cond3 = (after_zt_df['实体最低价'] <= cd_bound).any()  #==============================条件3:回调触底

        # ==================条件2：所有线的收盘价必须在 涨停板价格 之间 ===
        close_upper = zt_close          # 不能高于涨停价
        close_lower = prev_close        # 不能低于前一日的收盘价格
        cond4 = (after_zt_df['close'] <= close_upper).all() and (after_zt_df['close'] >= close_lower).all()

        if cond1 and cond2 and cond3 and cond4:
            gp_name = gp_row.get('name', 'Unknown')
            days_since_zt = len(recent_df) - last_zt_idx - 1  # 涨停日到今天共几天（含尾）
            # if days_since_zt <= 1:
            #     return 双炮台_process_arr

            touch_record = {
                'now_time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'gp_name': gp_name,
                'date': recent_df['date'].iloc[-1],
                'symbol': recent_df['code'].iloc[-1],
                'touch_type': '双炮台',
                'time_type': time_type,
                'direction': '买',
                'sell_u形图形_u_price': '',
                'sell_u形图形_u_n_price': '',
                'sell_u形图形_datetime': '',
                'sell_u形图形_point_datetime': '',
                'buy_u形图形_u_price': zt_close,
                'buy_u形图形_u_n_price': prev_close,
                'buy_u形图形_datetime': recent_df['date'].iloc[last_zt_idx],
                'buy_u形图形_point_datetime': recent_df['date'].iloc[last_zt_idx - 1],
            }
            双炮台_process_arr.append(touch_record)
            print(f"✅ 双炮台信号: {touch_record['symbol']} ({gp_name}) 涨停日 {touch_record['buy_u形图形_datetime']} 共 {days_since_zt} 天")

        return 双炮台_process_arr

    except Exception as e:
        print(f"处理 process_false_breakout 双炮台 数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return []