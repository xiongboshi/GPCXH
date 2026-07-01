"""
创建数据库和表结构
只需要运行一次
"""
import duckdb
import os

def create_database(db_path="market.duckdb"):
    """创建数据库和表结构"""
    
    # 如果数据库已存在，询问是否覆盖
    if os.path.exists(db_path):
        print(f"⚠️ 数据库 {db_path} 已存在")
        choice = input("是否删除并重新创建？(y/n): ").strip().lower()
        if choice != 'y':
            print("❌ 取消创建")
            return
        os.remove(db_path)
        print(f"✅ 已删除旧数据库")
    
    # 连接数据库
    db = duckdb.connect(db_path)
    
    # 创建日线表
    db.execute("""
        CREATE TABLE daily_quotes (
            thscode VARCHAR,
            trade_date DATE,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume DOUBLE,
            turnover DOUBLE,
            PRIMARY KEY (thscode, trade_date)
        )
    """)
    
    # 创建索引
    db.execute("CREATE INDEX idx_thscode ON daily_quotes(thscode)")
    db.execute("CREATE INDEX idx_trade_date ON daily_quotes(trade_date)")
    
    print("✅ 数据库和表结构创建成功！")
    print(f"📁 数据库文件: {db_path}")
    
    db.close()


if __name__ == "__main__":
    create_database()