
from database.sqlite import SQLiteDB

import pandas as pd
from 公用方法.换手率 import calculate_turnover_rate

def check_stock_market(code):
    '''
    检查是哪个交易所的股票
    '''
    if code.startswith('6'):
        return 'sh'  # 上海证券交易所
    elif code.startswith(('0', '3')):
        return 'sz'  # 深圳证券交易所
    else:
        return 'Unknown'  # 未知市场或非股票代码
    



def store_stock_data(all_gp_list, gp_zt_arr):
    '''
    存储股票数据
    支持两种输入格式：
      1. akshare DataFrame（推荐）
      2. easyquotation 字典（兼容）
    '''
    try:
        if all_gp_list is None or (hasattr(all_gp_list, '__len__') and len(all_gp_list) == 0):
            print("输入数据为空，跳过存储")
            return

        # === 统一转换为标准 DataFrame ===
        if isinstance(all_gp_list, dict):
            ######################################## 来自 easyquotation（新浪）的字典格式
            rows = []
            for code_with_prefix, data in all_gp_list.items():
                # 提取纯数字代码（去掉 sh/sz）
                if code_with_prefix.startswith(('sh', 'sz')):
                    code = code_with_prefix[2:]
                    jys = code_with_prefix[:2]
                else:
                    code = code_with_prefix
                    jys = check_stock_market(code)

                # 跳过指数（如 sh000001）—— 通常6位但非股票
                if not code.isdigit() or len(code) != 6:
                    continue
                # 剔除创业板、科创板
                if code.startswith(('300', '301', '688')):
                    continue

                # 尝试计算涨跌幅（避免除零）
                close = data.get('close', 0)
                now = data.get('now', 0)
                if close == 0:
                    chg_pct = 0.0
                else:
                    chg_pct = round((now - close) / close * 100, 2)

                # 剔除创业板、科创板
                if chg_pct > 11.0 or chg_pct < -11.0:
                    continue

                # 注意：新浪的 volume 是成交额（元），turnover 是成交量（股？）
                # 但实际测试发现 turnover 单位可能是“手”（100股），需谨慎
                # 这里保守处理：假设 turnover 是成交量（股）
                volume = data.get('turnover', 0)  # 成交量（股）
                amount = data.get('volume', 0)    # 成交额（元）

                # 计算换手率（需要流通股本，但新浪不提供 → 无法计算！）
                # 所以这里只能设为 None 或跳过
                turnover_rate = None  # 新浪数据无法计算换手率

                rows.append({
                    '代码': code,
                    '名称': data.get('name', ''),
                    '最新价': now,
                    '昨收': close,
                    '今开': data.get('open', 0),
                    '最高': data.get('high', 0),
                    '最低': data.get('low', 0),
                    '成交量': volume,       # 股
                    '成交额': amount,       # 元
                    '涨跌幅': chg_pct,
                    '涨跌额': now - close,
                    '振幅': round((data.get('high', 0) - data.get('low', 0)) / close * 100, 2) if close > 0 else 0,
                    '流通市值': None,       # 新浪不提供
                    '总市值': None,         # 新浪不提供
                    '量比': None,           # 需要历史数据
                    '换手率': turnover_rate  # 无法计算
                })
            df = pd.DataFrame(rows)
        elif isinstance(all_gp_list, pd.DataFrame):
            ###################################################################### 来自 akshare，直接使用
            df = all_gp_list.copy()
        else:
            print(f"不支持的数据类型: {type(all_gp_list)}")
            return

        # 如果 DataFrame 为空，退出
        if df.empty:
            print("转换后数据为空，跳过存储")
            return

        # === 后续逻辑保持不变（基于统一后的 df）===
        db = SQLiteDB('gps_database.db')
        fields = {
            'stock_code': 'TEXT',
            'name': 'TEXT',
            'now': 'REAL',
            'close': 'REAL',
            'open': 'REAL',
            'volume': 'REAL',
            '涨跌': 'REAL',
            '涨跌百分比': 'REAL',
            'high': 'REAL',
            'low': 'REAL',
            '流通市值': 'REAL',
            '总市值': 'REAL',
            '量比': 'REAL',
            '振幅': 'REAL',
            '换手': 'TEXT'
        }

        # 删除并重建表
        if db.check_table_exists('gps_all'):
            db.conn.execute("DROP TABLE gps_all")
        db.create_table('gps_all', fields)

        if db.check_table_exists('tactics'):
            db.conn.execute("DELETE FROM tactics")

        # 遍历统一后的 df
        for _, row in df.iterrows():
            code = str(row['代码']).zfill(6)  # 确保6位

            # 剔除创业板、科创板
            if code.startswith(('300', '301', '688')):
                continue
            

            # 剔除 ST
            name = str(row['名称'])
            if 'ST' in name.upper():
                continue

            # 剔除退市/无效数据
            if  pd.isna(row['最新价']) or pd.isna(row['昨收']) or row['最新价'] <= 0 or row['昨收'] <= 0:
                continue

            # 换手率处理（akshare 有，新浪无）
            turnover_rate = row.get('换手率', None)
            if turnover_rate is None:
                # 新浪数据无法获取换手率，可设为 -1 或跳过
                # 这里选择保留，但后续过滤时注意
                turnover_rate = -1.0
            else:
                turnover_rate = float(turnover_rate)

            # 换手率过滤（注意：新浪数据此处为 -1，会跳过）
            if turnover_rate > 30:
                continue

            # 交易所
            jys_code = check_stock_market(code)
            if jys_code == 'Unknown':
                continue
            stock_code = jys_code + code

            # 涨停判断（注意：盘后可能已收盘，涨跌幅准确）
            chg_pct = float(row['涨跌幅'])
            if chg_pct >= 9.8:
                gp_zt_arr.append(stock_code)

                
            # 剔除创业板、科创板
            if chg_pct > 11.0 or chg_pct < -11.0:
                continue

            stock_entry = {
                'stock_code': stock_code,
                'name': name,
                'now': float(row['最新价']),
                'close': float(row['昨收']),
                'open': float(row['今开']),
                'volume': float(row['成交量']),  # 注意：akshare 是“手”，新浪是“股”？需统一！
                '涨跌': float(row['涨跌额']),
                '涨跌百分比': chg_pct,
                'high': float(row['最高']),
                'low': float(row['最低']),
                '流通市值': float(row['流通市值']) if pd.notna(row.get('流通市值')) else 0.0,
                '总市值': float(row['总市值']) if pd.notna(row.get('总市值')) else 0.0,
                '量比': float(row['量比']) if pd.notna(row.get('量比')) else 0.0,
                '振幅': float(row['振幅']) if pd.notna(row.get('振幅')) else 0.0,
                '换手': turnover_rate
            }

            db.insert_row('gps_all', stock_entry)

        print(f"成功存储 {len(gp_zt_arr)} 只涨停股，共 {db.count_rows('gps_all')} 条记录")
        db.close()

    except Exception as e:
        import traceback
        print(f"Error in store_stock_data: {e}")
        traceback.print_exc()

        

