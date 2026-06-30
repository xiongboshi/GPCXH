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

def check_bowl_shaped_碗形(df, symbol, time_type, tactics_df, gp_row):
    '''
    检测 碗形 图形  同级别查看同级别的图形
    '''
    try:
        
        #如果前三天涨连续涨了2个板不看(只做1，2板)
        if 'pctChg' in df.columns:
            df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')
            if (float(df['pctChg'].iloc[-1]) > 9 and float(df['pctChg'].iloc[-2]) > 9) or \
                (float(df['pctChg'].iloc[-1]) > 9 and float(df['pctChg'].iloc[-3]) > 9):
                return
        else:
            return
        
        tactics_name = ['内突破']
        
        all_process_arr = []
        
        process_arr = process_false_breakout(tactics_df, df, tactics_name,time_type, gp_row)
        all_process_arr.extend(process_arr)  #合并
            
        
        if len(all_process_arr) > 0:
            all_process_df = pd.DataFrame(all_process_arr)
            
            #按照时间排序
            all_process_df['sell_u形图形_datetime'] = pd.to_datetime(all_process_df['sell_u形图形_datetime'])
            all_process_df['buy_u形图形_datetime'] = pd.to_datetime(all_process_df['buy_u形图形_datetime'])

            # 首先基于 'sell_u形图形_datetime' 排序
            sorted_by_sell = all_process_df.sort_values(by='sell_u形图形_datetime')
            last_row_sell = sorted_by_sell.iloc[-1].to_dict() if not sorted_by_sell.empty else {}

            # 然后基于 'buy_u形图形_datetime' 排序
            sorted_by_buy = all_process_df.sort_values(by='buy_u形图形_datetime')
            last_row_buy = sorted_by_buy.iloc[-1].to_dict() if not sorted_by_buy.empty else {}
                                
            # 比较两个字典中的日期，返回最新的那个
            if last_row_sell and last_row_buy: 
                final_row = last_row_sell if last_row_sell['sell_u形图形_datetime'] > last_row_buy['buy_u形图形_datetime'] else last_row_buy
            else:
                final_row = last_row_sell if last_row_sell else last_row_buy  # 如果其中一个是空的，就返回另一个
                

            return final_row
    
        return touch_to_save
                
    except Exception as e:
        print(f"计算策略函数（check_bowl_shaped_碗形）出错: {e}")
        




