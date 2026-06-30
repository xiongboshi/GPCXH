def calculate_turnover_rate(price ,volume, shares_traded):
    """
    计算换手率
    :param volume: 成交量
    :param shares_traded: 流通股本(流通市值)
    :return: 换手率
    """
    try:
        if shares_traded == 0:
            return 0  # 避免除以零的错误
        turnover_rate = ((price * volume) / (shares_traded * 100000000)) * 100
        return turnover_rate
    
    except Exception as e:
        print(f"Error calculate_turnover_rate : {e}")