# def store_stock_data(all_gp_list, gp_zt_arr):
#     '''
#     存储股票数据
#     剔除创业板和科创板 股票
#     剔除st股票
#     剔除涨幅小于5%的股票
#     '''
#     try:
        
#         if len(all_gp_list) <= 0:
#             return
            
#         db = SQLiteDB('gps_database.db')
        
#         # Create the table if it doesn't exist
#         fields =  {
#             'stock_code': 'TEXT',
#             'name': 'TEXT',
#             'now': 'REAL',
#             'close': 'REAL',
#             'open': 'REAL',
#             'volume': 'REAL',
#             '涨跌': 'REAL',
#             '涨跌百分比': 'REAL',
#             'high': 'REAL',
#             'low': 'REAL',
#             '流通市值': 'REAL',
#             '总市值': 'REAL',
#             '量比': 'REAL',
#             '振幅': 'REAL',
#             '换手': 'TEXT'
#         }


#         # 删除不需要的表  
#         if db.check_table_exists('gps_all'): 
#             delete_query = f"DROP TABLE IF EXISTS {'gps_all'};"  
#             try:  
#                 c = db.conn.cursor()  
#                 c.execute(delete_query)  
#                 db.conn.commit()
#                 # print(f"Deleted table: {table}")  
#             except Exception as e:  
#                 print(f"Failed to delete table {'gps_all'}: {e}") 
                
#         #创建表
#         db.create_table('gps_all', fields)
            
