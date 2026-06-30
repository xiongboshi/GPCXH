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

def check_bowl_shaped_仙人指路(df, symbol, time_type, tactics_df, gp_row):
    '''
    检测 仙人指路 图形  同级别查看同级别的图形
    '''
    try:
        tactics_name = ['仙人指路']
        
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
        print(f"计算策略函数（check_bowl_shaped_仙人指路）出错: {e}")
        




def process_false_breakout(tactics_df, df, tactics_name, time_type, gp_row):
    '''
    检测 仙人指路 图形：
    在最近10日内，某日满足：
      1. 最高价较前一日收盘涨幅 ≥ 6%
      2. 收盘价从最高价回撤 ≥ 30%（(high - close) / high ≥ 0.3）
      3. 当日K线为阳线（close > open）
      4. 往后的所有K线的收盘价不能低于这条大阳线的开盘价格向下1%
      5. 往后的所有K线的最高价不能大于这条大阳线的最高价
      6. 大阳线之前的三根K线中没有涨停的情况
    '''
    try:
        仙人指路_process_arr = []

        
        #个股价格大于40不看
        if float(gp_row['now']) > 40:
            return 仙人指路_process_arr

        required_cols = ['code', 'date', 'open', 'close', 'high', 'low', 'pctChg']
        for col in required_cols:
            if col not in df.columns:
                return 仙人指路_process_arr

        df = df.copy()
        for col in ['open', 'close', 'high', 'low', 'pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 只看最近15个交易日（含今天）
        recent_df = df.tail(15).reset_index(drop=True)
        if len(recent_df) < 2:
            return 仙人指路_process_arr

        # 标记是否找到符合条件的大阳线
        found_valid_candle = False
        valid_candle_open_price = None
        valid_candle_high_price = None

        
        today_str = datetime.now().strftime('%Y-%m-%d')  # 获取今天的日期
        
        # 先向前遍历找到符合条件的大阳线
        for i in range(1, len(recent_df)):
            prev_close = recent_df.loc[i - 1, 'close']
            curr = recent_df.loc[i]
            high = curr['high']
            open_price = curr['open']
            close = curr['close']
            low = curr['low']
            symbol = str(curr['code']).zfill(6)
            gp_name = gp_row.get('name', 'Unknown')
            date_str = curr['date']
            date_str = str(date_str)[:10]

                

            # 如果是今天的K线，跳过(不看今天)
            if date_str == today_str:
                continue

            # 条件1: 最高价较前一日收盘涨 ≥ 8%
            high_gain = (high / prev_close - 1)
            if high_gain < 0.08:
                continue

            # 条件2: 收盘价从最高价回撤 ≥ 30%
            retraction_from_high = (high - close) / high
            if retraction_from_high < 0.03:
                continue

            # 条件3: 当日K线为阳线（close > open）
            if close <= open_price:
                continue

            # 如果满足上述三个条件，标记这条K线，并记录其开盘价和最高价
            found_valid_candle = True
            valid_candle_open_price = open_price
            valid_candle_high_price = high
            break

        # 如果找到了符合条件的大阳线，再向后检查剩余的K线，并且向前检查前三根K线是否有涨停
        if found_valid_candle:
            # 检查大阳线之前的三根K线是否有涨停
            for k in range(max(0, i-3), i):
                prev_close_k = recent_df.loc[k - 1, 'close'] if k > 0 else recent_df.loc[0, 'close']
                curr_k = recent_df.loc[k]
                close_k = curr_k['close']
                pct_chg_k = (close_k / prev_close_k - 1)

                # 检查是否有涨停（假设涨停标准为涨幅≥10%）
                if pct_chg_k >= 0.1:
                    found_valid_candle = False
                    break

            # 遍历大阳线之后的所有K线
            for j in range(i + 1, len(recent_df)):
                next_close = recent_df.loc[j, 'close']
                next_high = recent_df.loc[j, 'high']
                
                # 条件4: 后续所有K线的收盘价不能低于大阳线的开盘价格向下5%
                if next_close < valid_candle_open_price - valid_candle_open_price * 0.05:
                    found_valid_candle = False
                    break
                
                # 条件5: 后续所有K线的最高价不能大于大阳线的最高价
                if next_high > valid_candle_high_price:
                    found_valid_candle = False
                    break

            if found_valid_candle:
                print(f"🔍仙人指路: {symbol} ({gp_name}) 日期: {date_str} 开盘: {open_price:.2f}, 收盘: {close:.2f} (涨幅: {(close/prev_close - 1):.1%}), 回撤占比: {retraction_from_high:.1%}")

                # 记录结果到返回数组中
                touch_record = touch_to_save.copy()
                touch_record.update({
                    'now_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'gp_name': gp_name,
                    'date': date_str,
                    'symbol': symbol,
                    'touch_type': '仙人指路',
                    'time_type': time_type,
                    'direction': '观察',
                    'buy_u形图形_u_price': high,
                    'buy_u形图形_u_n_price': prev_close,
                    'buy_u形图形_datetime': date_str,
                    'buy_u形图形_point_datetime': recent_df.loc[i - 1, 'date'] if i - 1 >= 0 else '',
                })
                仙人指路_process_arr.append(touch_record)

        return 仙人指路_process_arr

    except Exception as e:
        print(f"处理 process_false_breakout 仙人指路 数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return []