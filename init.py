"""
首次初始化：同时初始化股票列表、快照、K线
"""
from database.db_manager import DuckDBManager
from utils.getGPData import get_all_tickers
from datetime import datetime, timedelta

print("=" * 60)
print("🚀 首次初始化全市场数据")
print("=" * 60)

# 1. 连接数据库
manager = DuckDBManager("database/market.duckdb")

# 2. 获取所有股票列表（原始数据）
all_tickers = get_all_tickers()
print(f"✅ 从API获取到 {len(all_tickers)} 只")

# 3. 保存股票列表（内部会自动过滤）
print("\n📸 保存股票列表（自动过滤）...")
saved_count = manager.save_stock_list(all_tickers)
print(f"✅ 通过过滤保存 {saved_count} 只股票")

if saved_count == 0:
    print("❌ 没有股票通过过滤条件，退出")
    manager.close()
    exit()

# 4. 更新实时快照数据
filtered_tickers = manager.get_all_stock_codes()
# print("\n📸 更新实时快照...")
# manager.update_stock_list_snapshot(filtered_tickers)

# 5. 批量获取K线
print("\n📊 开始获取K线数据...")
start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")
print(f"📅 时间范围: {start_date} 至 {end_date}")

manager.batch_save_kline(filtered_tickers, start_date, end_date)

# 6. 打印统计
print("\n" + "=" * 60)
print("📊 初始化完成统计:")
print("=" * 60)
manager.print_filter_stats()
print(f"📊 K线记录数: {manager.get_kline_count()}")
print(f"📊 最新日期: {manager.get_latest_date()}")

# 7. 关闭连接
manager.close()

print("\n✅ 初始化完成！")
print("\n💡 后续维护:")
print("   - 盘后更新K线: python database/update_kline.py")
print("   - 盘中更新快照: python database/update_snapshot.py")




