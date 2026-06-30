import numpy as np 
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from 日线组合图形.index_双U形 import check_Double_U_双U形
from 日线组合图形.index_双炮台 import check_bowl_shaped_双炮台
from 日线组合图形.index_仙人指路 import check_bowl_shaped_仙人指路
from 日线组合图形.index_突破即回调 import check_bowl_shaped_突破即回调
from 日线组合图形.index_碗形 import check_bowl_shaped_碗形
from 日线组合图形.index_龙虎突破 import check_Double_U_龙虎突破
from database.makedata import get_tactics_data
from database.makedata import save_shape_data
from 公用方法.macd import calculate_macd
import baostock



def check_touch_type(bs: baostock, df, symbol, time_type, gp_row):
    '''
    检测组合图形 数据
    '''
    try:
        #关闭所有警告⚠
        pd.set_option('future.no_silent_downcasting', True)

        tactics_df = get_tactics_data('tactics', '日线')
            
        if len(tactics_df) > 0:
            print('进入============检测组合图形')
            
            # #macd 还是看空不看
            # calculate_macd(df)
            # if df['MACD_bar'].iloc[-1] < -0.15:
            #     return
            
            
            # 将无法转换的值转换为 NaN，然后再转换为 float
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            # 如果需要，可以用特定值替换 NaN，例如 0
            df['volume'] = df['volume'].fillna(-1).astype(float) 
            
            df['open'] = df['open'].astype(float)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            

            
            tactics_df['date'] = pd.to_datetime(tactics_df['date'], errors='coerce')  # 转换类型
            tactics_df['u形图形_内突_u_point'] = pd.to_datetime(tactics_df['u形图形_内突_u_point'], errors='coerce')  # 转换类型
            tactics_df['u形图形_内突_u_price'] = tactics_df['u形图形_内突_u_price'].astype(float)  
            tactics_df['u形图形_内突_u_bot_price'] = tactics_df['u形图形_内突_u_bot_price'].astype(float)  
            tactics_df['u形图形_内突_u_k_num'] = tactics_df['u形图形_内突_u_k_num'].astype(float)  
            
                
            data_entries = []
                    
            with ThreadPoolExecutor() as executor:
                strategies = [
                    # executor.submit(check_bowl_shaped_双炮台, df, symbol, time_type, tactics_df, gp_row),
                    executor.submit(check_Double_U_双U形, df, symbol, time_type, tactics_df, gp_row),
                    # executor.submit(check_Double_U_龙虎突破, bs , df, symbol, time_type, tactics_df, gp_row),
                    # executor.submit(check_bowl_shaped_突破即回调, df, symbol, time_type, tactics_df, gp_row),
                    # executor.submit(check_bowl_shaped_碗形, df, symbol, time_type, tactics_df, gp_row),
                ]
            

            # 循环调用各策略函数，并检查返回的字典是否全为NA
            for strategy in as_completed(strategies):    
                result = strategy.result()  # 获取 Future 的结果 
                if result is not None and isinstance(result, dict) and not all(pd.isnull(v) for v in result.values()):
                    data_entries.append(result)  
                    
            
            
            if data_entries:
                new_data_df = pd.DataFrame(data_entries)
                # 将空字符串替换为 NaN  
                new_data_df.replace('', np.nan, inplace=True)  
                # # 过滤掉全为 NaN 的行  
                filtered_data = new_data_df.dropna(how='all') 

                if len(filtered_data) > 0:
                    
                    #表的唯一键值对
                    columns_dp = "symbol, time_type, touch_type"
                    
                    #过滤的名称
                    # unique_columns = ['symbol', 'touch_type', 'time_type', 'direction', 'tp_time', 'ht_time', '小的_U形_u_price', '大的_U形_datetime']
                    unique_columns = ['symbol', 'touch_type', 'time_type', 'direction', '小的_U形_u_price', '大的_U形_datetime']
                    
                    # market_db.save_or_show_unique_data_from_db(filtered_data, '组合图形', columns_dp, unique_columns)
                    
                    # 去重（根据unique_columns）  
                    df_unique = filtered_data.drop_duplicates(subset= unique_columns, keep='last')
                    print('===========================来新股票了============================')
                    print('===========================来新股票了============================')
                    print('===========================来新股票了============================')
                    print(df_unique)
                    save_shape_data(df_unique, '组合图形', columns_dp)
            
    except Exception as e:
        print(f"计算策略函数（check_touch_type）出错: {e}")
        






def check_touch_type_pure(bs: baostock, df, symbol, time_type, gp_row):
    '''
    检测组合图形 数据 目前专用双炮台 仙人指路
    '''
    try:
        #关闭所有警告⚠
        pd.set_option('future.no_silent_downcasting', True)
        
        # 将无法转换的值转换为 NaN，然后再转换为 float
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        # 如果需要，可以用特定值替换 NaN，例如 0
        df['volume'] = df['volume'].fillna(-1).astype(float) 
        
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        

        
        df['date'] = pd.to_datetime(df['date'], errors='coerce')  # 转换类型
        
            
        data_entries = []
                
        with ThreadPoolExecutor() as executor:
            strategies = [
                # executor.submit(check_bowl_shaped_双炮台, df, symbol, time_type, df, gp_row)
                executor.submit(check_bowl_shaped_仙人指路, df, symbol, time_type, df, gp_row)
            ]
        

        # 循环调用各策略函数，并检查返回的字典是否全为NA
        for strategy in as_completed(strategies):
            result = strategy.result()  # 获取 Future 的结果
            if result is not None and isinstance(result, dict) and not all(pd.isnull(v) for v in result.values()):
                data_entries.append(result)
                
        

        
        if data_entries:
            new_data_df = pd.DataFrame(data_entries)
            # 将空字符串替换为 NaN  
            new_data_df.replace('', np.nan, inplace=True)
            # # 过滤掉全为 NaN 的行  
            filtered_data = new_data_df.dropna(how='all') 

            if len(filtered_data) > 0:
                
                #表的唯一键值对
                columns_dp = "symbol, time_type, touch_type"
                
                #过滤的名称
                # unique_columns = ['symbol', 'touch_type', 'time_type', 'direction', 'tp_time', 'ht_time', '小的_U形_u_price', '大的_U形_datetime']
                # unique_columns = ['symbol', 'touch_type', 'time_type', 'direction', '小的_U形_u_price', '大的_U形_datetime']
                unique_columns = ['symbol', 'touch_type', 'time_type', 'direction']
                
                # market_db.save_or_show_unique_data_from_db(filtered_data, '组合图形', columns_dp, unique_columns)
                
                # 去重（根据unique_columns）  
                df_unique = filtered_data.drop_duplicates(subset= unique_columns, keep='last')
                print(df_unique)
                save_shape_data(df_unique, '组合图形', columns_dp)
            
            
    except Exception as e:
        print(f"计算策略函数（check_touch_type）出错: {e}")
        