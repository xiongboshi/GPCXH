import os
import pandas as pd
from datetime import datetime, timedelta
from utils.垂线 import hammer_line

touch_to_save = {
    'date': '',
    'symbol': '',
    'touch_type': '',
    'time_type': '',
    'direction': '',
    '小的_U形_datetime': '',
    '小的_U形_point_time': '',
    '小的_U形_u_price': '',
    '小的_U形_n_price': '',
    '小的_U形_k_num': '',
    '大的_U形_datetime': '',
    '大的_U形_point_time': '',
    '大的_U形_u_price': '',
    '大的_U形_n_price': '',
    '大的_U形_k_num': '',
    'limit_date': '',
    'limit_close': '',
    'prev_close': '',
}


def check_Enter_U(df, symbol, time_type, tactics_df):
    """
    检测入场条件
    """
    try:
        # 筛选该股票的多头图形
        zhtx_tactics = tactics_df[tactics_df['symbol'] == symbol].copy()
        if zhtx_tactics.empty:
            return touch_to_save
        

        for _, zhtx in zhtx_tactics.iterrows():

            buy_date = zhtx['大的_U形_datetime']
            buy_small_point = zhtx['小的_U形_point_time']
            buy_price = zhtx['大的_U形_u_price']
            buy_bot_price = zhtx['大的_U形_n_price']
            touch_type = zhtx['touch_type']

                
            #条件1：第一个U形的date之后的最高价格不能大于第一个U的上下差值,U图形失效
            filtered_df = pd.DataFrame([])
            if touch_type == '主升内' or touch_type == '主升外':
                filtered_df = df[pd.to_datetime(df['date']) > pd.to_datetime(buy_small_point)]
            if touch_type == '主升六外':
                filtered_df = df[pd.to_datetime(df['date']) > pd.to_datetime(buy_date)]


            if not filtered_df.empty:
                max_high = filtered_df['high'].max()
                if max_high - buy_price >= buy_price - buy_bot_price:
                    continue
                
                
            #条件2： ★ 涨停检测

            # 从 df 中筛选 small_u_date 到今天的K线
            mask = (pd.to_datetime(df['date']) >= pd.to_datetime(buy_date))
            kline = df[mask].sort_values('date')


            # 取最近 12 个交易日
            recent = kline.tail(12)
            if recent.empty:
                continue

            print(recent)
            # 查找涨停（涨幅 ≥ 9.8，且日期 > buy_date
            limit_days = recent[(recent['pctChg'] >= 9.8) & (recent['date'] > pd.to_datetime(buy_date))]
            if limit_days.empty:
                continue

            first_limit = limit_days.iloc[0]
            limit_date = pd.to_datetime(first_limit['date'])
            limit_close = float(first_limit['close'])

            # 涨停前一日
            prev_days = recent[recent['date'] < limit_date]
            prev_close = float(prev_days.iloc[-1]['close']) if not prev_days.empty else 0.0

            
            # 找到符合条件的配对，返回信号（取最新日期）
            return {
                    'date': zhtx['date'],
                    'symbol': symbol,
                    'touch_type': zhtx['touch_type'],
                    'time_type': time_type,
                    'direction': zhtx['direction'],
                    '小的_U形_datetime': zhtx['小的_U形_datetime'],
                    '小的_U形_point_time': zhtx['小的_U形_point_time'],
                    '小的_U形_u_price': zhtx['小的_U形_u_price'],
                    '小的_U形_n_price': zhtx['小的_U形_n_price'],
                    '小的_U形_k_num': zhtx['小的_U形_k_num'],
                    '大的_U形_datetime': zhtx['大的_U形_datetime'],
                    '大的_U形_point_time': zhtx['大的_U形_point_time'],
                    '大的_U形_u_price': zhtx['大的_U形_u_price'],
                    '大的_U形_n_price': zhtx['大的_U形_n_price'],
                    '大的_U形_k_num': zhtx['大的_U形_k_num'],
                    'limit_date': limit_date,
                    'limit_close': limit_close,
                    'prev_close': prev_close,
                }

        return touch_to_save

    except Exception as e:
        print(f"计算策略函数 入场条件（check_Enter_U）出错: {e}")
        return touch_to_save