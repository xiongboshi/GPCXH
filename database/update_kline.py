"""
更新历史K线数据
可以独立运行，用于盘后更新
"""
from database.db_manager import DuckDBManager
from utils.getGPData import get_all_tickers
from datetime import datetime, timedelta

def init_kline():
    """
    首次初始化：批量拉取半年K线（使用已过滤的股票列表）
    """
    print("=" * 60)
    print("📊 初始化K线数据 (批量拉取半年)")
    print("=" * 60)
    
    manager = DuckDBManager("database/market.duckdb")
    
    # 获取股票列表
    tickers = manager.get_all_stock_codes()
    if not tickers:
        print("⚠️ 股票列表为空，先从API获取并过滤...")
        all_tickers = get_all_tickers()
        saved_count = manager.save_stock_list(all_tickers)
        if saved_count == 0:
            print("❌ 没有股票通过过滤条件")
            manager.close()
            return
        tickers = manager.get_all_stock_codes()
    
    print(f"✅ 共 {len(tickers)} 只股票 (已过滤)")
    
    # 批量获取K线
    start_date = (datetime.now() - timedelta(days=360)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    manager.batch_save_kline(tickers, start_date, end_date)
    
    # 显示结果
    print(f"\n📊 K线记录数: {manager.get_kline_count()}")
    print(f"📊 最新日期: {manager.get_latest_date()}")
    
    manager.close()
    print("✅ K线初始化完成！")


def daily_update_kline():
    """
    每日盘后增量更新K线（只更新已过滤的股票）
    """
    print("=" * 60)
    print("📊 每日K线增量更新")
    print("=" * 60)
    
    manager = DuckDBManager("database/market.duckdb")
    
    # 检查股票列表
    count = manager.get_stock_count()
    if count == 0:
        print("⚠️ 股票列表为空，请先运行初始化")
        manager.close()
        return
    
    # 增量更新
    manager.daily_update_kline()
    
    # 显示结果
    print(f"\n📊 当前K线记录数: {manager.get_kline_count()}")
    print(f"📊 最新日期: {manager.get_latest_date()}")
    
    manager.close()
    print("✅ K线更新完成！")


if __name__ == "__main__":
    print("请选择操作:")
    print("1. 首次初始化（批量拉取半年K线）")
    print("2. 每日增量更新（只更新最近1天）")
    
    choice = input("请输入选项 (1/2): ").strip()
    
    if choice == "1":
        init_kline()
    elif choice == "2":
        daily_update_kline()
    else:
        print("❌ 无效选项")