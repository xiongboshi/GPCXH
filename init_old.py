import time
import amount as amt
import pandas as pd
import tushare as ts
import easyquotation as eq
import threading as trd
import extrude as ext
import akshare as ak
import sys
import os
import baostock as bs
from database.makedata import store_stock_data,get_stock_data
import gc


# pro = ts.pro_api()

#盘后使用

#### 登陆系统 ####
bs.login()

# 使用新浪sina作为数据源
quotation = eq.use('sina')

# prefix 参数指定返回的行情字典中的股票代码 key 是否带 sz/sh 前缀
# all_gp_list = quotation.market_snapshot(prefix=True)
# print(all_gp_list)


gp_arr = []  # 所有股票列表

gp_zt_arr = [] #当前所有涨停股票
gp_zt_ph_arr = [] #当前所有涨停数排行


# 存储已处理的股票列表
processed_stocks = set()  # 使用 set 来快速查找和去重




def fetch_stock_list(max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            print(f"尝试获取股票列表 (第 {attempt + 1} 次)...")
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            print(f"获取失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                print("多次尝试失败，返回空列表")
                return pd.DataFrame()
    return pd.DataFrame()




def restart_program():
    '''
    程序自动启动
    '''
    python = sys.executable
    print('重新启动')
    os.execlp('python', 'python',"init.py", * sys.argv[1:])



for idxx in range(1):
    
    try:
        #获取所有股票编码
        all_gp_list = quotation.market_snapshot(prefix=True)
        # print(all_gp_list)
        #获取实时交易数据 所有股票编码
        # all_gp_list = fetch_stock_list()
    except Exception as e:
        print(f"获取所有股票编码: {e}")
        all_gp_list = []
        
    #存储股票
    store_stock_data(all_gp_list, gp_zt_arr)

    gc.collect()  # 手动触发垃圾回收，清理未使用的对象
    
    start1 = time.time()
    gp_arr = get_stock_data('gps_all')  # 获取所有股票数据
    
    # 提取当前已处理的股票，加入到已处理的股票列表中
    current_stocks = gp_arr['stock_code']  # 获取当前股票的 stock_code 列
    
    # 找出新股票：不在已处理的股票列表中的股票
    new_gp_arr = gp_arr[~gp_arr['stock_code'].isin(processed_stocks)]  # 使用 ~ 和 isin 来找到新股票
    
    if not new_gp_arr.empty:  # 如果有新股票，进行计算
        # print(f"正在计算以下新股票：{new_gp_arr['stock_code'].tolist()} {len(new_gp_arr['stock_code'])}")
        print(f"正在计算以下新股票： {len(new_gp_arr['stock_code'])}")
        amt.get_threading_list_history(new_gp_arr, gp_zt_arr, gp_zt_ph_arr, bs)  # 计算新股票  
        
        # 更新已处理股票列表
        processed_stocks.update(new_gp_arr['stock_code'].tolist())  # 将新股票添加到已处理列表
        
    print("退出主线程")
    end1 = time.time()
    diff2 = end1 - start1
    print('计算花费时间:' + str(diff2))  # 计算花费时间
            
    gp_arr = []
    gp_zt_arr = []
    gp_zt_ph_arr = []
    # 手动删除会话对象，释放资源
    del all_gp_list
    gc.collect()  # 手动触发垃圾回收，清理未使用的对象
    time.sleep(60)
    gc.collect()  # 手动触发垃圾回收，清理未使用的对象
    
    
    #避免链接中断
    if idxx > 0 and idxx % 5 == 0:
        bs.logout()
        time.sleep(2)
        bs.login()
    # if idxx > 0 and idxx % 40 == 0:
    #     restart_program() #重启程序
        
        
        
#  restart_program() #重启程序

