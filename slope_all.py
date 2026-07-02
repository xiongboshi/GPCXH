import pandas as pd
from database.shape_storage import save_shape_data

def inside_break_all(df: pd.DataFrame, time_type, num_check_points=150):
    """
    内突破（多基准点版本）
    从最新K线开始，向前逐根移动基准点，检测每个基准点是否构成U形。
    内部检测逻辑完全保持不变，仅通过切片实现基准点移动。
    """
    try:
        # ========== 数据反转：最新K线在索引0 ==========
        df = df.iloc[::-1].reset_index(drop=True)

        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)

        max_callback_arr_buy = []  # 存储符合条件的结果
        max_callback_arr_sell = []

        total_len = len(df)
        columns_dp = "symbol, direction, time_type, u形图形_内突_u_price, u形图形_内突_u_bot_price, u形图形_内突_u_top_price"

        # ========== 内部检测函数（完全保留原始逻辑） ==========
        def _run_for_base(df_sub):
            """
            对给定的子DataFrame（末尾为基准点）执行原始内突破检测。
            不修改任何内部代码。
            """
            # 获取基准点数据（子DataFrame的最后一行）
            last_row_close = df_sub['close'].iloc[-1]
            last_row_high = df_sub['high'].iloc[-1]
            last_row_time = df_sub['date'].iloc[-1]

            # 检测参数（基于子DataFrame长度动态计算）
            all_k_num = int(len(df_sub) * 0.6)
            zc_k_num = int(len(df_sub) * 0.38)
            look_k_num = 6

            # 以下代码完全复制自原始 inside_break，未作任何修改
            for i in range(all_k_num):
                if i < look_k_num:
                    continue

                ##################多
                #取最高点吧
                prev_row_high = df_sub['high'].iloc[-i - 1]
                if last_row_close < prev_row_high:
                    range_of_interest = df_sub['high'].iloc[-i - 1:-1]
                    long_condition = (range_of_interest <= prev_row_high).sum() / len(range_of_interest)
                    max_deviation_long = (range_of_interest - prev_row_high).max()
                    if long_condition >= 0.9 and max_deviation_long <= 1.0:
                        range_of_interest = df_sub['low'].iloc[-i - 1:-1]
                        min_price_within_range = range_of_interest.min()
                        min_price_idx = range_of_interest.idxmin()
                        range_max = df_sub['high'].iloc[-i:-i + 5].max()
                        prev_row_5_high = df_sub['high'].iloc[-i - 5:-i + 5].max()
                        if range_max <= prev_row_5_high and prev_row_5_high <= prev_row_high:
                            lookback_period = zc_k_num
                            start_index = -i - 1
                            for j in range(lookback_period):
                                now_row_high = df_sub['high'].iloc[start_index - j]
                                now_row_low = df_sub['low'].iloc[start_index - j]
                                if now_row_high > prev_row_high:
                                    break
                                if prev_row_high != min_price_within_range:
                                    is_zc = (prev_row_high - now_row_low) / (prev_row_high - min_price_within_range) >= 1.1  #支撑
                                else:
                                    continue
                                if is_zc:
                                    ratio = (last_row_high - min_price_within_range) / (prev_row_high - min_price_within_range)
                                    if ratio >= 0.3:
                                        min_price_within_range = df_sub['low'].loc[min_price_idx]
                                        tactics_to_save = {
                                            'date': str(last_row_time),
                                            'tactics_name': '内突破',
                                            'time_type': time_type,
                                            'symbol': df_sub.iloc[-i - 1]['code'],
                                            'direction': '买',
                                            'u形图形_内突_u_price': prev_row_high,
                                            'u形图形_内突_u_now_price': last_row_close,
                                            'u形图形_内突_u_bot_price': min_price_within_range,
                                            'u形图形_内突_u_top_price': 0,
                                            'u形图形_内突_u_k_num': i,
                                            'u形图形_内突_u_point': str(df_sub.iloc[-i - 1]['date'])
                                        }
                                        max_callback_arr_buy.append(tactics_to_save)

                #################空
                prev_row_low = df_sub['low'].iloc[-i - 1]
                if last_row_close > prev_row_low:
                    range_of_interest = df_sub['low'].iloc[-i - 1:-1]
                    short_condition = (range_of_interest >= prev_row_low).sum() / len(range_of_interest)
                    min_deviation_short = (range_of_interest - prev_row_low).min()
                    if short_condition >= 0.9 and min_deviation_short >= -1.0:
                        range_of_interest = df_sub['high'].iloc[-i - 1:-1]
                        max_price_within_range = range_of_interest.max()
                        max_price_idx = range_of_interest.idxmax()
                        range_min = df_sub['low'].iloc[-i:-i + 5].min()
                        prev_row_5_low = df_sub['low'].iloc[-i - 5:-i + 5].min()
                        if range_min >= prev_row_5_low and prev_row_5_low >= prev_row_low:
                            lookback_period = zc_k_num
                            start_index = -i - 1
                            for j in range(lookback_period):
                                now_row_low = df_sub['low'].iloc[start_index - j]
                                now_row_high = df_sub['high'].iloc[start_index - j]
                                if now_row_low < prev_row_low:
                                    break
                                if prev_row_low != max_price_within_range:
                                    is_zc = (now_row_high - prev_row_low) / (max_price_within_range - prev_row_low) >= 1.1  #支撑
                                else:
                                    continue
                                if is_zc:
                                    ratio = (max_price_within_range - last_row_close) / (max_price_within_range - prev_row_low)
                                    if ratio >= 0.3:
                                        max_price_within_range = df_sub['high'].iloc[max_price_idx]
                                        tactics_to_save = {
                                            'date': str(last_row_time),
                                            'tactics_name': '内突破',
                                            'time_type': time_type,
                                            'symbol': df_sub.iloc[-i - 1]['code'],
                                            'direction': '卖',
                                            'u形图形_内突_u_price': prev_row_low,
                                            'u形图形_内突_u_now_price': last_row_close,
                                            'u形图形_内突_u_bot_price': 0,
                                            'u形图形_内突_u_top_price': max_price_within_range,
                                            'u形图形_内突_u_k_num': i,
                                            'u形图形_内突_u_point': str(df_sub.iloc[-i - 1]['date']),
                                        }
                                        max_callback_arr_sell.append(tactics_to_save)




        # ========== 外部循环：逐根移动基准点 ==========
        for k in range(num_check_points):
            if k >= total_len:
                break
            # 取从开头到倒数第 k 根（不含最后 k 根），即基准点为倒数第 k+1 根
            if k == 0:
                df_sub = df.copy()
            else:
                df_sub = df.iloc[:-k].copy()
            # 此时 df_sub.iloc[-1] 是基准点（第 k+1 根）
            # print(f"基准点日期: {df_sub.iloc[-1]['date']}")
            _run_for_base(df_sub)





        # ========== 保存结果（去重） ==========
        if len(max_callback_arr_buy) > 0:
            max_callback_df = pd.DataFrame(max_callback_arr_buy)
            columns_to_check = ['symbol', 'time_type', 'direction', 'u形图形_内突_u_price', 'u形图形_内突_u_bot_price', 'u形图形_内突_u_top_price']
            drop_callback_df = max_callback_df.drop_duplicates(subset=columns_to_check, keep='last')
            save_shape_data(pd.DataFrame(drop_callback_df), 'tactics', columns_dp)

        if len(max_callback_arr_sell) > 0:
            max_callback_df = pd.DataFrame(max_callback_arr_sell)
            columns_to_check = ['symbol', 'time_type', 'direction', 'u形图形_内突_u_price', 'u形图形_内突_u_bot_price', 'u形图形_内突_u_top_price']
            drop_callback_df = max_callback_df.drop_duplicates(subset=columns_to_check, keep='last')
            save_shape_data(pd.DataFrame(drop_callback_df), 'tactics', columns_dp)

        return df

    except Exception as e:
        print(f"处理每个合约的数据出错 inside_break: {e}")