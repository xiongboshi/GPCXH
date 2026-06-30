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

# ============ 清除代理设置 ============
import os
# 清除所有代理环境变量
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
# ============ 代理清除结束 ============

# 设置 pandas 打印选项：显示所有行和列
pd.set_option('display.max_rows', None)        # 显示所有行
pd.set_option('display.max_columns', None)     # 显示所有列
pd.set_option('display.width', None)           # 自动调整宽度
pd.set_option('display.max_colwidth', None)    # 列内容不截断

#盘中实时使用

#### 登陆系统 ####
bs.login()

# 使用新浪sina作为数据源
quotation = eq.use('sina')

gp_arr = []  # 所有股票列表
gp_zt_arr = [] #当前所有涨停股票
gp_zt_ph_arr = [] #当前所有涨停数排行

# 存储已处理的股票列表
processed_stocks = set()  # 使用 set 来快速查找和去重


def fetch_stock_list(max_retries=3, delay=5):
    """
    获取股票列表，带重试机制
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试获取股票列表 (第 {attempt + 1} 次)...")
            df = ak.stock_zh_a_spot_em()
            
            # 检查是否获取成功
            if df is not None and not df.empty:
                print(f"✅ 成功获取 {len(df)} 只股票数据")
                return df
            else:
                print(f"⚠️ 获取的股票列表为空，第 {attempt + 1} 次尝试失败")
                
        except Exception as e:
            print(f"❌ 获取失败: {e}")
            
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries - 1:
            wait_time = delay * (attempt + 1)  # 递增等待时间
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
        else:
            print("❌ 多次尝试失败，返回空列表")
            return pd.DataFrame()
    
    # 所有尝试都失败，返回空DataFrame
    return pd.DataFrame()


def restart_program():
    '''
    程序自动启动
    '''
    python = sys.executable
    print('重新启动')
    os.execlp('python', 'python', "init.py", * sys.argv[1:])


# ============ 主程序 ============
for idxx in range(1):
    
    try:
        # 获取实时交易数据 所有股票编码
        all_gp_list = fetch_stock_list()
        
        # 检查是否获取成功
        if all_gp_list.empty:
            print("❌ 获取股票列表失败，退出程序")
            break
            
        print(f"✅ 获取到的股票列表数量: {len(all_gp_list)}")
        
    except Exception as e:
        print(f"❌ 获取所有股票编码异常: {e}")
        all_gp_list = pd.DataFrame()  # 确保是DataFrame
        
    # 存储股票
    if not all_gp_list.empty:
        store_stock_data(all_gp_list, gp_zt_arr)
        print(f"✅ 存储 {len(all_gp_list)} 只股票数据成功")
    else:
        print("⚠️ 输入数据为空，跳过存储")

    gc.collect()  # 手动触发垃圾回收
    
    start1 = time.time()
    gp_arr = get_stock_data('gps_all')  # 获取所有股票数据
    
    # 检查是否获取到数据
    if gp_arr is None or gp_arr.empty:
        print("❌ 从数据库获取股票数据失败")
        time.sleep(60)
        continue
    
    print(f"✅ 从数据库获取 {len(gp_arr)} 只股票数据")
    
    # 找出新股票：不在已处理的股票列表中的股票
    new_gp_arr = gp_arr[~gp_arr['stock_code'].isin(processed_stocks)]
    
    if not new_gp_arr.empty:
        print(f"🔄 发现新股票： {len(new_gp_arr)} 只")
        
        # 执行策略计算
        try:
            # 选择策略模式
            amt.get_threading_list(new_gp_arr, gp_zt_arr, gp_zt_ph_arr, bs)  # 双U形
            # amt.get_threading_list(new_gp_arr, gp_zt_arr, gp_zt_ph_arr, bs)  # 双炮台
            # amt.get_threading_list_realtime(new_gp_arr, gp_zt_arr, gp_zt_ph_arr, bs)  # 仙人指路
            # amt.check_big_main()  # 实时监控大单
            
            # 更新已处理股票列表
            processed_stocks.update(new_gp_arr['stock_code'].tolist())
            print(f"✅ 已处理股票总数: {len(processed_stocks)}")
            
        except Exception as e:
            print(f"❌ 策略计算失败: {e}")
    else:
        print("ℹ️ 没有新股票需要处理")
    
    print("✅ 退出主线程")
    end1 = time.time()
    diff2 = end1 - start1
    print(f'⏱️ 计算花费时间: {diff2:.2f} 秒')
    
    # 清理资源
    gp_arr = []
    gp_zt_arr = []
    gp_zt_ph_arr = []
    del all_gp_list
    gc.collect()
    
    print(f"⏳ 等待 60 秒后继续...")
    time.sleep(60)
    gc.collect()
    
    # 避免链接中断
    if idxx > 0 and idxx % 5 == 0:
        bs.logout()
        time.sleep(2)
        bs.login()
        print("🔄 baostock重新登录成功")