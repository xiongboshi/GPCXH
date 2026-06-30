import os
import time
import datetime
import amount as am
import smtplib
import threading as trd
from email.mime.text import MIMEText
from email.header import Header

def list_split(items, n):
    '''
    数组拆分 将数组每 n 个切分一次
    '''
    return [items[i:i+n] for i in range(0, len(items), n)]


def sendEmail(send_user,send_pwd,accept_user,send_title,send_msg):
    '''
    发送邮箱
    @param send_user:发送人账户
    @param send_pwd:授权密匙
    @param accept_user:接收人账户
    @param send_title:发送标题
    @param send_msg:发送内容
    '''
    try:
        msg = MIMEText(send_msg, 'plain', 'utf-8')
        msg['From'] = send_user
        msg['To'] = accept_user 
        msg['Subject'] = Header(send_title,'utf-8') 

        server = smtplib.SMTP()  
        server.connect("smtp.163.com", 25)
        server.login(send_user, send_pwd)  
        server.sendmail(send_user, [accept_user], msg.as_string())  
        server.quit()  # 关闭连接
    except Exception as e:
        print("sendEmail()=>err:",str(e))
        pass


def countGains(yes_day_close_price,now_price):
    '''
    计算涨幅
    @param yes_day_close_price:昨日收盘价
    @param now_price:当前实时价
    '''
    try:
        gains = (now_price-yes_day_close_price)/yes_day_close_price*100
        return gains
    except Exception as e:
        print('countGains()=>err:',e)
    

def fileWrite(all_gp):
    '''
    前一交易日价格文件写入
    @param all_gp:当天所以股票代码
    '''
    try:
        now_day = time.strftime('%Y-%m-%d',time.localtime(time.time())) #当天日期
        gp_id = all_gp[0][0:2]+'.'+all_gp[0][2:]
        list = am.get_day_list(trd.Lock(), gp_id, now_day, now_day,
                                "date,code,close,isST")
        if len(list) > 0:
            file = os.getcwd()+'/data/yes_day_gp.txt'
            res = os.path.exists(file) # 文件是否存在
            if res == True:
                os.remove(file)
            f = open(file,"w",encoding="UTF-8") #新创建
            for i in range(len(all_gp)):
                gp_pid = all_gp[i][0:2]+'.'+all_gp[i][2:]
                arr = am.get_day_list(trd.Lock(), gp_pid, now_day, now_day,
                            "date,code,close,isST")
                if len(arr) > 0:
                    f.write(arr[0]['date']+','+str(gp_pid)+','+arr[0]['close']+','+arr[0]['isST']+'\n')   #写入
                    f.flush()

    except Exception as e:
        print('fileWrite()=>err:',str(e))


def fileRead():
    '''
    文件读取
    '''
    try:
        yes_day_gp = []
        file = os.getcwd()+'/data/yes_day_gp.txt'
        res = os.path.exists(file)
        if res == True:
            with open(file,'r',encoding='UTF-8') as f:
                arr = f.readlines()
                for item in arr:
                    yes_day_gp.append(item.replace('\n','').split(','))
                return yes_day_gp
    except Exception as e:
        print('fileRead()=>err:',str(e))


yes_day_gp_arr = fileRead()
# print(yes_day_gp_arr)


def timeRange(gp_arr):
    '''
    下午5.30后-晚上09.00段内获取当日k数据
    @parma gp_arr:所有股票
    @return bool:完成行情写入
    '''
    try:
        res = False
        # 范围时间
        d_time = datetime.datetime.strptime(str(datetime.datetime.now().date())+'17:30', '%Y-%m-%d%H:%M')
        d_time1 =  datetime.datetime.strptime(str(datetime.datetime.now().date())+'23:00', '%Y-%m-%d%H:%M')
        
        # 当前时间
        n_time = datetime.datetime.now()
        
        # 判断当前时间是否在范围时间内
        # if n_time > d_time and n_time < d_time1:
        print('时间范围内')
        fileWrite(gp_arr) # 写入昨日行情,完成后关闭主程序
        res =True
        return res
    except Exception as e:
        print('timeRange()=>err:',str(e))
        pass

def isTradingTime():
    '''
    交易时间段确认
    '''
    try:
        res = False
        # 范围时间
        d_time = datetime.datetime.strptime(str(datetime.datetime.now().date())+'09:14', '%Y-%m-%d%H:%M')
        d_time1 =  datetime.datetime.strptime(str(datetime.datetime.now().date())+'11:32', '%Y-%m-%d%H:%M')
        d_time2 = datetime.datetime.strptime(str(datetime.datetime.now().date())+'12:59', '%Y-%m-%d%H:%M')
        d_time3 =  datetime.datetime.strptime(str(datetime.datetime.now().date())+'15:02', '%Y-%m-%d%H:%M')

        # 当前时间
        n_time = datetime.datetime.now()
                # 判断当前时间是否在范围时间内
        res = n_time > d_time and n_time < d_time1
        if res:
            print('交易时间内')
            return res
        res = n_time > d_time2 and n_time < d_time3
        if res:
            print('交易时间内')
            return res
        return res
    except Exception as e:
        print('isTradingTime()=>err:',str(e))
    

        
        
def filter_stock_ids(stock_ids):
    '''
    用于剔除不需要的股票ID（'ST'、'300'、'688'、'100'开头的）
    '''
    valid_stock_ids = []
    for stock_id in stock_ids:
        # # # 排除 'ST' 开头的股票
        # if stock_id.startswith('ST'):
        #     continue
        # 排除创业板 '300' 开头的股票
        if stock_id.startswith('sz300'):
            continue
        # 排除科创板 '688' 开头的股票
        if stock_id.startswith('sz688'):
            continue
        # 排除创业板 '300' 开头的股票
        if stock_id.startswith('sh300'):
            continue
        # 排除科创板 '688' 开头的股票
        if stock_id.startswith('sz688'):
            continue
        # 排除北交所 'bj' 开头的股票
        if stock_id.startswith('bj'):
            continue
        # 如果不满足上述条件，保留股票ID
        valid_stock_ids.append(stock_id)
    return valid_stock_ids