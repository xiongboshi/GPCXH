import time
import utils
import baostock as bs
import pandas as pd
import threading as trd
import easyquotation as eq

#### 登陆系统 ####
bs.login()

threads = []  # 线程池
thread_num = 8  # 线程数

# 所有股票行情
quotation = eq.use('sina')  # 新浪 ['sina'] 腾讯 ['tencent', 'qq']

# prefix 参数指定返回的行情字典中的股票代码 key 是否带 sz/sh 前缀
all_gp_list = quotation.market_snapshot(prefix=True)  # 获取所有股票行情

print(all_gp_list)