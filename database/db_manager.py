"""
数据操作层
提供增删改查功能
"""
import os
import time
import duckdb as duckdb_lib  # 使用别名避免冲突
import pandas as pd
import requests
from datetime import datetime, timedelta
from utils.getGPData import get_all_tickers, get_historical_kline

# ============ API配置 ============
API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"  # 从 https://fuyao.aicubes.cn/admin/ 获取
BASE_URL = "https://fuyao.aicubes.cn"
HEADERS = {"X-api-key": API_KEY}


class DuckDBManager:
    """DuckDB 数据管理类"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # 默认使用项目根目录/database/market.duckdb
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'database', 'market.duckdb')
        self.db_path = db_path
        self.db = duckdb_lib.connect(db_path)

        # ============ 过滤配置 ============
        self.filter_config = {
            'exclude_st': True,        # 排除ST股票
            'exclude_kcb': True,       # 排除科创板(688)
            'exclude_cyb': True,       # 排除创业板(300,301)
            'exclude_bj': True,        # 排除北交所(8开头)
            'max_price': 50,           # 最大股价
        }
        
        self._init_tables()
        print(f"✅ 连接数据库: {db_path}")
    
    def _init_tables(self):
        """初始化表结构"""
        # 日线数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS daily_quotes (
                thscode VARCHAR,
                trade_date DATE,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                close_price DOUBLE,
                volume DOUBLE,
                turnover DOUBLE,
                pct_chg DOUBLE,
                PRIMARY KEY (thscode, trade_date)
            )
        """)
        
        # 股票列表表 - 实时快照
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS stock_list (
                thscode VARCHAR PRIMARY KEY,
                ticker VARCHAR,
                name VARCHAR,
                market VARCHAR,
                last_price DOUBLE,
                price_change DOUBLE,
                price_change_ratio_pct DOUBLE,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                prev_price DOUBLE,
                volume DOUBLE,
                turnover DOUBLE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_thscode ON daily_quotes(thscode)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_trade_date ON daily_quotes(trade_date)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_stock_thscode ON stock_list(thscode)")
    
    def close(self):
        self.db.close()
        print("✅ 数据库连接已关闭")
    
    # ============ 过滤函数 ============
    def should_exclude_stock(self, thscode):
        """
        判断是否应该排除某只股票
        返回: True表示排除，False表示保留
        """
        ticker = thscode.split('.')[0] if '.' in thscode else thscode
        
        # 1. 排除北交所 (8开头)
        if self.filter_config.get('exclude_bj', True) and ticker.startswith('8'):
            return True
        
        # 2. 排除创业板 (300, 301开头)
        if self.filter_config.get('exclude_cyb', True) and ticker.startswith(('300', '301')):
            return True
        
        # 3. 排除科创板 (688开头)
        if self.filter_config.get('exclude_kcb', True) and ticker.startswith('688'):
            return True
        
        return False
    
    def should_exclude_by_price(self, price):
        """根据价格判断是否排除"""
        if price is None:
            return False
        return price > self.filter_config.get('max_price', 50)
    
    def should_exclude_st(self, name):
        """判断是否为ST股票"""
        if not name:
            return False
        return self.filter_config.get('exclude_st', True) and ('ST' in name.upper() or '*ST' in name.upper())
    
    # ============ 股票列表管理 ============
    def save_stock_list(self, tickers, names=None):
        """
        保存股票列表到数据库（带过滤）
        tickers: 股票代码列表，如 ['600519.SH', '000001.SZ']
        names: 股票名称列表（可选）
        """
        if not tickers:
            print("⚠️ 股票列表为空")
            return 0
        
        # ============ 过滤股票 ============
        filtered_data = []
        skipped_count = 0
        skip_reasons = {
            'code': 0,
            'st': 0
        }
        
        for i, thscode in enumerate(tickers):
            name = names[i] if names and i < len(names) else ''
            
            # 1. 检查代码是否被排除（科创板、创业板、北交所）
            if self.should_exclude_stock(thscode):
                skipped_count += 1
                skip_reasons['code'] += 1
                continue
            
            # 2. 检查是否为ST股票
            if self.should_exclude_st(name):
                skipped_count += 1
                skip_reasons['st'] += 1
                continue
            
            # 通过过滤，保留该股票
            ticker = thscode.split('.')[0] if '.' in thscode else thscode
            market = thscode.split('.')[1] if '.' in thscode else ''
            
            filtered_data.append({
                'thscode': thscode,
                'ticker': ticker,
                'name': name,
                'market': market,
                'updated_at': datetime.now()
            })
        
        if not filtered_data:
            print(f"⚠️ 所有股票都被过滤掉了")
            print(f"   - 代码过滤 (科创板/创业板/北交所): {skip_reasons['code']}")
            print(f"   - ST过滤: {skip_reasons['st']}")
            return 0
        
        # 清空并插入
        self.db.execute("DELETE FROM stock_list")
        
        params = [[d['thscode'], d['ticker'], d['name'], d['market'], 
                   None, None, None, None, None, None, None, None, None, d['updated_at']] for d in filtered_data]
        self.db.executemany("""
            INSERT INTO stock_list (thscode, ticker, name, market, 
                last_price, price_change, price_change_ratio_pct, 
                open_price, high_price, low_price, prev_price, volume, turnover, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
        
        print(f"✅ 已保存 {len(filtered_data)} 只股票到 stock_list")
        print(f"   - 跳过 {skipped_count} 只 (代码过滤: {skip_reasons['code']}, ST过滤: {skip_reasons['st']})")
        return len(filtered_data)
    

    # =========== 行情快照管理 ============
    def get_snapshot(self, thscodes=None, limit=100, offset=0):
        """获取行情快照"""
        url = f"{BASE_URL}/api/a-share/prices/snapshot"
        params = {}
        
        if thscodes:
            params["thscodes"] = thscodes
        else:
            params["limit"] = limit
            params["offset"] = offset
        
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            data = resp.json()
            
            if data.get("code") != 0:
                print(f"❌ 获取快照失败: {data.get('message')}")
                return []
            
            return data.get("data", {}).get("item", [])
        except Exception as e:
            print(f"❌ 快照请求异常: {e}")
            return []
    

    # =========== 股票列表快照更新 ============
    def update_stock_list_snapshot(self, tickers=None):
        """
        更新股票列表的实时快照数据（只更新快照，不修改列表）
        """
        if tickers is None:
            tickers = self.get_all_stock_codes()
        
        if not tickers:
            print("⚠️ 股票列表为空")
            return 0
        
        batch_size = 100
        updated_count = 0
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            thscodes_str = ",".join(batch)
            
            try:
                items = self.get_snapshot(thscodes_str)
                
                if not items:
                    continue
                
                for item in items:
                    self.db.execute("""
                        UPDATE stock_list SET
                            last_price = ?,
                            price_change = ?,
                            price_change_ratio_pct = ?,
                            open_price = ?,
                            high_price = ?,
                            low_price = ?,
                            prev_price = ?,
                            volume = ?,
                            turnover = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE thscode = ?
                    """, [
                        item.get('last_price'),
                        item.get('price_change'),
                        item.get('price_change_ratio_pct'),
                        item.get('open_price'),
                        item.get('high_price'),
                        item.get('low_price'),
                        item.get('prev_price'),
                        item.get('volume'),
                        item.get('turnover'),
                        item.get('thscode')
                    ])
                    updated_count += 1
                
                # print(f"✅ 已更新 {len(items)} 只股票快照")
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ 批量快照更新失败: {e}")
        
        print(f"✅ 快照更新完成！共更新 {updated_count} 只股票")
        return updated_count
    
    def refresh_stock_list(self):
        """
        从API刷新股票列表（带过滤）
        只保存满足过滤条件的股票
        """
        print("🔄 从API获取最新股票列表...")
        tickers = get_all_tickers()
        if not tickers:
            print("❌ 获取股票列表失败")
            return 0
        
        # save_stock_list 内部已经包含过滤逻辑
        return self.save_stock_list(tickers)
    

    # =========== 股票列表 + 快照刷新 ============
    def refresh_stock_list_with_snapshot(self):
        """
        刷新股票列表并获取快照数据（带过滤）
        """
        print("🔄 从API获取最新股票列表...")
        tickers = get_all_tickers()
        if not tickers:
            print("❌ 获取股票列表失败")
            return 0
        
        # save_stock_list 内部已经包含过滤逻辑
        saved_count = self.save_stock_list(tickers)
        if saved_count == 0:
            print("⚠️ 没有股票通过过滤条件")
            return 0
        
        # 只更新通过过滤的股票快照
        filtered_tickers = self.get_all_stock_codes()
        return self.update_stock_list_snapshot(filtered_tickers)
    
    def get_all_stock_codes(self):
        """获取所有股票代码"""
        result = self.db.execute("SELECT thscode FROM stock_list ORDER BY thscode").fetchall()
        return [row[0] for row in result]
    
    def get_all_stocks_df(self):
        """获取所有股票信息"""
        return self.db.execute("SELECT * FROM stock_list ORDER BY thscode").df()
    
    def get_stock_count(self):
        """获取股票数量"""
        return self.db.execute("SELECT COUNT(*) FROM stock_list").fetchone()[0]
    
    def search_stock(self, keyword):
        """搜索股票（按代码或名称）"""
        return self.db.execute("""
            SELECT * FROM stock_list 
            WHERE thscode LIKE ? OR name LIKE ?
            ORDER BY thscode
        """, [f'%{keyword}%', f'%{keyword}%']).df()
    
    def get_filtered_stock_codes(self, include_price_check=True):
        """
        获取通过过滤条件的股票代码列表
        include_price_check: 是否包含股价检查（从K线数据中获取最新价）
        """
        if include_price_check:
            # 从K线数据中获取最新价进行过滤
            df = self.db.execute("""
                WITH latest_price AS (
                    SELECT thscode, close_price,
                           ROW_NUMBER() OVER (PARTITION BY thscode ORDER BY trade_date DESC) as rn
                    FROM daily_quotes
                )
                SELECT DISTINCT sl.thscode
                FROM stock_list sl
                WHERE sl.thscode NOT LIKE '688.%'
                  AND sl.thscode NOT LIKE '300.%'
                  AND sl.thscode NOT LIKE '301.%'
                  AND sl.thscode NOT LIKE '8%'
                  AND sl.name NOT LIKE '%ST%'
                  AND sl.name NOT LIKE '%*ST%'
                  AND (SELECT close_price FROM latest_price lp 
                       WHERE lp.thscode = sl.thscode AND lp.rn = 1) <= ?
            """, [self.filter_config.get('max_price', 50)]).df()
        else:
            # 只做代码和ST过滤
            df = self.db.execute("""
                SELECT thscode
                FROM stock_list
                WHERE thscode NOT LIKE '688.%'
                  AND thscode NOT LIKE '300.%'
                  AND thscode NOT LIKE '301.%'
                  AND thscode NOT LIKE '8%'
                  AND name NOT LIKE '%ST%'
                  AND name NOT LIKE '%*ST%'
            """).df()
        
        return df['thscode'].tolist() if not df.empty else []
    
    # ============ K线数据管理 ============
    def insert_kline_data(self, df, thscode, name=""):
        """
        插入K线数据（带过滤 + 涨跌幅计算）
        涨跌幅：第N天显示第N天相对第N-1天的涨跌幅
        """
        if df.empty:
            return 0
        
        try:
            # 过滤检查
            if self.should_exclude_stock(thscode):
                return 0
            if self.should_exclude_st(name):
                return 0
            
            df = df.copy()
            
            # 按日期升序排序（从旧到新）
            df = df.sort_values('date_ms', ascending=True).reset_index(drop=True)
            
            # ✅ 关键修改：移除 shift(1)，直接使用原始涨跌幅
            df['pct_chg'] = df['close_price'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].round(2).fillna(0)
            # 不再使用 shift(1)
            
            # 股价过滤（使用最新收盘价）
            latest_price = df.iloc[-1]['close_price'] if not df.empty else 0
            if self.should_exclude_by_price(latest_price):
                return 0
            
            # 生成日期列（强制使用北京时间）
            df["thscode"] = thscode
            df["trade_date"] = pd.to_datetime(df["date_ms"], unit="ms", utc=True).dt.tz_convert('Asia/Shanghai').dt.date
            
            columns = ["thscode", "trade_date", "open_price", "high_price", 
                    "low_price", "close_price", "volume", "turnover", "pct_chg"]
            
            for col in ['open_price', 'high_price', 'low_price', 'close_price', 'volume', 'turnover']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 删除旧数据，重新插入
            self.db.execute("DELETE FROM daily_quotes WHERE thscode = ?", [thscode])
            
            self.db.executemany("""
                INSERT OR REPLACE INTO daily_quotes 
                (thscode, trade_date, open_price, high_price, low_price, close_price, volume, turnover, pct_chg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, df[columns].values.tolist())
            
            return len(df)
            
        except Exception as e:
            print(f"❌ {thscode} 插入失败: {e}")
            import traceback
            traceback.print_exc()
            return 0



    def batch_save_kline(self, tickers, start_date, end_date):
        """
        批量获取并保存K线数据
        注意：tickers 应该已经是过滤后的列表（从 stock_list 获取）
        """
        total = len(tickers)
        success_count = 0
        fail_count = 0
        skipped_count = 0
        total_rows = 0
        
        print(f"🚀 开始批量获取K线数据，共 {total} 只股票")
        print(f"📅 时间范围: {start_date} 至 {end_date}")
        print(f"🔧 最大股价限制: {self.filter_config.get('max_price', 50)}")
        
        for i, thscode in enumerate(tickers):
            # 代码过滤（双重保险）
            if self.should_exclude_stock(thscode):
                skipped_count += 1
                continue
            
            if (i + 1) % 100 == 0:
                print(f"进度: {i+1}/{total} - {thscode}")
            else:
                print(f"进度: {i+1}/{total} - {thscode}")
            
            try:
                bars = get_historical_kline(thscode, start_date, end_date)
                
                if not bars:
                    fail_count += 1
                    continue
                
                df = pd.DataFrame(bars)
                
                # 检查股价过滤
                latest_price = df.iloc[-1]['close_price'] if not df.empty else 0
                if self.should_exclude_by_price(latest_price):
                    print(f"⏭️ 跳过 {thscode} (股价 {latest_price:.2f} > {self.filter_config.get('max_price', 50)})")
                    skipped_count += 1
                    continue
                
                rows = self.insert_kline_data(df, thscode)
                if rows > 0:
                    success_count += 1
                    total_rows += rows
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"❌ {thscode} 处理失败: {e}")
                fail_count += 1
            
            if (i + 1) % 10 == 0:
                print(f"💾 已处理 {i+1} 只，成功 {success_count}，失败 {fail_count}，跳过 {skipped_count}，共 {total_rows} 条记录")
            
            time.sleep(0.3)
        
        print(f"\n✅ 批量保存完成！成功 {success_count} 只，失败 {fail_count} 只，跳过 {skipped_count} 只")
        print(f"📊 数据库中共有 {self.get_kline_count()} 条记录")
        return success_count, fail_count, skipped_count
    
    def daily_update_kline(self):
        """每日收盘后增量更新K线数据（优化版）"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"🔄 开始每日K线更新: {today}")
        
        tickers = self.get_all_stock_codes()
        if not tickers:
            print("⚠️ 股票列表为空")
            return 0
        
        total = len(tickers)
        success_count = 0
        skipped_count = 0
        price_skipped = 0
        
        print(f"📊 共 {total} 只股票需要更新")
        
        for i, thscode in enumerate(tickers):
            if self.should_exclude_stock(thscode):
                skipped_count += 1
                continue
            
            try:
                bars = get_historical_kline(thscode, yesterday, today)
                
                if bars:
                    df = pd.DataFrame(bars)
                    latest_price = df.iloc[-1]['close_price'] if not df.empty else 0
                    if self.should_exclude_by_price(latest_price):
                        price_skipped += 1
                        continue
                    self.insert_kline_data(df, thscode)
                    success_count += 1
                
                # 优化：每100只打印一次进度（而不是每50只）
                if (i + 1) % 100 == 0:
                    print(f"💾 已更新 {i+1}/{total} 只，成功 {success_count}")
                
                # 优化：减少sleep，从0.3改为0.15
                time.sleep(0.15)
                
            except Exception as e:
                print(f"❌ {thscode} 更新失败: {e}")
        
        print(f"✅ {today} K线更新完成！成功更新 {success_count} 只股票")
        print(f"   - 代码跳过: {skipped_count}，股价跳过: {price_skipped}")
        return success_count





    # ============ 查询数据 ============
    def query_data(self, thscode=None, start_date=None, end_date=None, limit=10):
        """查询日线数据（含涨跌幅）"""
        sql = "SELECT * FROM daily_quotes WHERE 1=1"
        params = []
        
        if thscode:
            sql += " AND thscode = ?"
            params.append(thscode)
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        
        sql += f" ORDER BY trade_date DESC LIMIT {limit}"
        return self.db.execute(sql, params).df()
    
    def query_sql(self, sql):
        """执行自定义SQL查询"""
        return self.db.execute(sql).df()
    
    # ============ 统计信息 ============
    def get_latest_date(self):
        """获取数据库中最新数据日期"""
        result = self.db.execute("SELECT MAX(trade_date) FROM daily_quotes").fetchone()[0]
        return result if result else None
    
    def get_kline_count(self):
        """获取日线总记录数"""
        return self.db.execute("SELECT COUNT(*) FROM daily_quotes").fetchone()[0]
    
    def get_row_count(self):
        """获取总记录数（别名）"""
        return self.get_kline_count()
    
    def get_stock_list_df(self):
        """获取股票列表DataFrame"""
        return self.db.execute("SELECT * FROM stock_list ORDER BY thscode").df()
    
    def get_stock_list(self):
        """获取所有股票代码列表（别名）"""
        return self.get_all_stock_codes()
    
    def get_filter_stats(self):
        """获取过滤统计信息"""
        result = self.db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN thscode LIKE '688.%' THEN 1 ELSE 0 END) as kcb_count,
                SUM(CASE WHEN thscode LIKE '300.%' OR thscode LIKE '301.%' THEN 1 ELSE 0 END) as cyb_count,
                SUM(CASE WHEN thscode LIKE '8%' THEN 1 ELSE 0 END) as bj_count,
                SUM(CASE WHEN name LIKE '%ST%' OR name LIKE '%*ST%' THEN 1 ELSE 0 END) as st_count
            FROM stock_list
        """).fetchone()
        
        return {
            'total': result[0],
            'kcb': result[1],
            'cyb': result[2],
            'bj': result[3],
            'st': result[4]
        }
    
    def print_filter_stats(self):
        """打印过滤统计"""
        stats = self.get_filter_stats()
        effective = stats['total'] - stats['kcb'] - stats['cyb'] - stats['bj'] - stats['st']
        print(f"📊 过滤统计:")
        print(f"   - 总股票数: {stats['total']}")
        print(f"   - 科创板: {stats['kcb']}")
        print(f"   - 创业板: {stats['cyb']}")
        print(f"   - 北交所: {stats['bj']}")
        print(f"   - ST股票: {stats['st']}")
        print(f"   - ✅ 有效股票: {effective}")
    
    # ============ 删除数据 ============
    def delete_stock_data(self, thscode):
        """删除某只股票的所有日线数据"""
        self.db.execute("DELETE FROM daily_quotes WHERE thscode = ?", [thscode])
        print(f"✅ 已删除 {thscode} 的日线数据")
    
    def delete_stock_from_list(self, thscode):
        """从股票列表中删除某只股票"""
        self.db.execute("DELETE FROM stock_list WHERE thscode = ?", [thscode])
        print(f"✅ 已从股票列表中删除 {thscode}")
    
    def clear_all_data(self):
        """清空所有数据（谨慎使用）"""
        confirm = input("⚠️ 确认要清空所有数据？(yes/no): ")
        if confirm.lower() == 'yes':
            self.db.execute("DELETE FROM daily_quotes")
            self.db.execute("DELETE FROM stock_list")
            print("✅ 已清空所有数据")
        else:
            print("❌ 已取消")


if __name__ == "__main__":
    manager = DuckDBManager("database/market.duckdb")
    print(f"📊 股票数量: {manager.get_stock_count()}")
    print(f"📊 K线记录数: {manager.get_kline_count()}")
    print(f"📊 最新日期: {manager.get_latest_date()}")
    manager.print_filter_stats()
    manager.close()