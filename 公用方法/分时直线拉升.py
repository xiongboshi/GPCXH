import akshare as ak
import pandas as pd
from datetime import timedelta


def mintun_zx_ls(gp_row , stock_code,zzf = 6, time_kd = 1, time_zf = 4):
    '''
    分时2分钟涨幅大于4%同时个股涨幅大于7%
    
    zzf 总涨幅
    
    time_kd 查看时间
    
    time_zf 查看时间内的涨幅
    '''
    try:
        fs_pd = ak.stock_intraday_em(stock_code)
        #昨日收盘价
        zr_close = gp_row['close']
        #今日当前涨幅
        jr_zf = gp_row['涨跌百分比']
        if jr_zf > zzf:
            #计算2分钟涨幅是否大于等于4%
            
            # 将时间列转换为 datetime 对象
            fs_pd['时间'] = pd.to_datetime(fs_pd['时间'], format='%H:%M:%S')

            # 遍历 DataFrame
            for i in range(len(fs_pd)):
                current_time = fs_pd['时间'].iloc[i]

                # 找到2分钟前和2分钟后的时间
                time_two_minutes_ago = current_time - timedelta(minutes=time_kd)
                time_two_minutes_later = current_time + timedelta(minutes=time_kd)

                # 查找2分钟前的成交价
                price_two_minutes_ago = fs_pd.loc[fs_pd['时间'] == time_two_minutes_ago, '成交价']
                # 查找2分钟后的成交价
                price_two_minutes_later = fs_pd.loc[fs_pd['时间'] == time_two_minutes_later, '成交价']

                if not price_two_minutes_ago.empty and not price_two_minutes_later.empty:
                    price_before = price_two_minutes_ago.values[0]
                    price_after = price_two_minutes_later.values[0]
                    
                    # 计算涨幅
                    price_change = ((price_after - price_before) / price_before) * 100
                    
                    if current_time < current_time.replace(hour=9, minute=30):  # 当前时间小于 9:30
                        if price_change > 9:
                            print(f"{stock_code}时间: {current_time.strftime('%H:%M:%S')} | 前涨幅: {price_before:.2f}, 后涨幅: {price_after:.2f} | 涨幅: {price_change:.2f}%")
                            return True
                    else:
                        if price_change > time_zf: # 其他时间段
                            print(f"{stock_code}时间: {current_time.strftime('%H:%M:%S')} | 前涨幅: {price_before:.2f}, 后涨幅: {price_after:.2f} | 涨幅: {price_change:.2f}%")
                            return True

    
        return False
    
    except Exception as e:
        print('mintun_zx_ls()=>err:'+str(e))