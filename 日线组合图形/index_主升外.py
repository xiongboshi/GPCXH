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


def check_Double_U_主升外(df, symbol, time_type, tactics_df, gp_row):
    """
    检测“主升外”形态：
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


        # 4. 遍历每个多头图形（从最新开始）
        for _, buy_row in buy_tactics.iterrows():
            buy_date = buy_row['date']
            buy_bot_price = buy_row['u形图形_内突_u_bot_price']  # 背部价格（阻力位）
            buy_price = buy_row['u形图形_内突_u_price']          # 卖的价格（突破位）
            buy_point = buy_row['u形图形_内突_u_point']          # 多头图形形成的时间点
            buy_k_num = buy_row['u形图形_内突_u_k_num']          # 多头图形形成的时间点

            if pd.isna(buy_bot_price) or buy_bot_price == 0:
                continue

            #第一个U形的k线数量必须大于20
            if buy_k_num < 20:
                continue

            # 验证：从 buy_date 之后（不含当天）到最新的K线最低价是否 > buy_price
            future_buy = buy_tactics[pd.to_datetime(buy_tactics['u形图形_内突_u_point']) > pd.to_datetime(buy_date)]  # ✅ 不含当天
            if future_buy.empty:
                continue

            for _, future_row in future_buy.iterrows():

                future_price = future_row['u形图形_内突_u_price']
                future_date = future_row['date']

                # 条件1：第二个u_price > 第一个u_price
                if future_price < buy_price:
                    continue

                # 条件2：第二个的背部价格（此处用 u形图形_内突_u_bot_price）在第一个u_price的±10%内
                back_price_j = future_row['u形图形_内突_u_bot_price']
                if pd.isna(back_price_j) or back_price_j == 0:
                    continue

                ratio = abs(back_price_j - buy_price) / buy_price
                if ratio > 0.10:
                    continue

                #条件3：第二个U形的date之后的最低价格不能小于第一个U的bot价格,U图形失效
                filtered_df = df[pd.to_datetime(df['date']) > pd.to_datetime(future_date)]
                if not filtered_df.empty:
                    min_low = filtered_df['low'].min()
                if min_low <= buy_bot_price:
                    # print(f"条件3不满足：{symbol} 第二个U形的date之后的最低价格 {min_low} <= 第一个U的bot价格 {buy_bot_price}")
                    continue


                # 找到符合条件的配对，返回信号（取最新日期）
                latest_date = df['date'].iloc[0]  # df已反转，iloc[0]为最新
                return {
                    'date': latest_date,
                    'symbol': symbol,
                    'touch_type': '主升外',
                    'time_type': time_type,
                    'direction': '买',
                    '小的_U形_datetime': future_row['date'],
                    '小的_U形_point_time': future_row['u形图形_内突_u_point'],
                    '小的_U形_u_price': future_price,
                    '小的_U形_n_price': future_row['u形图形_内突_u_bot_price'],
                    '小的_U形_k_num': future_row['u形图形_内突_u_k_num'],
                    '大的_U形_datetime': buy_row['date'],
                    '大的_U形_point_time': buy_row['u形图形_内突_u_point'],
                    '大的_U形_u_price': buy_price,
                    '大的_U形_n_price': buy_row['u形图形_内突_u_bot_price'],
                    '大的_U形_k_num': buy_row['u形图形_内突_u_k_num']
                }

        return touch_to_save

    except Exception as e:
        print(f"计算策略函数（check_Double_U_主升外）出错: {e}")
        return touch_to_save