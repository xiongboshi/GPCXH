import os
import pandas as pd
from datetime import datetime, timedelta  
from database.makedata import select_日U图形_row_data
from 公用方法.垂线 import hammer_line
from 公用方法.获取k线行情 import get_day_list
import baostock

touch_to_save ={
    'date':'',
    'symbol': '',
    'touch_type': '',
    'time_type': '',
    'direction': '',
    '大的_U形_datetime': '',
    '大的_U形_u_price': '',
}  

def check_Double_U_龙虎突破(bs: baostock, df, symbol, time_type, tactics_df, gp_row):
    '''
    检测 龙虎突破 图形  同级别查看同级别的图形和多级别查看
    对日线前后200根的高点进行  将突破的操作
    '''
    try:
        
        #前一天必须是涨停
        if 'pctChg' in df.columns:
            df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')
            if float(df['pctChg'].iloc[-1]) < 9.8:
                return
            
        
        tactics_name = ['内突破']
        
            
        all_process_arr = []
        
        process_arr = process_false_breakout_peer(bs, tactics_df, df, tactics_name,time_type, gp_row)
        all_process_arr.extend(process_arr) #合并
            
        
        if len(all_process_arr) > 0:
            all_process_df = pd.DataFrame(all_process_arr)
            columns_to_check = ['symbol', 'touch_type', 'time_type', 'direction','大的_U形_datetime','大的_U形_u_price']
            #按照时间排序
            all_process_df['大的_U形_datetime'] = pd.to_datetime(all_process_df['大的_U形_datetime'])
            sorted_df = all_process_df.sort_values(by=['大的_U形_datetime'])
            
            all_process_df_dup = sorted_df.drop_duplicates(subset=columns_to_check, keep='last', ignore_index=True)   #去重
            
            if len(all_process_df_dup) > 0:
                
                last_row_dict = all_process_df_dup.iloc[-1].to_dict()  
                
                return last_row_dict
    
        return touch_to_save
    
    except Exception as e:
        print(f"计算策略函数（check_Double_U_龙虎突破）出错: {e}")
        




def process_false_breakout_peer(bs: baostock, tactics_df, df, tactics_name, time_type, gp_row):
    """
    处理龙虎突破记录的通用函数  同级别的图形
    """
    try:
        
        
        龙虎突破_process_arr = []
        
        # 取出最后一行数据
        last_symbol = df['code'].iloc[-1]
        last_price = df['close'].iloc[-1]
        
        ########################买########################
    
        # 获取当前日期
        start_date = datetime.now()
        now_day = (start_date).strftime("%Y-%m-%d")
        prev_day = (start_date + timedelta(days=-2000)).strftime("%Y-%m-%d")
        
        #取出每只股票400天的周线数据
        week_df = get_day_list(bs, gp_row['gp_id'], prev_day, now_day,
                            "date,code,open,close,high,low,pctChg,volume", 'w')
        
        if len(week_df) > 0:
            
            week_df['high'] = week_df['high'].astype(float)
            #将突破的价格 =  今天的涨停价格到明天的涨停价格之间
            #今天涨停价格
            now_zt_price = gp_row['close'] * 1.1
            #明天涨停价格
            mt_zt_price = now_zt_price * 1.1
            
            week_filtered_df = week_df[(week_df['high'] > now_zt_price) & (week_df['high'] < mt_zt_price)]
            if len(week_filtered_df) > 0:

                # 遍历 week_filtered_df 中的每一行
                for i in range(len(week_filtered_df)):
                    
                    current_row = week_filtered_df.iloc[i]
                    current_time = pd.to_datetime(current_row['date'])  # 或者是其他时间列
                    current_high = current_row['high']
                    
                    #向前40根
                    wk_d_df = week_df[(pd.to_datetime(week_df['date']) < current_time)]
                    if len(wk_d_df) < 40:
                        continue
                    # 然后取最后40根数据
                    last_40_df = wk_d_df.tail(40)
                    prve_max_price = last_40_df['high'].max()
                    
                    #向后40根
                    wk_d_df = week_df[(pd.to_datetime(week_df['date']) > current_time)]
                    if len(wk_d_df) < 40:
                        continue
                    next_max_price = wk_d_df['high'].max() 
                    
                    
                    #同时是前后最高点
                    if current_high > prve_max_price and current_high > next_max_price:
                
                        龙虎突破_process_arr.append({
                            'now_time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            'gp_name': gp_row['name'],
                            'date': df['date'].iloc[-1],
                            'symbol': last_symbol,
                            'touch_type': '龙虎突破',
                            'time_type': time_type,
                            'direction': '买',
                            '小的_U形_u_price': now_zt_price,
                            '大的_U形_datetime': week_filtered_df['date'].iloc[-1],
                            '大的_U形_u_price': week_filtered_df['high'].iloc[-1],
                        })
                
           
        return 龙虎突破_process_arr
                
    except Exception as e:
        print(f"处理 process_false_breakout_peer 数据时出错: {e}")