def process_false_breakout(tactics_df, df, tactics_name, time_type, gp_row):
    """
    处理碗形记录的通用函数
    """
    try:
        
        碗形_process_arr = []
        
        last_symbol = df['code'].iloc[-1]
        last_price = df['close'].iloc[-1]
        last_high_price = df['high'].iloc[-1]
        
        filtered_df_buy = tactics_df.loc[
            (tactics_df['symbol'] == last_symbol) &
            (tactics_df['tactics_name'].isin(tactics_name)) &
            (tactics_df['time_type'] == '日线') &
            (tactics_df['direction'] == '买')
        ]
        
        filtered_df_sell = tactics_df.loc[
            (tactics_df['symbol'] == last_symbol) &
            (tactics_df['tactics_name'].isin(tactics_name)) &
            (tactics_df['time_type'] == '日线') &
            (tactics_df['direction'] == '卖')
        ]
        
        if len(filtered_df_buy) > 0 and len(filtered_df_sell) > 0:
            
            # 遍历买操作，尝试找到对应的卖操作  
            for buy_index, buy_row in filtered_df_buy.iterrows():  
                
                buy_u形图形_内突_u_price = float(buy_row['u形图形_内突_u_price'])
                buy_u形图形_内突_u_bot_price = float(buy_row['u形图形_内突_u_bot_price'])
                buy_u形图形_datetime = buy_row['date']
                buy_u形图形_point_datetime = buy_row['u形图形_内突_u_point']
                buy_u形图形_u_k_num = buy_row['u形图形_内突_u_k_num']
                
                for sell_index,sell_row in filtered_df_sell.iterrows():
                    
                    sell_u形图形_内突_u_price = float(sell_row['u形图形_内突_u_price'])
                    sell_u形图形_内突_u_top_price = float(sell_row['u形图形_内突_u_top_price'])
                    sell_u形图形_datetime = sell_row['date']
                    sell_u形图形_point_datetime = sell_row['u形图形_内突_u_point']
                    sell_u形图形_u_k_num = sell_row['u形图形_内突_u_k_num']
                    
                    # if buy_u形图形_u_k_num > 40 or sell_u形图形_u_k_num > 40:
                    
                    
                        
                    ###############第一种： 卖在前 上，买在后 下##############
                    # if buy_u形图形_u_k_num > sell_u形图形_u_k_num:
                    #     continue
                    
                    if buy_u形图形_u_k_num < 20:
                        continue
                    
                    if  sell_u形图形_u_k_num < 15:
                        continue
                    
                    
                    if abs(sell_u形图形_内突_u_price - buy_u形图形_内突_u_price) <= 0.1:
                        
                        #前面的U图形必须已经突破过
                        filtered_row = df[(pd.to_datetime(df['date']) > sell_u形图形_datetime) & (pd.to_datetime(df['date']) < buy_u形图形_point_datetime)] 
                        if len(filtered_row) <= 0:
                            continue
                        
                        min_price_row = filtered_row.loc[filtered_row['low'].idxmin()]
                        min_price = min_price_row['low']
                        min_price_datetime = min_price_row['date']
                        if min_price > sell_u形图形_内突_u_price:
                            continue
                        
                        #后U必须是最大的那个
                        filtered_row = df[(pd.to_datetime(df['date']) > min_price_datetime) & (pd.to_datetime(df['date']) < buy_u形图形_point_datetime)] 
                        if len(filtered_row) <= 0:
                            continue
                        
                        filtered_row_max_price = filtered_row['high'].max()
                        if filtered_row_max_price > buy_u形图形_内突_u_price:
                            continue
                        
                        
                        #后面U的pricey应该小于前U的top_price
                        if buy_u形图形_内突_u_price > (sell_u形图形_内突_u_top_price - sell_u形图形_内突_u_price) / 2 + sell_u形图形_内突_u_price:
                            continue
                        
                        #前U的price价格90%必须在60线之上
                        filtered_row = df[(pd.to_datetime(df['date']) > sell_u形图形_point_datetime) & (pd.to_datetime(df['date']) < sell_u形图形_datetime)] 
                        filtered_rows = filtered_row[filtered_row['low'] < filtered_row['ma_gray_60']]
                        if len(filtered_rows) > 4:
                            continue
                        #前U中间不能有线
                        filtered_rows = filtered_row[filtered_row['low'] < sell_u形图形_内突_u_price]
                        if len(filtered_rows) > 1:
                            continue
                        
                        
                        #前U的top_price应该小于最高价格
                        filtered_df = df[(pd.to_datetime(df['date']) >= (sell_u形图形_point_datetime+ timedelta(days=-20))) 
                                        & (pd.to_datetime(df['date']) <= (sell_u形图形_point_datetime+ timedelta(days=+4)))]
                        
                        filtered_row_max_price = filtered_df['high'].max()
                        if sell_u形图形_内突_u_top_price > filtered_row_max_price + 0.4:
                            continue
                        
                        
                        #最后一根线必须在后面U里面之上
                        if last_high_price < buy_u形图形_内突_u_bot_price:
                            continue
                                    
                        
                        #大于后U的u_price价格两根线不看
                        filtered_df = df[(pd.to_datetime(df['date']) > buy_u形图形_point_datetime)]
                        filtered_rows = filtered_df[filtered_df['high'] > buy_u形图形_内突_u_price]
                        if len(filtered_rows) >= 8:
                            continue
                                
                            
                        #两个U的时间不能重叠
                        if buy_u形图形_point_datetime > sell_u形图形_datetime:
                                
                            touch_to_save = {
                                'now_time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                'gp_name': gp_row['name'],
                                'date': df['date'].iloc[-1],
                                'symbol': last_symbol,
                                'touch_type': '碗形',
                                'time_type': time_type,
                                'direction': '买',
                                'sell_u形图形_u_price': sell_u形图形_内突_u_price,
                                'sell_u形图形_u_n_price': sell_u形图形_内突_u_top_price,
                                'sell_u形图形_datetime': sell_u形图形_datetime,
                                'sell_u形图形_point_datetime': sell_u形图形_point_datetime,
                                'buy_u形图形_u_price': buy_u形图形_内突_u_price,
                                'buy_u形图形_u_n_price': buy_u形图形_内突_u_bot_price,
                                'buy_u形图形_datetime': buy_u形图形_datetime,
                                'buy_u形图形_point_datetime': buy_u形图形_point_datetime,
                            }
                            
                            碗形_process_arr.append(touch_to_save)
                            
                    
                    
        return 碗形_process_arr
                            
    except Exception as e:
        print(f"处理 process_false_breakout 数据时出错: {e}")

