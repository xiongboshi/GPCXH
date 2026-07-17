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
    '大的_U形_k_num': ''
}


def check_Double_U_主升六外(df, symbol, time_type, tactics_df, gp_row):
    """
    检测“主升六外”形态：
    1. 筛选该股票的所有多头基础图形（direction='买'），按日期升序。
    2. 遍历每一对 (i, j)，其中 j > i。
    3. 要求：buy_j.u_price > buy_i.u_price（价格逐步抬高）
    4. 要求：buy_j.u形图形_内突_u_bot_price 在 buy_i.u_price 的 ±10% 范围内（背部价格接近前突破位）
    5. 返回最早出现的一组（即时间上最靠前的配对），也可改为返回最新配对。
    """
    try:
        # 筛选该股票的多头图形
        stock_tactics = tactics_df[tactics_df['symbol'] == symbol].copy()
        if stock_tactics.empty:
            return touch_to_save

        stock_tactics = stock_tactics.sort_values('date', ascending=False)  # 最新在前

        # 2. 获取多头图形（买），已按日期降序，所以最新空头在前
        buy_tactics = stock_tactics[stock_tactics['direction'] == '买']
        if buy_tactics.empty:
            return touch_to_save

        # 我们统一处理：将 df 按日期升序排序，以便使用 > 比较。
        df_sorted = df.sort_values('date', ascending=True)

        # 4. 遍历每个多头图形（从最新开始）
        for _, buy_row in buy_tactics.iterrows():
            buy_date = buy_row['date']
            buy_bot_price = buy_row['u形图形_内突_u_bot_price']  # 背部价格（阻力位）
            buy_price = buy_row['u形图形_内突_u_price']          # 卖的价格（突破位）
            buy_point = buy_row['u形图形_内突_u_point']          # 多头图形形成的时间点
            buy_k_num = buy_row['u形图形_内突_u_k_num']          # 多头图形形成的时间点

            if pd.isna(buy_bot_price) or buy_bot_price == 0:
                continue

            #条件1:第一个U形的k线数量必须大于20
            if buy_k_num < 20:
                continue
            
            # 条件2：从 buy_date 之后（不含当天）到最新的K线最高价是否 > buy_price
            future_rows = df_sorted[(pd.to_datetime(df_sorted['date']) > pd.to_datetime(buy_date)) &
                                   (df_sorted['high'] > buy_price) &
                                   (df_sorted['pctChg'] > 9.8)]  # ✅ 不含当天,突破涨停
            if future_rows.empty:
                continue


            # 条件3：进一步筛选：前一天收盘价 < buy_price
            valid_future = []
            for idx, krow in future_rows.iterrows():
                # 找到该日期之前的最近一个交易日
                prev_rows = df_sorted[(pd.to_datetime(df_sorted['date']) < pd.to_datetime(krow['date']))]
                if not prev_rows.empty:
                    prev_close = prev_rows.iloc[-1]['close']  # 最近一个交易日收盘价
                    if prev_close < buy_price:
                        # # 附加条件：多头的date之后到当前涨停之间的k线的最大值不能超过涨停价格
                        # max_high_between = df_sorted[(pd.to_datetime(df_sorted['date']) > pd.to_datetime(buy_date)) &
                        #                              (pd.to_datetime(df_sorted['date']) < pd.to_datetime(krow['date']))]['high'].max()
                        # if max_high_between <= krow['high']:
                        valid_future.append(krow)
                        break  # 一旦找到满足条件的涨停K线，就可以跳出，取最早的或任意一个

            if not valid_future:
                continue

            
            #条件3：第一个U形的date之后的最低价格不能小于第一个U的bot价格,U图形失效
            filtered_df = df[pd.to_datetime(df['date']) > pd.to_datetime(buy_date)]
            if not filtered_df.empty:
                min_low = filtered_df['low'].min()
                if min_low <= buy_bot_price:
                    # print(f"条件3不满足：{symbol} 第一个U形的date之后的最低价格 {min_low} <= 第一个U的bot价格 {buy_bot_price}")
                    continue

            
            # #条件4：第一个U形的date之后的最高价格不能大于第一个U的上下差值,U图形失效
            # if not filtered_df.empty:
            #     max_high = filtered_df['high'].max()
            #     if max_high - buy_price >= buy_price - buy_bot_price:
            #         continue

            
            # 找到符合条件的配对，返回信号（取最新日期）
            latest_date = df['date'].iloc[0]  # df已反转，iloc[0]为最新
            return {
                'date': latest_date,
                'symbol': symbol,
                'touch_type': '主升六外',
                'time_type': time_type,
                'direction': '买',
                '小的_U形_datetime': valid_future[0]['date'],
                '小的_U形_point_time': valid_future[0]['date'],
                '小的_U形_u_price': valid_future[0]['high'],
                '小的_U形_n_price': valid_future[0]['open'],
                '小的_U形_k_num': 0,  # 这里没有具体的K线数量信息
                '大的_U形_datetime': buy_row['date'],
                '大的_U形_point_time': buy_row['u形图形_内突_u_point'],
                '大的_U形_u_price': buy_price,
                '大的_U形_n_price': buy_row['u形图形_内突_u_bot_price'],
                '大的_U形_k_num': buy_row['u形图形_内突_u_k_num']
            }

        return touch_to_save

    except Exception as e:
        print(f"计算策略函数（check_Double_U_主升六外）出错: {e}")
        return touch_to_save