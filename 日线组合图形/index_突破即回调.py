import os
import pandas as pd
from datetime import datetime, timedelta  
from 公用方法.垂线 import hammer_line
from database.makedata import select_日U图形_row_data

touch_to_save = {
    'date':'',
    'symbol': '',
    'touch_type': '',
    'time_type': '',
    'direction': '',
    'tp_price': '',
    'tp_time': '',
    'tp_point_time': '',
    'big_u_d': '',
    'now_tp_price': '', 
    'ht_price': '',
    'ht_time': '',
    'ht_point_time': ''
}


def check_bowl_shaped_突破即回调(df, symbol, time_type, tactics_df, gp_row):
    '''
    检测 正突破即回调
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
        
        process_arr = process_false_breakout(tactics_df, df, tactics_name, time_type, gp_row)
        all_process_arr.extend(process_arr) #合并
            
        if len(all_process_arr) > 0:
            all_process_df = pd.DataFrame(all_process_arr)
            
            columns_to_check = ['symbol', 'touch_type', 'time_type', 'direction', 'tp_price', 'big_u_d']
            
            #按照时间排序
            all_process_df['tp_time'] = pd.to_datetime(all_process_df['tp_time'])
            all_process_df['ht_time'] = pd.to_datetime(all_process_df['ht_time'])
            sorted_df = all_process_df.sort_values(by=['tp_time', 'ht_time'])
            
            all_process_df_dup = sorted_df.drop_duplicates(subset=columns_to_check, keep='last', ignore_index=True)   #去重
            
            if len(all_process_df_dup) > 0:
            
                last_row_dict = all_process_df_dup.iloc[-1].to_dict()  
                return last_row_dict
    
        return touch_to_save
                
    except Exception as e:
        print(f"计算策略函数（check_bowl_shaped_正突破即回调）出错: {e}")
        
        
        
def process_false_breakout(tactics_df, df, tactics_name, time_type, gp_row):
    """
    处理突破即回调 记录的通用函数
    """
    try:
        突破即回调_process_arr = []
        
        last_symbol = df['code'].iloc[-1]
        
        
        ########################买########################
        filtered_df_buy = tactics_df.loc[
            (tactics_df['symbol'] == last_symbol) &
            (tactics_df['tactics_name'].isin(tactics_name)) &
            (tactics_df['time_type'] == '日线') &
            (tactics_df['direction'] == '买')
        ]
        
        filtered_df_buy = filtered_df_buy.sort_values(by='u形图形_内突_u_k_num', ascending=False)
        
        # 遍历图形并查找符合条件的图形对  
        for i in range(len(filtered_df_buy)):  # 至少需要一个后续图形进行比较  
            max_row = filtered_df_buy.iloc[i]  
            for j in range(len(filtered_df_buy)):  # 从当前图形的下一个开始遍历  
                min_row = filtered_df_buy.iloc[j]  
        
                if max_row['u形图形_内突_u_k_num'] >= 40:
                    
                    #小U
                    if min_row['u形图形_内突_u_k_num'] > 30:
                        continue
            
                    #大U图形的空间比小U图形的空间大
                    if max_row['u形图形_内突_u_k_num'] / min_row['u形图形_内突_u_k_num'] < 2:
                        continue
                    
                        
                    #判断小图形回调位置
                    if min_row['u形图形_内突_u_price'] > max_row['u形图形_内突_u_price']:
                        
                        #回调的U形状底部价格在不超过前U的一半
                        if ((max_row['u形图形_内突_u_price'] - max_row['u形图形_内突_u_bot_price']) / 3 + max_row['u形图形_内突_u_bot_price'] < min_row['u形图形_内突_u_bot_price']):
                            
                            #回调发现时间大于U的时间
                            if min_row['u形图形_内突_u_point'] > max_row['u形图形_内突_u_point']:
                                
                                
                                #靠近突破价格
                                if  min_row['u形图形_内突_u_bot_price'] < max_row['u形图形_内突_u_price'] + 0.5:
                                    
                                    max_u_point_time = max_row['u形图形_内突_u_point']
                                    min_u_point_time = min_row['u形图形_内突_u_point']
                                    min_u_time = min_row['date']
                                    
                                    #大U的左侧必须在60均线之上
                                    filtered_df = df[(pd.to_datetime(df['date']) >= (max_u_point_time+ timedelta(days=-4))) & (pd.to_datetime(df['date']) <= (max_u_point_time+ timedelta(days=+4)))]
                                    filtered_rows = filtered_df[filtered_df['low'] <= filtered_df['ma_gray_60']]
                                    if len(filtered_rows) > 0:
                                        continue
                                    
                                    #小U2.5倍以上缩量回调
                                    filtered_df = df[(pd.to_datetime(df['date']) >= (min_u_point_time+ timedelta(days=-4))) & (pd.to_datetime(df['date']) <= (min_u_point_time+ timedelta(days=+4)))]
                                    filtered_df = filtered_df[filtered_df['volume'] > 0]
                                    prve_max_volume = filtered_df['volume'].max() 
                                    filtered_df = df[(pd.to_datetime(df['date']) > min_u_point_time) & (pd.to_datetime(df['date']) < min_u_time)]
                                    filtered_df = filtered_df[filtered_df['volume'] > 0]
                                    next_min_volume = filtered_df['volume'].min()
                                    # next_min_volume = filtered_df['volume'].mean() #平均值
                                    
                                    if prve_max_volume / next_min_volume >= 2:
                                        
                                        #小U底部必须踩20均线
                                        filtered_rows = filtered_df[filtered_df['low'] <= filtered_df['ma_red_20'] + 0.05]
                                        
                                        #或者最后一根线是垂线
                                        is_czx = hammer_line(df)
                                        
                                        if len(filtered_rows) > 0 or is_czx:

                                                
                                                # #大于小U的u_price价格两根线不看
                                                filtered_df = df[(pd.to_datetime(df['date']) > min_u_point_time)]
                                                filtered_rows = filtered_df[filtered_df['high'] > min_row['u形图形_内突_u_price']]
                                                if len(filtered_rows) > 2:
                                                    continue
                                                filtered_rows = filtered_df[filtered_df['low'] < min_row['u形图形_内突_u_bot_price']]
                                                if len(filtered_rows) >= 1:
                                                    continue
                                                
                                                #查询反U图形是否形成背靠背
                                                tactics_row = select_日U图形_row_data('tactics', last_symbol, '卖', str(max_row['u形图形_内突_u_point']), 
                                                                                   str(min_row['u形图形_内突_u_point']))
                                                if len(tactics_row) > 0 and \
                                                    min_row['u形图形_内突_u_bot_price'] >= float(tactics_row['u形图形_内突_u_price']) - 1.5 and \
                                                    min_row['u形图形_内突_u_price'] > float(tactics_row['u形图形_内突_u_price']):
                                                        
                                                    
                                                    #中间不能有其他图形
                                                    filtered_df = df[(pd.to_datetime(df['date']) > pd.to_datetime(max_row['u形图形_内突_u_point'])) & 
                                                                     (pd.to_datetime(df['date']) < pd.to_datetime(tactics_row['u形图形_内突_u_point']))]
                                                    if len(filtered_df) > 0:
                                                            max_high_price = filtered_df['high'].max() 
                                                            if max_high_price > max_row['u形图形_内突_u_price']:
                                                                continue
                                                    
                                                                        
                                                    #必须是反向假突破
                                                    filtered_df = df[(pd.to_datetime(df['date']) > pd.to_datetime(tactics_row['u形图形_内突_u_point'])) & 
                                                                     (pd.to_datetime(df['date']) < pd.to_datetime(min_row['u形图形_内突_u_point']))]
                                                    if len(filtered_df) > 0:
                                                        min_low_price = filtered_df['low'].min() 
                                                        if min_low_price < float(tactics_row['u形图形_内突_u_price']):
                                                            
                                                            #大U到小U之间的最高价格应该就是小U的u_price价格
                                                            max_high_price = filtered_df['high'].max() 
                                                            if max_high_price > min_row['u形图形_内突_u_price']:
                                                                continue
                                                            
                                                            #小U太抽不看，空锤线大于等于3根不看
                                                            filtered_df = df[(pd.to_datetime(df['date']) >= (min_u_point_time+ timedelta(days=-6))) &
                                                                             (pd.to_datetime(df['date']) <= (min_u_point_time+ timedelta(days=+4)))]
                                                            is_czx_num = 0
                                                            for item_index, item_row in filtered_df.iterrows():
                                                                if hammer_line(pd.DataFrame([item_row]), '卖'):
                                                                    is_czx_num += 1
                                                            if is_czx_num >= 2:
                                                                print(f' k线太抽了 {last_symbol}  {is_czx_num}')
                                                                return 突破即回调_process_arr
                                                            
                                                            #小U最高线为2倍垂线不看
                                                            max_index = filtered_df['high'].idxmax()  # 获取最高值的索引
                                                            highest_row = filtered_df.loc[max_index]  # 获取该行
                                                            if hammer_line(pd.DataFrame([highest_row]), '2倍'):
                                                                print(f'2倍垂线 k线太抽了 {last_symbol}  {is_czx_num}')
                                                                return 突破即回调_process_arr
                                                            
                                                
                                                
                                                            touch_to_save = {
                                                                'now_time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                                                'gp_name': gp_row['name'],
                                                                'date': df['date'].iloc[-1],
                                                                'symbol': last_symbol,
                                                                'touch_type': '正突破即回调',
                                                                'time_type': time_type,
                                                                'direction': '买',
                                                                'tp_price': max_row['u形图形_内突_u_price'],
                                                                'tp_time': max_row['date'],
                                                                'tp_point_time': max_row['u形图形_内突_u_point'],
                                                                'big_u_d': max_row['u形图形_内突_u_bot_price'],
                                                                'now_tp_price': min_row['u形图形_内突_u_price'], 
                                                                'ht_price': min_row['u形图形_内突_u_bot_price'],
                                                                'ht_time': min_row['date'],
                                                                'ht_point_time': min_row['u形图形_内突_u_point'],
                                                            }
                                                            
                                                            突破即回调_process_arr.append(touch_to_save)
                
            
        return 突破即回调_process_arr
                            
    except Exception as e:
        print(f"处理 突破即回调 process_false_breakout 数据时出错: {e}")

