# import time
from datetime import datetime, timedelta, time
import pandas as pd
# import baostock
from slope import inside_break
from 日线组合图形.index import check_touch_type, check_touch_type_pure
from 公用方法.个股板块排行 import is_top_industry,check_continuous_buy_blocks_per_stock_with_email
from 公用方法.个股概念排行 import is_hot_concept
from 公用方法.分时直线拉升 import mintun_zx_ls
# from 公用方法.获取k线行情 import get_day_list
from 公用方法.getGPData import get_all_tickers, get_historical_kline


# 创建报价对象
# quotation = eq.use('sina')  
# 所有股票行情
# quotation = eq.use('tencent')  # 新浪 ['sina'] 腾讯 ['tencent', 'qq']


def get_up_win(gp_id, gp_row, list: pd.DataFrame, time_type = '日线'):
    '''
    组装今日当前日k，开始策略执行
    '''
    try:
        
        inside_break(list, time_type)
        
        df = pd.DataFrame([])
        #向前查看40天
        total_days_to_subtract = 150
        for idx in range(total_days_to_subtract):
            # 递减之前的天数
            if idx == 0:
                df = list
            else:
                # 使用 .loc 来避免 SettingWithCopyWarning
                df = list.loc[:len(list) - idx - 1]  # 显示指定行范围

            # 检查 df 是否为空
            if df.empty:
                print(f"Warning: DataFrame is empty after subtracting {idx} days.")
                break  # 如果为空，退出循环
            
            df = pd.DataFrame(df)
            inside_break(df, time_type)
        
    except Exception as e:
        print('get_up_win()=>err:'+str(e))



def get_threading_list(gp_arr, gp_zt_arr, gp_zt_ph_arr, bs: baostock):
    '''
    获取涨幅数据
    gp_zt_arr 目前涨停的股票
    '''
    try:
        
        for gp_index, gp_row in gp_arr.iterrows():  
            
            
            # 获取当前日期
            start_date = datetime.now()
            now_day = (start_date).strftime("%Y-%m-%d")
            # gp_id = gp_row['stock_code'][0:2]+'.'+gp_row['stock_code'][2:]
            gp_id = gp_row['stock_code'][2:] + '.' + gp_row['stock_code'][0:2].upper()
            gp_row['gp_id'] = gp_id
            
            #个股价格大于40不看
            if float(gp_row['now']) > 40:
                continue
            
            
            
            # # 下午2点后不看策略
            # two_pm = time(14, 0, 0)
            # if start_date.time() > two_pm:
            #     print("当前时间大于下午14.00点  不允许开仓了")
            #     return
            
            
            #个股行业板块排名是否在前6(板块强度)
            # result = is_top_3_industry(gp_row['stock_code'], (start_date).strftime("%Y%m%d"), gp_zt_arr, gp_zt_ph_arr)
            # if result == False:
            #     continue
            
            
            prev_day = (start_date + timedelta(days=-300)).strftime("%Y-%m-%d")
            
            
            
            #取出每只股票300天的日线数据
            df = get_historical_kline(gp_id, prev_day, now_day)

            if len(df) < 100:
                continue
            
                        
            # #分时2分钟涨幅大于5%同时个股涨幅大于6%(分时直线拉升)
            # result = mintun_zx_ls(gp_row, gp_row['stock_code'][2:],6,2,5)
            # if result == False:
            #     continue
            
            
            df['ma_orange_10'] = df['close'].rolling(10).mean()
            df['ma_red_20'] = df['close'].rolling(20).mean()
            df['ma_gray_60'] = df['close'].rolling(60).mean()
            
            #计算基础U图形
            get_up_win(gp_id, gp_row, df)
            
            
            #计算组合图形(日线背靠背图形)
            check_touch_type(bs, df, df.iloc[-1]['code'], '日线', gp_row)
            
            #######################################
            
            # #取出每只股票400天的周线数据
            # prev_day = (start_date + timedelta(days=-4000)).strftime("%Y-%m-%d")
            # week_df = get_day_list(bs, gp_row['gp_id'], prev_day, now_day,
            #                     "date,code,open,close,high,low,pctChg,volume", 'w')
            
            # if len(week_df) < 100:
            #     continue
            
            # #计算基础U图形
            # get_up_win(gp_id, gp_row, week_df, '周线')
            

            
    except Exception as e:
        print('get_threading_list()=>err:'+str(e))









