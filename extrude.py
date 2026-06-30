import utils
import time


class ExtrudeMode:
    '''平台二次突破'''
    def remove_down(code, gp_detail, up_arr, add_price, recur, trdLock):
        '''
        移出中线大于2的行情 0.6
        '''
        try:
            if len(gp_detail) < 26:
                return
            # 中线大于2
            high_price = float(gp_detail[0]['high']) + add_price  # 最后一根最高价
            detail = utils.list_split(gp_detail, 26)[0]

            num = 0
            for j in range(len(detail)):
                # print('价格：'+str(detail[j]['high']))
                if float(detail[j]['high']) > high_price:
                    num += 1
                if num > 3:
                    print('不满足' + str(j))
                    return
                if j >= len(detail)-1 & num <= 2:
                    # up_arr.append(detail[0])
                    if recur != True:
                        for idx in range(6):
                            # print('递归 add_price:'+str(idx))
                            ExtrudeMode.remove_down(
                                code, gp_detail, up_arr, round(0.1*(idx+1), 1), True, trdLock)
                    else:
                        # trdLock.acquire()
                        ExtrudeMode.check_interval(
                            code, gp_detail, up_arr, add_price, trdLock)
                        # 释放锁，开启下一个线程
                        # trdLock.release()
                    return

        except Exception as e:
            print('remove_down()=>err:'+str(e))

    def check_interval(code, gp_detail, up_arr, add_price, trdLock):
        '''
        检查区间0.1-0.6是否满足中线小于2
        '''
        try:
            # print('检查区间0.1-0.6是否满足中线小于2 add_price:'+str(add_price))
            last_k_id = int(gp_detail[0]['Id'])
            for idx in range(11):
                diff_price = round(float(add_price-idx*0.01), 2) #距离顶部的差值
                # print(diff_price)
                high_price = round(
                    float(gp_detail[0]['high']) + diff_price, 2)  # 最后一根最高价
                # print('检查区间0.1-0.6是否满足中线小于2 high_price:'+str(high_price))

                # 定位相同价位K
                equal_k_arr = [instance
                               for instance in gp_detail if round(float(instance['high']), 2) == high_price and last_k_id-int(instance['Id']) >= 26 and last_k_id-int(instance['Id']) <= 120]  # 取相同价位所有K
                if len(equal_k_arr) <= 0:
                    continue
                if idx == 0:
                    del(equal_k_arr[0])
                # print('检查区间0.1-0.6是否满足中线小于2 取相同价位所有K:')
                # print(equal_k_arr)

                for item in equal_k_arr:
                    now_k_id = int(item['Id'])
                    mid_k_num = last_k_id-now_k_id+1  # 中间相差K数
                    # print('中间相差K数:'+str(mid_k_num))
                    mid_k_arr = utils.list_split(gp_detail, mid_k_num)[
                        0]  # 中间相差K数据


                    # 区间中线小于3
                    mid_big_arr = [e for e in mid_k_arr if round(float(e['high']), 2) > high_price]
                    if len(mid_big_arr) <= 0:
                        # print('区间中线<= 0:'+str(len(mid_big_arr)))
                        continue
                    if len(mid_big_arr) > 3:
                        # print('区间中线> 3:'+str(len(mid_big_arr)))
                        return
                    # 距离最后一根线的区间数大于3
                    mid_k_id = int(mid_big_arr[len(mid_big_arr)-1]['Id'])
                    if last_k_id - mid_k_id <= 3:
                        print('距离最后一根线的区间数不大于3:'+str(gp_detail[0]['code']))
                        return


                    # u形低价
                    u_min_price = round(min([float(e['low']) for e in mid_k_arr]), 2)
                    # print(
                    #     '号码：'+str(gp_detail[0]['code'])+'   u形低价:'+str(u_min_price))

                    # top不超过20%
                    diff_percent = diff_price/(high_price-u_min_price)
                    if diff_percent > 0.2 or diff_percent < 0.02:
                        break

                    # 支撑
                    gp_detail.reverse()
                    # zc_k_arr = utils.list_split(gp_detail, (180-mid_k_num+1))[0]  # 支撑相差K数据
                    zc_k_arr = utils.list_split(gp_detail, (len(gp_detail)-mid_k_num+1))[0]  # 支撑相差K数据
                    zc_k_arr.reverse()
                    print('长度：'+str(len(gp_detail)))

                    num = 0
                    for im in zc_k_arr:
                        num += 1
                        now_high_price = round(float(im['high']), 2)
                        # 不能大于最高价格
                        if now_high_price > high_price:
                            print('最高价：',high_price)
                            print('当前价：',now_high_price)
                            print(str(gp_detail[0]['code'])+':true')
                            break


                        # 定位支撑点
                        now_low_price = round(float(im['low']), 2)
                        if now_low_price < u_min_price:
                            item_rc = {
                                'code': gp_detail[0]['code'],
                                'high_price': high_price,
                                'low_price': u_min_price,
                                'top_k_time':item['date'],
                                'big_top_num':len(mid_big_arr),
                                'poor_price':diff_price,
                                'diff_percent':str(int(round(diff_percent*100,2)))+'%',
                            }
                            up_arr.append(item_rc)
                            print(up_arr)
                            utils.sendEmail('17508266621@163.com','QNIWTRJINSUGLLPL','626473648@qq.com',gp_detail[0]['code']+'市场即时消息',str(item_rc))
                            break
        except Exception as e:
            print('check_interval()=>err:'+str(e))
