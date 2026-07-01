"""
更新股票列表和实时快照
可以独立运行，用于盘前/盘中更新
"""
from database.db_manager import DuckDBManager
from utils.getGPData import get_all_tickers

def update_snapshot_only():
    """
    只更新快照数据（不修改股票列表）
    """
    print("=" * 60)
    print("📸 更新实时快照数据")
    print("=" * 60)
    
    manager = DuckDBManager("database/market.duckdb")
    
    # 检查是否有股票列表
    count = manager.get_stock_count()
    if count == 0:
        print("⚠️ 股票列表为空，请先运行更新股票列表")
        manager.close()
        return
    
    # 更新快照
    manager.update_stock_list_snapshot()
    
    # 显示结果
    df = manager.get_stock_list_df()
    print(f"\n📊 当前股票快照 (前2只):")
    print(df[['thscode', 'name', 'last_price', 'price_change_ratio_pct']].head(2))
    
    manager.close()
    print("✅ 快照更新完成！")


def refresh_list_and_snapshot():
    """
    刷新股票列表 + 更新快照（带过滤）
    """
    print("=" * 60)
    print("🔄 刷新股票列表 + 快照")
    print("=" * 60)
    
    manager = DuckDBManager("database/market.duckdb")
    
    # 获取股票列表
    all_tickers = get_all_tickers()
    print(f"✅ 从API获取到 {len(all_tickers)} 只股票")
    
    # 保存列表（自动过滤）
    saved_count = manager.save_stock_list(all_tickers)
    print(f"✅ 通过过滤保存 {saved_count} 只股票")
    
    if saved_count > 0:
        # 更新快照
        filtered_tickers = manager.get_all_stock_codes()
        manager.update_stock_list_snapshot(filtered_tickers)
        
        # 显示结果
        df = manager.get_stock_list_df()
        print(f"\n📊 当前股票列表 (前10只):")
        print(df[['thscode', 'name', 'last_price', 'price_change_ratio_pct']].head(10))
    
    manager.close()
    print("✅ 股票列表刷新完成！")


if __name__ == "__main__":
    print("请选择操作:")
    print("1. 只更新快照（不修改列表）")
    print("2. 刷新股票列表 + 快照（自动过滤）")
    
    choice = input("请输入选项 (1/2): ").strip()
    
    if choice == "1":
        update_snapshot_only()
    elif choice == "2":
        refresh_list_and_snapshot()
    else:
        print("❌ 无效选项")