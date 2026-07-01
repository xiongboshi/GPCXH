import os
import pandas as pd
from datetime import datetime, timedelta  
# from database.makedata import select_日U图形_row_data
from utils.垂线 import hammer_line

touch_to_save ={
    'date':'',
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

def check_Double_U_双U形(df, symbol, time_type, tactics_df, gp_row):
    '''
    检测 双U形 图形  同级别查看同级别的图形和多级别查看
    '''
    try:
        
        return touch_to_save
    
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
        
        process_arr = process_false_breakout_peer(tactics_df, df, tactics_name,time_type, gp_row)
        all_process_arr.extend(process_arr) #合并
            
        
        if len(all_process_arr) > 0:
            all_process_df = pd.DataFrame(all_process_arr)
            columns_to_check = ['symbol', 'touch_type', 'time_type', 'direction', '小的_U形_datetime',
                            '小的_U形_u_price', '大的_U形_datetime','大的_U形_u_price']
            #按照时间排序
            all_process_df['大的_U形_datetime'] = pd.to_datetime(all_process_df['大的_U形_datetime'])
            all_process_df['小的_U形_datetime'] = pd.to_datetime(all_process_df['小的_U形_datetime'])
            sorted_df = all_process_df.sort_values(by=['大的_U形_datetime', '小的_U形_datetime'])
            
            all_process_df_dup = sorted_df.drop_duplicates(subset=columns_to_check, keep='last', ignore_index=True)   #去重
            
            if len(all_process_df_dup) > 0:
                
                last_row_dict = all_process_df_dup.iloc[-1].to_dict()  
                
                return last_row_dict
    
        return touch_to_save
    
    except Exception as e:
        print(f"计算策略函数（check_Double_U_双U形）出错: {e}")
        




def process_false_breakout_peer(tactics_df, df, tactics_name, time_type, gp_row):
    """
    处理双U形记录的通用函数  同级别的图形
    """
    try:
        
        
        双U形_process_arr = []
        
        # 取出最后一行数据
        last_symbol = df['code'].iloc[-1]
        last_price = df['close'].iloc[-1]
        
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
                
                
                #大U的空间
                if max_row['u形图形_内突_u_k_num'] < 60:
                    continue
                
                #小U的空间
                if min_row['u形图形_内突_u_k_num'] < 10:
                    continue
                
                #相同U突破值不看
                if max_row['u形图形_内突_u_price'] == min_row['u形图形_内突_u_price']:
                    continue
                
                max_u_time = max_row['date']
                max_u_point_time = max_row['u形图形_内突_u_point']
                max_u_k_num = max_row['u形图形_内突_u_k_num']
                min_u_time = min_row['date']
                min_u_point_time = min_row['u形图形_内突_u_point']
                min_u_k_num = min_row['u形图形_内突_u_k_num']
                
                #当前价格必须过小U图形的一半
                if last_price < (min_row['u形图形_内突_u_price'] - min_row['u形图形_内突_u_bot_price']) / 6 + min_row['u形图形_内突_u_bot_price']:
                    continue
                
                
                
                #小U的U_price 必须过半
                if min_row['u形图形_内突_u_price'] < (max_row['u形图形_内突_u_price']  - max_row['u形图形_内突_u_bot_price']) / 2 + max_row['u形图形_内突_u_bot_price']:
                    continue
                
                
                # 检查 k_num 是否一个比另一个大  
                if max_row['u形图形_内突_u_k_num'] > min_row['u形图形_内突_u_k_num']:  
                    # 检查价格是否在范围内  
                    if (max_row['u形图形_内突_u_bot_price'] <= min_row['u形图形_内突_u_bot_price']) \
                        and (max_row['u形图形_内突_u_price'] + 0.4 >= min_row['u形图形_内突_u_price']):  
                            
                    
                            
                            #小U形状价格过半
                            if  (min_row['u形图形_内突_u_price'] - max_row['u形图形_内突_u_bot_price']) \
                                / (max_row['u形图形_内突_u_price'] - max_row['u形图形_内突_u_bot_price']) >= 0.4 and \
                                round((min_row['u形图形_内突_u_bot_price'] - max_row['u形图形_内突_u_bot_price']) \
                                / (max_row['u形图形_内突_u_price'] - max_row['u形图形_内突_u_bot_price']), 2) >= 0.1:
                                    
                                    
                                #小U3倍以上缩量回调
                                filtered_df = df[(pd.to_datetime(df['date']) >= (min_u_point_time+ timedelta(days=-6))) & (pd.to_datetime(df['date']) <= (min_u_point_time+ timedelta(days=+4)))]
                                filtered_df = filtered_df[filtered_df['volume'] > 0]
                                prve_max_volume = filtered_df['volume'].max() 
                                prve_max_high = filtered_df['high'].max() 
                                prve_max_60 = filtered_df['ma_gray_60'].max() 
                                filtered_df = df[(pd.to_datetime(df['date']) > min_u_point_time) & (pd.to_datetime(df['date']) < min_u_time)]
                                filtered_df = filtered_df[filtered_df['volume'] > 0]
                                next_min_volume = filtered_df['volume'].min()
                                # next_min_volume = filtered_df['volume'].mean() #平均值

                                #小U前高必须穿60
                                if prve_max_high <= prve_max_60:
                                    continue
                                
                                if prve_max_volume / next_min_volume >= 2.5:

                                        
                                    #小U底部必须踩60均线
                                    filtered_rows = filtered_df[filtered_df['low'] <= filtered_df['ma_gray_60'] + 0.2]
                                    if len(filtered_rows) > 0:
                                        
                                        
                                        #大于大U的u_price价格两根线不看
                                        filtered_df = df[(pd.to_datetime(df['date']) > min_u_point_time)]
                                        filtered_rows = filtered_df[filtered_df['high'] > max_row['u形图形_内突_u_price']+ 0.4]
                                        if len(filtered_rows) > 1:
                                            continue
                                        filtered_rows = filtered_df[filtered_df['low'] < min_row['u形图形_内突_u_bot_price']]
                                        if len(filtered_rows) >= 1:
                                            continue
                                        
                                        
                                        #小U里面80%都在60均线之上
                                        # filtered_row = df[(pd.to_datetime(df['date']) > min_u_point_time) & (pd.to_datetime(df['date']) < min_u_time)] 
                                        # # 计算低于 ma_gray_60 的行数
                                        # condition_met = filtered_row[filtered_row['low'] < filtered_row['ma_gray_60']]
                                        # # 计算低于 ma_gray_60 的行占比是否大于等于 30%
                                        # percentage_above_ma_gray_60 = len(condition_met) / len(filtered_row)
                                        # if percentage_above_ma_gray_60 > 0.5:
                                        #     continue
                                        
                                                
                                        #查询反U图形是否形成背靠背
                                        tactics_row = select_日U图形_row_data('tactics', last_symbol, '卖', str(max_row['u形图形_内突_u_point']), 
                                                                            str(min_row['u形图形_内突_u_point']))
                                        if len(tactics_row) > 0 and \
                                            min_row['u形图形_内突_u_bot_price'] >= float(tactics_row['u形图形_内突_u_price']) - 0.5 and \
                                            min_row['u形图形_内突_u_price'] > float(tactics_row['u形图形_内突_u_price']):
                                                
                                                
                                            #中间不能有其他图形
                                            filtered_df = df[(pd.to_datetime(df['date']) > pd.to_datetime(max_row['u形图形_内突_u_point'])) & 
                                                                (pd.to_datetime(df['date']) < pd.to_datetime(tactics_row['u形图形_内突_u_point']))]
                                            if len(filtered_df) > 0:
                                                    max_high_price = filtered_df['high'].max() 
                                                    if max_high_price > max_row['u形图形_内突_u_price'] + 0.2:
                                                        continue
                                                    
                                                    
                                            #必须是反向假突破
                                            filtered_df = df[(pd.to_datetime(df['date']) > pd.to_datetime(tactics_row['u形图形_内突_u_point'])) &
                                                                (pd.to_datetime(df['date']) < pd.to_datetime(min_row['u形图形_内突_u_point']))]
                                            if len(filtered_df) > 0:
                                                min_low_price = filtered_df['low'].min() 
                                                
                                                # print(min_u_point_time)
                                                # print(max_u_point_time)
                                                # print(tactics_row)
                                                
                                                if min_low_price < float(tactics_row['u形图形_内突_u_price']):
                                                    
                                                    #小U太抽不看，空锤线大于等于3根不看
                                                    filtered_df = df[(pd.to_datetime(df['date']) >= (min_u_point_time+ timedelta(days=-6))) &
                                                                        (pd.to_datetime(df['date']) <= (min_u_point_time+ timedelta(days=+4)))]
                                
                                                    is_czx_num = 0
                                                    for item_index, item_row in filtered_df.iterrows():
                                                        if hammer_line(pd.DataFrame([item_row]), '卖'):
                                                            is_czx_num += 1
                                                    if is_czx_num >= 2:
                                                        print(f' k线太抽了 {last_symbol}  {is_czx_num}')
                                                        return 双U形_process_arr
                                                    
                                                    #小U最高线为3倍垂线不看
                                                    max_index = filtered_df['high'].idxmax()  # 获取最高值的索引
                                                    highest_row = filtered_df.loc[max_index]  # 获取该行
                                                    if hammer_line(pd.DataFrame([highest_row]), '3倍'):
                                                        print(f'3倍垂线 k线太抽了 {last_symbol}  {is_czx_num}')
                                                        return 双U形_process_arr
                                                    
                                
                                        
                                                    双U形_process_arr.append({
                                                        'now_time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                                        'gp_name': gp_row['name'],
                                                        'date': df['date'].iloc[-1],
                                                        'symbol': last_symbol,
                                                        'touch_type': '双U形',
                                                        'time_type': time_type,
                                                        'direction': '买',
                                                        '小的_U形_datetime': min_row['date'],
                                                        '小的_U形_point_time': min_u_point_time,
                                                        '小的_U形_u_price': min_row['u形图形_内突_u_price'],
                                                        '小的_U形_n_price': min_row['u形图形_内突_u_bot_price'],
                                                        '小的_U形_k_num': min_row['u形图形_内突_u_k_num'],
                                                        '大的_U形_datetime': max_row['date'],
                                                        '大的_U形_point_time': max_u_point_time,
                                                        '大的_U形_u_price': max_row['u形图形_内突_u_price'],
                                                        '大的_U形_n_price': max_row['u形图形_内突_u_bot_price'],
                                                        '大的_U形_k_num': max_row['u形图形_内突_u_k_num']
                                                    })
                                
        
           
        return 双U形_process_arr
                
    except Exception as e:
        print(f"处理 process_false_breakout_peer 数据时出错: {e}")

