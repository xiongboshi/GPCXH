import pandas as pd
# from A_DB.marketData import MarketDataDB
# from Utils.存储csv数据 import save_tactics_to_csv

from database.shape_storage import save_shape_data

def inside_break(df: pd.DataFrame, time_type) -> pd.DataFrame:
    """
    内突破
    计算策略函数：将最后一根线的收盘价与其前120根线的每一根收盘价进行比较，只要有任何一根K线的收盘价与当前的K线相同，
    并且在判断为多（True）或空（False）的过程中，需额外满足最后一根线和当前线之间的90%的线的close价格若要判断为多，则必须
    小于等于最后一根线的close价格；若要判断为空，则必须大于等于最后一根线的close价格。
    """
    
    
    try:
        # ========== 新增：按日期降序排列，最新K线在索引0 ==========
        df = df.iloc[::-1].reset_index(drop=True)
        
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['close'] = df['close'].astype(float) 
        
        max_callback_arr_buy = [] # 存储符合条件的结果
        max_callback_arr_sell = []
        
        # 对前面300的每一个数据进行检查,现在是计算自身长度
        all_k_num = int(len(df) * 0.7)
        zc_k_num = int(len(df) * 0.28)  #支撑查看k线数
            
        # 获取最后一根K线的收盘价
        last_row_close = df['close'].iloc[-1]
        last_row_high = df['high'].iloc[-1]
        last_row_time = df['date'].iloc[-1]
        
        #表的唯一键值对
        columns_dp = "symbol, direction, time_type, u形图形_内突_u_price, u形图形_内突_u_bot_price, u形图形_内突_u_top_price"
        

        look_k_num = 6
        
        
        # 对前面300的每一个数据进行检查
        for i in range(all_k_num):
            
            # 确保我们查询的历史数据足够（维持距最后一根K线至少60根线的距离）
            if i >= look_k_num:
                
                ##################多
                #取最高点吧
                prev_row_high = df['high'].iloc[-i - 1]
                
                if last_row_close < prev_row_high:#是否在60均线内
                
                    # 最后一根与当前i根线之间的区间数据
                    range_of_interest = df['high'].iloc[-i - 1:-1]
                    # 计算区间中满足多头条件的价格的占比,与U形前高点的close价格进行计算
                    long_condition = (range_of_interest <= prev_row_high).sum() / len(range_of_interest)
                    # 多头判断的额外条件
                    max_deviation_long = (range_of_interest - prev_row_high).max()  # 计算区间内与U形前高点的close价格之差的最大值
                    # 多头条件：90%以上的价格需要小于等于最后一根K线的close价格
                    if long_condition >= 0.8 and max_deviation_long <= 1.0:
                        # 最后一根与当前i根线之间的区间数据
                        range_of_interest = df['low'].iloc[-i - 1:-1]
                        min_price_within_range = range_of_interest.min()  # 多头情况：取U最低价
                        # 找到最低价格的索引
                        min_price_idx = range_of_interest.idxmin()
                        
                        
                        # 计算往后看10根线的最大值和最小值
                        range_max = df['high'].iloc[-i:-i + 5].max()  # 往后看5根线的最大值
                        prev_row_5_high = df['high'].iloc[-i - 5:-i + 5].max()  # 往前后看5根线的最大值
                        if range_max <= prev_row_5_high and prev_row_5_high <= prev_row_high:
                            
                            
                            # 支撑计算
                            # 计算指定回看区间中的最高价和最低价
                            lookback_period = zc_k_num  # 定义回看区间长度
                            start_index = -i - 1  # 从当前K线向后查看
                            for j in range(lookback_period):
                                now_row_high = df['high'].iloc[start_index - j]
                                now_row_low = df['low'].iloc[start_index - j]
                                
                                if now_row_high > prev_row_high:
                                    break
                                
                                
                                # is_zc = (prev_row_high - now_row_high) / (prev_row_high - min_price_within_range) >= 0.9
                                #支持
                                if prev_row_high != min_price_within_range:  # 除数不为零
                                    is_zc = (prev_row_high - now_row_low) / (prev_row_high - min_price_within_range) >= 0.9
                                else:
                                    continue
                                    
                                    
                                if is_zc:
                                    
                                    # 当前价格在U图形的的位置
                                    ratio = (last_row_high - min_price_within_range) / (prev_row_high - min_price_within_range)
                                    if ratio >= 0.3:
                                    
                                        min_price_within_range = df['low'].loc[min_price_idx]   #最低价格 
                                        
                                        # if prev_row_high - min_price_within_range >= 1.0: #空间大于1块钱
                                        
                                        tactics_to_save = {
                                            'date': str(last_row_time),
                                            'tactics_name': '内突破',
                                            'time_type': time_type,
                                            'symbol': df.iloc[-i -1]['code'],
                                            'direction': '买',
                                            'u形图形_内突_u_price': prev_row_high,
                                            'u形图形_内突_u_now_price': last_row_close, # 此处用实际的收盘价替换
                                            'u形图形_内突_u_bot_price': min_price_within_range,
                                            'u形图形_内突_u_top_price': 0,
                                            'u形图形_内突_u_k_num': i,
                                            'u形图形_内突_u_point': str(df.iloc[-i -1]['date'])
                                        }
                                        
                                        max_callback_arr_buy.append(tactics_to_save)
                                            
                                            
                                            
                                        
                                        
                #################空
                #取最低点吧
                prev_row_low = df['low'].iloc[-i - 1]
                
                if last_row_close > prev_row_low:#是否在60均线内
                    
                    
                    # 最后一根与当前i根线之间的区间数据
                    range_of_interest = df['low'].iloc[-i - 1:-1]  
                    # 计算区间中满足空头条件的价格的占比,与U形前高点的close价格进行计算
                    short_condition = (range_of_interest >= prev_row_low).sum() / len(range_of_interest)
                    # 空头判断的额外条件
                    min_deviation_short = (range_of_interest - prev_row_low).min()  # 计算区间内与U形前高点的close价格之差的最小值
                    # 空头条件：90%以上的价格需要大于等于最后一根K线的close价格
                    if short_condition >= 0.8 and min_deviation_short >= -1.0:
                        # 最后一根与当前i根线之间的区间数据
                        range_of_interest = df['high'].iloc[-i - 1:-1]  
                        max_price_within_range = range_of_interest.max()  # 空头情况：取U最高价
                        # 找到最高价格的索引
                        max_price_idx = range_of_interest.idxmax()
                        
                        # 计算往后看10根线的最大值和最小值
                        range_min = df['low'].iloc[-i:-i + 5].min()  # 往后看5根线的最小值
                        prev_row_5_low = df['low'].iloc[-i - 5:-i + 5].min()  # 往前后看5根线的最大值
                        if range_min >= prev_row_5_low and prev_row_5_low >= prev_row_low:
                            
                            
                            # 支撑计算
                            # 计算指定回看区间中的最高价和最低价
                            lookback_period = zc_k_num  # 定义回看区间长度
                            start_index = -i - 1  # 从当前K线向后查看
                            for j in range(lookback_period):
                                now_row_low = df['low'].iloc[start_index - j]
                                now_row_high = df['high'].iloc[start_index - j]
                                
                                if now_row_low < prev_row_low:
                                    break
                                
                                
                                # is_zc = (now_row_low - prev_row_low) / (max_price_within_range - prev_row_low) >= 0.3
                                #支持
                                if prev_row_low != max_price_within_range:  # 除数不为零
                                    is_zc = (now_row_high - prev_row_low) / (max_price_within_range - prev_row_low) >= 0.9
                                else:
                                    continue
                                
                                if is_zc:
                                    
                                    # 当前价格在U图形的的位置
                                    ratio = (max_price_within_range - last_row_close) / (max_price_within_range - prev_row_low)
                                    if ratio >= 0.3:
                                        
                                        max_price_within_range = df['high'].iloc[max_price_idx]  #最高价格
                                            
                                        tactics_to_save = {
                                            'date': str(last_row_time),
                                            'tactics_name': '内突破',
                                            'time_type': time_type,
                                            'symbol': df.iloc[-i -1]['code'],
                                            'direction': '卖',
                                            'u形图形_内突_u_price': prev_row_low,
                                            'u形图形_内突_u_now_price': last_row_close, # 此处用实际的收盘价替换
                                            'u形图形_内突_u_bot_price': 0,
                                            'u形图形_内突_u_top_price': max_price_within_range,
                                            'u形图形_内突_u_k_num': i,
                                            'u形图形_内突_u_point': str(df.iloc[-i -1]['date']),
                                        }
                                        
                                        max_callback_arr_sell.append(tactics_to_save)
                                            
                                        
            
            
            
        # 将结果列表转换为 DataFrame 并去重
        if len(max_callback_arr_buy) >= 2:
            max_callback_df = pd.DataFrame(max_callback_arr_buy)
            columns_to_check = [
                'symbol',
                'time_type',
                'direction',
                'u形图形_内突_u_price',
                'u形图形_内突_u_bot_price',
                'u形图形_内突_u_top_price'
            ]
            drop_callback_df = max_callback_df.drop_duplicates(subset=columns_to_check, keep='last')
            #保存
            save_shape_data(pd.DataFrame(drop_callback_df),'tactics', columns_dp)
        
        
        if len(max_callback_arr_sell) > 2:
            max_callback_df = pd.DataFrame(max_callback_arr_sell)
            columns_to_check = [
                'symbol',
                'time_type',
                'direction',
                'u形图形_内突_u_price',
                'u形图形_内突_u_bot_price',
                'u形图形_内突_u_top_price'
            ]
            drop_callback_df = max_callback_df.drop_duplicates(subset=columns_to_check, keep='last')
            #保存
            save_shape_data(pd.DataFrame(drop_callback_df),'tactics', columns_dp)
            
        return df

    except Exception as e:
        print(f"处理每个合约的数据出错 inside_break: {e}")