#         #删除原始数据    
#         # db.conn.execute(f"DELETE FROM {'gps_all'};")
#         if db.check_table_exists('tactics'): 
#             db.conn.execute(f"DELETE FROM {'tactics'};")
            
        
#         for gp_index, gp_row in all_gp_list.iterrows():  
            
#             turnover_rate = gp_row['换手率']
            
            
#             #剔除已经退市股票
#             if turnover_rate <= 0:
#                 continue
            
#             #剔除sz300创业板和sh688科创板 股票
#             if gp_row['代码'].startswith('300') or gp_row['代码'].startswith('688'):
#                 continue
            
#             # 剔除st股票
#             if 'st' in gp_row['名称'] or 'ST' in gp_row['名称']:
#                 continue
            
            
#             # #剔除涨幅小于5%的股票
#             # if gp_row['涨跌幅'] < 7 or gp_row['涨跌幅'] > 10.5:  #实盘
#             #     continue
            
            
#             # 剔除不满足的换手率
#             if turnover_rate < -0.5 or turnover_rate > 30:
#                 continue
            
            
#             ##########################开始############################
            
#             #交易所代码
#             jys_code = check_stock_market(gp_row['代码'])
#             if jys_code == 'Unknown':
#                 continue
#             stock_code = jys_code + gp_row['代码']
            
            
#             #保存当前涨停股票
#             if gp_row['涨跌幅'] >= 9.8:
#                 gp_zt_arr.append(stock_code)
                
            
#             # # 测试
#             # if gp_row['代码'] not in ['603690','002427','002549','002900','002342','600126', '600610', '002724', '000601', '002278', '002406', '603677', '002093',
#             #                         '603716', '603206', '000665', '605100', '002196', '000409', '600371']:
#             # if gp_row['代码'] not in ['301156']:
#             #     continue
            

            
            
#             stock_entry = {
#                 'stock_code': stock_code,
#                 'name': gp_row['名称'],
#                 'now': gp_row['最新价'],
#                 'close': gp_row['昨收'],
#                 'open': gp_row['今开'],
#                 'volume': gp_row['成交量'],
#                 '涨跌': gp_row['涨跌额'],
#                 '涨跌百分比': gp_row['涨跌幅'],
#                 'high': gp_row['最高'],
#                 'low': gp_row['最低'],
#                 '流通市值': gp_row['流通市值'],
#                 '总市值': gp_row['总市值'],
#                 '量比': gp_row['量比'],
#                 '振幅': gp_row['振幅'],
#                 '换手': turnover_rate
#             }
            
#             db.insert_row('gps_all', stock_entry)
            
        
#         print("所有股票数据已成功存储到数据库中！")
        
#         db.close()


#     except Exception as e:
#         print(f"Error in save_data with {store_stock_data}: {e}")



def get_stock_data(table_name):
    '''
    取出表里面的数据
    '''
    
    try:
        db = SQLiteDB('gps_database.db')
        gp_arr = db.fetch_all_data(table_name)
        
        db.close()
        return gp_arr
    
    except Exception as e:
        print(f"Error in save_data with {get_stock_data}: {e}")




            
    
def save_shape_data(df, table_name, columns_dp = 'date, stock_code'):  
    '''
    保存各种策略数据的通用方法
    '''
    try:  
        
        if df.empty:  
            print("数据为空，不必保存")
            return  
        
        
        # lock = FileLock("data.lock")
        # with lock:
        db = SQLiteDB('gps_database.db')
        
        
        # 确保所有时间戳列都被转换为字符串  
        for col in df.columns:  
            if pd.api.types.is_datetime64_any_dtype(df[col].dtype):  
                df[col] = df[col].astype(str) 
                
        # 检查表是否存在，不存在则创建  
        if not db.check_table_exists(table_name): 
            # 创建或检查表  
            check_and_create_table(db, table_name, df.columns, columns_dp)  
            
            
        # #删除原始数据    
        # db.conn.execute(f"DELETE FROM {table_name};")
        

        # 准备 SQL 语句  
        columns = ', '.join(df.columns)  
        placeholders = ', '.join(['?' for _ in df.columns])  
        update_arr = columns_dp.split(',')
        # # 假设我们只想在 datetime 冲突时更新其他字段（除了 datetime 和 symbol）  
        # update_cols = ', '.join([f"{col} = EXCLUDED.{col}" for col in df.columns if col not in update_arr])  
        # insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) ON CONFLICT ({columns_dp}) DO UPDATE SET {update_cols}"  
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) ON CONFLICT ({columns_dp}) DO NOTHING"

        # 准备数据  
        data_to_insert = [tuple(row) for index, row in df.iterrows()]  

        # 执行 SQL 语句  
        db.executemany(insert_query, data_to_insert)  
        # 关闭
        db.close()

    except Exception as e:  
        print(f"Error in save_shape_data with {table_name}: {e}")  
        
        
        
