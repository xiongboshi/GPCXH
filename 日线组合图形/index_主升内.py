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

def check_Double_U_主升内(df, symbol, time_type, tactics_df, gp_row):
    """
    检测主升形态（从最新日期向前查找）：
    1. 筛选该股票的基础图形，按日期降序（最新在前）。
    2. 遍历空头图形（卖），取其背部价格（u形图形_内突_u_top_price）。
    3. 验证：从该空头图形的 u_point 日期**之后**（不含当天），K线最低价是否 <= 卖的 u_price（确认下跌）。
    4. 若满足，查找该空头图形之后的多头图形（买），若其 u_price 在空头背部价格的 ±2% 内，则视为信号。
    优先返回最新匹配的组合。
    """
    try:
        # 1. 筛选该股票的基础图形，按日期降序（最新在前）
        stock_tactics = tactics_df[tactics_df['symbol'] == symbol].copy()
        if stock_tactics.empty:
            return touch_to_save

        stock_tactics = stock_tactics.sort_values('date', ascending=False)  # 最新在前

        # 2. 获取空头图形（卖），已按日期降序，所以最新空头在前
        sell_tactics = stock_tactics[stock_tactics['direction'] == '卖']
        if sell_tactics.empty:
            return touch_to_save

        # 3. 获取最新K线日期（df 是升序，iloc[0] 才是最新）
        latest_date = df['date'].iloc[0]

        # 4. 遍历每个空头图形（从最新开始）
        for _, sell_row in sell_tactics.iterrows():
            sell_date = sell_row['date']
            sell_top_price = sell_row['u形图形_内突_u_top_price']  # 背部价格（阻力位）
            sell_price = sell_row['u形图形_内突_u_price']          # 卖的价格（突破位）
            sell_point = sell_row['u形图形_内突_u_point']          # 空头图形形成的时间点

            if pd.isna(sell_top_price) or sell_top_price == 0:
                continue

            # 验证：从 sell_point 之后（不含当天）到最新的K线最低价是否 <= sell_price
            future_df = df[df['date'] > sell_point]  # ✅ 不含当天
            if future_df.empty:
                continue
            min_low = future_df['low'].min()
            if min_low > sell_price:
                continue  # 未跌穿，跳过

            # 查找该空头之后（时间更近）的多头图形
            # 因为 stock_tactics 已降序，所以 date > sell_date 即时间更新（索引更小）
            buy_tactics = stock_tactics[
                (stock_tactics['direction'] == '买') &
                (pd.to_datetime(stock_tactics['u形图形_内突_u_point']) > pd.to_datetime(sell_point))
            ]
            if buy_tactics.empty:
                continue

            
            for _, buy_row in buy_tactics.iterrows():

                buy_price = buy_row['u形图形_内突_u_price']
                buy_point = buy_row['u形图形_内突_u_point']          # 多头图形形成的时间点
                

                #条件3：第一个U形的date之后的最低价格不能小于第一个U的bot价格,U图形失效
                days_before = 6  # 给个缓冲时间
                # 计算 buy_point 减去 days_before 天的日期
                buy_point_before = pd.to_datetime(buy_point) - pd.Timedelta(days=days_before)

                filtered_df = df[(pd.to_datetime(df['date']) > pd.to_datetime(sell_date)) &
                                 (pd.to_datetime(df['date']) < buy_point_before)]
                if filtered_df.empty:
                    continue
                max_high = filtered_df['high'].max()
                if max_high > sell_top_price:
                    print(f"条件3不满足：{symbol} 第一个U形的date之后到第二个U的point时间之间的最高价格 {max_high} > 第一个U的top价格 {sell_top_price}")
                    continue


                # 检查是否有任意多头图形的 u_price 在 sell_top_price 的 ±10% 内
                if abs(buy_price - sell_top_price) / sell_top_price <= 0.2:
                    # 找到符合条件的组合（这是最新的）
                    return {
                        'date': latest_date,
                        'symbol': symbol,
                        'touch_type': '主升内',
                        'time_type': time_type,
                        'direction': '买',
                        '小的_U形_datetime': buy_row['date'],
                        '小的_U形_point_time': buy_row['u形图形_内突_u_point'],
                        '小的_U形_u_price': buy_price,
                        '小的_U形_n_price': buy_row['u形图形_内突_u_bot_price'],
                        '小的_U形_k_num': buy_row['u形图形_内突_u_k_num'],
                        '大的_U形_datetime': sell_row['date'],
                        '大的_U形_point_time': sell_row['u形图形_内突_u_point'],
                        '大的_U形_u_price': sell_top_price,
                        '大的_U形_n_price': sell_row['u形图形_内突_u_bot_price'],
                        '大的_U形_k_num': sell_row['u形图形_内突_u_k_num']
                    }

        return touch_to_save

    except Exception as e:
        print(f"计算策略函数（check_Double_U_主升内）出错: {e}")
        return touch_to_save