def get_threading_list_history(gp_arr, gp_zt_arr, gp_zt_ph_arr):
    '''
    历史数据-可用于回撤
    获取 纯k线,不做图形计算  
    gp_zt_arr 目前专用双炮台,仙人指路
    '''
    try:
        
        for gp_index, gp_row in gp_arr.iterrows():  
            
            
            # 获取当前日期
            start_date = datetime.now()
            now_day = (start_date).strftime("%Y-%m-%d")
            # gp_id = gp_row['stock_code'][0:2]+'.'+gp_row['stock_code'][2:]
            gp_id = gp_row['stock_code'][2:] + '.' + gp_row['stock_code'][0:2].upper()
            gp_row['gp_id'] = gp_id
            
            #个股价格大于40不看
            if float(gp_row['now']) > 40:
                continue
            
            
            # # 个股行业板块排名是否在前10(板块强度)
            # result = is_top_industry(gp_row['stock_code'], (start_date).strftime("%Y%m%d"), gp_zt_arr, gp_zt_ph_arr)
            # if result == False:
            #     continue

            # # 个股行业概念排名是否在前10(板块强度)
            # result = is_hot_concept(gp_row['stock_code'], (start_date).strftime("%Y%m%d"), gp_zt_arr, gp_zt_ph_arr)
            # if result == False:
            #     continue

            
            
            #取出每只股票30天的日线数据
            prev_day = (start_date + timedelta(days=-30)).strftime("%Y-%m-%d") 
            df = get_day_list(gp_id, prev_day, now_day,
                                "date,code,open,close,high,low,pctChg,volume")

            if len(df) < 15:
                continue
            
                        
            # #分时2分钟涨幅大于5%同时个股涨幅大于6%(分时直线拉升)
            # result = mintun_zx_ls(gp_row, gp_row['stock_code'][2:],6,2,5)
            # if result == False:
            #     continue
            
            #均线
            df['ma_orange_10'] = df['close'].rolling(10).mean()
            df['ma_red_20'] = df['close'].rolling(20).mean()
            df['ma_gray_60'] = df['close'].rolling(60).mean()
            
            
            #计算组合图形(日线背靠背图形)
            # check_touch_type_pure(df, df.iloc[-1]['code'], '日线', gp_row)

            
    except Exception as e:
        print('get_threading_list()=>err:'+str(e))







def get_threading_list_realtime(gp_arr, gp_zt_arr, gp_zt_ph_arr, bs: baostock):
    '''
    实时数据
    获取 纯k线,不做图形计算  
    gp_zt_arr 目前专用双炮台,仙人指路
    '''
    all_signals = []  # 👈 收集本批次信号
    try:
        
        for gp_index, gp_row in gp_arr.iterrows():  
            
            
            # 获取当前日期
            start_date = datetime.now()
            now_day = (start_date).strftime("%Y-%m-%d")
            gp_id = gp_row['stock_code'][0:2]+'.'+gp_row['stock_code'][2:]
            gp_row['gp_id'] = gp_id
            
            #个股价格大于40不看
            if float(gp_row['now']) > 40:
                continue
            
            
            # # 个股行业板块排名是否在前10(板块强度)
            # result = is_top_industry(gp_row['stock_code'], (start_date).strftime("%Y%m%d"), gp_zt_arr, gp_zt_ph_arr)
            # if result == False:
            #     continue

            # # 个股行业概念排名是否在前10(板块强度)
            # result = is_hot_concept(gp_row['stock_code'], (start_date).strftime("%Y%m%d"), gp_zt_arr, gp_zt_ph_arr)
            # if result == False:
            #     continue

            
            
            #取出每只股票30天的日线数据
            prev_day = (start_date + timedelta(days=-30)).strftime("%Y-%m-%d") 
            df = get_day_list(bs, gp_id, prev_day, now_day,
                                "date,code,open,close,high,low,pctChg,volume")

            if len(df) < 15:
                continue


            
            # ================== 构造今日完整K线数据 ==========================
            open_val = float(gp_row.get('open'))
            close_val = float(gp_row.get('now'))          # 当前价作为今日 close
            high_val = float(gp_row.get('high'))
            low_val = float(gp_row.get('low'))
            volume_val = int(gp_row.get('volume'))

            # 计算 pctChg：基于昨日收盘
            pct_chg_val = 0.0
            if not df.empty:
                last_close = float(df.iloc[-1]['close'])
                if last_close > 0:
                    pct_chg_val = (close_val / last_close - 1) * 100

            # 构建今日记录（与 get_day_list 返回结构一致，含 Id）
            today_record = {
                'Id': len(df),  # 连续编号
                'date': now_day,
                'code': gp_id,
                'open': open_val,
                'close': close_val,
                'high': high_val,
                'low': low_val,
                'pctChg': pct_chg_val,
                'volume': volume_val
            }

            # 转为 DataFrame
            today_df = pd.DataFrame([today_record])
            # 拼接
            df = pd.concat([df, today_df], ignore_index=True)

                        
            # #分时2分钟涨幅大于5%同时个股涨幅大于6%(分时直线拉升)
            # result = mintun_zx_ls(gp_row, gp_row['stock_code'][2:],6,2,5)
            # if result == False:
            #     continue
            
            #均线
            df['ma_orange_10'] = df['close'].rolling(10).mean()
            df['ma_red_20'] = df['close'].rolling(20).mean()
            df['ma_gray_60'] = df['close'].rolling(60).mean()

            
            #计算组合图形(日线背靠背图形)
            check_touch_type_pure(bs, df, df.iloc[-1]['code'], '日线', gp_row)
            

            
    except Exception as e:
        print('get_threading_list()=>err:'+str(e))

    return all_signals  # 👈 返回







def check_big_main():
    '''
    监控个股大单,发现后发送邮箱
    '''
    # 假设你有一批想监控的股票
    watch_list = ['002802','605162','000592','002418']

    # 邮件配置（请替换为你的实际信息）
    EMAIL_CONFIG = {
        "to_emails": ["lcnjmq@qq.com"],  # 可多个
        "sender_email": "lcnjmq@qq.com",
        "sender_password": "crmnkqorabhecfeb",  # QQ邮箱16位授权码
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465
    }
    
    # 执行监控 + 自动发邮件
    results = check_continuous_buy_blocks_per_stock_with_email(
        watch_stocks=watch_list,
        min_consecutive=10,
        min_total_hands=30000,  #连续30000手大单
        email_config=EMAIL_CONFIG
    )