
import tqsdk.tafunc

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    """
    计算 MACD 指标
    白线：这条线一般表示 MACD 线，即快速线。 MACD_white
    黄线：这条线通常表示 Signal 线，即慢速线。 MACD_yellow

    :param df: 包含 'close' 列的 DataFrame
    :param short_window: 短期 EMA 的周期大小
    :param long_window: 长期 EMA 周期大小
    :param signal_window: Signal line 的周期大小
    :return: 包含 MACD 数据的 DataFrame
    """
    try:
        # 计算短期 EMA 和长期 EMA
        df['EMA_short'] = tqsdk.tafunc.ema(df["close"], short_window)
        df['EMA_long'] = tqsdk.tafunc.ema(df["close"], long_window)
        
        # 计算 MACD 线
        df['MACD_white'] = df['EMA_short'] - df['EMA_long']
        
        # 计算 Signal 线
        df['MACD_yellow'] = tqsdk.tafunc.ema(df["MACD_white"], signal_window)
        
        # 计算 MACD 柱子
        df['MACD_bar'] =  2 * (df["MACD_white"] - df["MACD_yellow"])
        
        return df
    except Exception as e:
        print(f"处理每个合约的数据出错 calculate_macd: {e}")