def check_and_create_table(db:SQLiteDB, table_name, df_columns,  columns_dp = 'datetime, symbol'):
    # 去重后构建列
    unique_columns = set(df_columns)  # 使用集合去除重复列名
    columns_sql = ', '.join([f"{col} TEXT" for col in unique_columns])
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {columns_sql},
        PRIMARY KEY ({columns_dp})
    );
    """
    try:
        db.execute_query(create_table_query)
    except Exception as e:
        print(f"Error creating table {table_name}: {e}")
        
        
        
        
    
def read_table_data(db:SQLiteDB , table_name, time_type = None):  
    '''  
    从SQLite数据库中读取表数据并返回DataFrame  
    '''  
    try:  
        # lock = FileLock("data.lock")
        # with lock:
        # db = SQLiteDB('gps_database.db')

        # 检查表是否存在  
        cursor = db.conn.cursor()  # 假设SQLiteDB类有一个connection属性  
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")  
        if cursor.fetchone() is None:  
            # print(f"Table {table_name} does not exist.")  
            # 关闭
            db.close()
            return pd.DataFrame()  # 返回空DataFrame  

        # # 构造查询语句  
        # query = f"SELECT * FROM {table_name}"  
        # columns, data = db.executequery(query)  
        # df = pd.DataFrame(data, columns=columns) 
        
        # 构造查询语句  
        if time_type is not None:
            query = f"SELECT * FROM {table_name} WHERE time_type = ?"  # 使用 ? 占位符
            # 执行查询
            cursor.execute(query, (time_type,))
        else:
            query = f"SELECT * FROM {table_name}"  
            cursor.execute(query)

        columns = [column[0] for column in cursor.description]  # 获取列名
        data = cursor.fetchall()  # 获取所有数据
        df = pd.DataFrame(data, columns=columns) 
        
        
        return df  
    except Exception as e:  
        print(f"Error read_table_data== {table_name}: {e}")  
        
    
    
def  get_tactics_data(table_name, time_type = None):
    try:
        db = SQLiteDB('gps_database.db')
        df = read_table_data(db , table_name, time_type) 
        # 关闭
        db.close()
        
        return df
        
    except Exception as e:
        print(f"Error creating table: {e}")
        
        
        
        
        
        
def select_日U图形_row_data(table_name, symbol, direction, start_time, end_time):
    '''
    根据表名称 查询 日U图形 对应的数据 根据传入的时间范围进行匹配
    查找同方向、时间范围内，u形图形_内突_u_k_num 最大的行
    '''
    try:  
        db = SQLiteDB('gps_database.db')

        # 检查表是否存在，不存在则返回
        if not db.check_table_exists(table_name): 
            return []

        # 根据传入的 direction 动态生成 SQL 查询条件
        query = f"""
            SELECT * FROM {table_name} 
            WHERE direction = ? 
            AND symbol = ?
            AND u形图形_内突_u_point > ? 
            AND date < ?
        """
        params = (direction, symbol, start_time, end_time)

        # 执行查询并返回结果
        df = pd.read_sql_query(query, db.conn, params=params)

        # 如果查询结果为空，直接返回空列表
        if df.empty:
            return []
        # 根据 u形图形_内突_u_k_num 字段，找出最大值对应的行
        # 确保 u形图形_内突_u_k_num 是数值类型
        df['u形图形_内突_u_k_num'] = pd.to_numeric(df['u形图形_内突_u_k_num'], errors='coerce')
        max_idx = df['u形图形_内突_u_k_num'].idxmax()
        max_row = df.loc[max_idx]
        

        # 提交事务
        db.conn.commit()

        # 关闭数据库连接
        db.close()

        return max_row

    except Exception as e:  
        print(f"Error in select_日U图形_row_data== {table_name}: {e}")
        return []
    
    