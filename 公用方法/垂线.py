
def hammer_line(prices_df, direction = '买'):
    '''
    锤子线
    '''
    try:
    
        
        if direction == '买':
            
            
            open_price_low = prices_df['open'].iloc[-1]
            close_price_low = prices_df['close'].iloc[-1]
            high_price_low = prices_df['high'].iloc[-1]
            low_price_low = prices_df['low'].iloc[-1]
            
            ################锤线################
            if open_price_low > close_price_low: #反方向线
                #垂体部分小于引线
                if abs(open_price_low - close_price_low) < abs(close_price_low - low_price_low):
                        
                    #上边引线小于下边引线  至少两倍
                    if abs(high_price_low - open_price_low) < abs(close_price_low - low_price_low) and \
                        abs(high_price_low - open_price_low) / abs(close_price_low - low_price_low) <= 0.67:
                        # print('反方向线 --- 锤线')
                        
                        return True
                    
                    
            elif open_price_low < close_price_low: #同方向线
                #垂体部分小于引线
                is_yx_bc = False
                if abs(open_price_low - close_price_low) < abs(open_price_low - low_price_low):
                    is_yx_bc = True
                        
                if is_yx_bc == True:
                    
                    #上边引线小于下边引线
                    if abs(high_price_low - close_price_low) < abs(open_price_low - low_price_low) and \
                        abs(high_price_low - close_price_low) / abs(open_price_low - low_price_low) <= 0.67:
                        # print('同方向线 --- 锤线')
                        return True
                
            
            elif open_price_low == close_price_low: #十字线
                #垂体部分小于引线
                if abs(open_price_low - close_price_low) < abs(close_price_low - low_price_low):
                    #上边引线小于下边引线
                    if abs(high_price_low - open_price_low) < abs(close_price_low - low_price_low) and \
                        abs(high_price_low - open_price_low) / abs(close_price_low - low_price_low) <= 0.55:
                        # print('十字线 --- 锤线')
                        return True
                    
                    
                    
        if direction == '卖':
                     
            open_price_high = prices_df['open'].iloc[-1]
            close_price_high = prices_df['close'].iloc[-1]
            high_price_high = prices_df['high'].iloc[-1]
            low_price_high = prices_df['low'].iloc[-1]
            
            #太小的线不看  根据价格判断什么k线不用看
            if close_price_high <= 14:
                if high_price_high - low_price_high < 0.4:
                    return False
            elif close_price_high > 14:
                if high_price_high - low_price_high < 0.8:
                    return False
                
            
            
            ################锤线################
            if open_price_high < close_price_high: #反方向线
                
                #垂体部分小于引线
                if abs(open_price_high - close_price_high) * 1 < abs(high_price_high - close_price_high):
                    
                    #下边引线小于上边引线
                    if abs(open_price_high - low_price_high) < abs(high_price_high - close_price_high) and \
                        abs(open_price_high - low_price_high) / abs(high_price_high - close_price_high) <= 0.67:
                        # print('反方向线 --- 锤线')
                        
                        return True
                    
                    
            elif open_price_high > close_price_high: #同方向线
                #垂体部分小于引线
                is_yx_bc = False
                if abs(open_price_high - close_price_high) * 1 < abs(high_price_high - open_price_high):
                    is_yx_bc = True
                        
                if is_yx_bc == True:
                
                    #下边引线小于上边引线
                    if abs(close_price_high - low_price_high) < abs(high_price_high - open_price_high) and \
                        abs(close_price_high - low_price_high) / abs(high_price_high - open_price_high) <= 0.67:
                        # print('同方向线 --- 锤线')
                        
                        return True
                    
            
            elif open_price_high == close_price_high: #十字线
                #垂体部分小于引线
                if abs(open_price_high - close_price_high) * 1 < abs(high_price_high - open_price_high):
                    #下边引线小于上边引线
                    if abs(open_price_high - low_price_high) < abs(high_price_high - open_price_high) and \
                        abs(open_price_high - low_price_high) / abs(high_price_high - open_price_high) <= 0.55:
                        # print('十字线 --- 锤线')
                        return True
        
                        
        #卖最高线为4倍垂线
        if direction == '3倍':
                     
            open_price_high = prices_df['open'].iloc[-1]
            close_price_high = prices_df['close'].iloc[-1]
            high_price_high = prices_df['high'].iloc[-1]
            low_price_high = prices_df['low'].iloc[-1]
            
                
            
            
            ################锤线################
            if open_price_high < close_price_high: #反方向线
                
                #垂体部分小于引线
                if abs(open_price_high - close_price_high) * 3 < abs(high_price_high - close_price_high):
                    
                    #下边引线小于上边引线
                    if abs(open_price_high - low_price_high) < abs(high_price_high - close_price_high) and \
                        abs(open_price_high - low_price_high) / abs(high_price_high - close_price_high) <= 0.67:
                        # print('反方向线 --- 锤线')
                        
                        return True
                    
                    
            elif open_price_high > close_price_high: #同方向线
                #垂体部分小于引线
                is_yx_bc = False
                if abs(open_price_high - close_price_high) * 3 < abs(high_price_high - open_price_high):
                    is_yx_bc = True
                        
                if is_yx_bc == True:
                
                    #下边引线小于上边引线
                    if abs(close_price_high - low_price_high) < abs(high_price_high - open_price_high) and \
                        abs(close_price_high - low_price_high) / abs(high_price_high - open_price_high) <= 0.67:
                        # print('同方向线 --- 锤线')
                        
                        return True
                    
            
            elif open_price_high == close_price_high: #十字线
                #垂体部分小于引线
                if abs(open_price_high - close_price_high) * 3 < abs(high_price_high - open_price_high):
                    #下边引线小于上边引线
                    if abs(open_price_high - low_price_high) < abs(high_price_high - open_price_high) and \
                        abs(open_price_high - low_price_high) / abs(high_price_high - open_price_high) <= 0.55:
                        # print('十字线 --- 锤线')
                        return True
                    
                    
        #卖最高线为4倍垂线
        if direction == '2倍':
                     
            open_price_high = prices_df['open'].iloc[-1]
            close_price_high = prices_df['close'].iloc[-1]
            high_price_high = prices_df['high'].iloc[-1]
            low_price_high = prices_df['low'].iloc[-1]
            
                
            
            
            ################锤线################
            if open_price_high < close_price_high: #反方向线
                
                #垂体部分小于引线
                if abs(open_price_high - close_price_high) * 2 < abs(high_price_high - close_price_high):
                    
                    #下边引线小于上边引线
                    if abs(open_price_high - low_price_high) < abs(high_price_high - close_price_high) and \
                        abs(open_price_high - low_price_high) / abs(high_price_high - close_price_high) <= 0.67:
                        # print('反方向线 --- 锤线')
                        
                        return True
                    
                    
            elif open_price_high > close_price_high: #同方向线
                #垂体部分小于引线
                is_yx_bc = False
                if abs(open_price_high - close_price_high) * 2 < abs(high_price_high - open_price_high):
                    is_yx_bc = True
                        
                if is_yx_bc == True:
                
                    #下边引线小于上边引线
                    if abs(close_price_high - low_price_high) < abs(high_price_high - open_price_high) and \
                        abs(close_price_high - low_price_high) / abs(high_price_high - open_price_high) <= 0.67:
                        # print('同方向线 --- 锤线')
                        
                        return True
                    
            
            elif open_price_high == close_price_high: #十字线
                #垂体部分小于引线
                if abs(open_price_high - close_price_high) * 2 < abs(high_price_high - open_price_high):
                    #下边引线小于上边引线
                    if abs(open_price_high - low_price_high) < abs(high_price_high - open_price_high) and \
                        abs(open_price_high - low_price_high) / abs(high_price_high - open_price_high) <= 0.55:
                        # print('十字线 --- 锤线')
                        return True
                    
        return False

    except Exception as e:
        print(f"计算策略函数（hammer_line）出错: {e}")