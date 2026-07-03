"""
策略信号存储模块
提供 tactics（策略模板）和 tactics_zhtx（组合图形）的存取
"""
import duckdb
import pandas as pd
import os


class ShapeStorage:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'database', 'market.duckdb')
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self):
        return duckdb.connect(self.db_path)

    def _init_tables(self):
        """创建表（如果不存在）"""
        conn = self._get_conn()
        try:
            # 1. tactics 表（不变）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tactics (
                    id INTEGER PRIMARY KEY,
                    date DATE,
                    tactics_name VARCHAR,
                    time_type VARCHAR,
                    symbol VARCHAR,
                    direction VARCHAR,
                    u形图形_内突_u_price DOUBLE,
                    u形图形_内突_u_now_price DOUBLE,
                    u形图形_内突_u_bot_price DOUBLE,
                    u形图形_内突_u_top_price DOUBLE,
                    u形图形_内突_u_k_num DOUBLE,
                    u形图形_内突_u_point DATE
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_tactics_unique 
                ON tactics (symbol, direction, time_type, u形图形_内突_u_price, u形图形_内突_u_bot_price, u形图形_内突_u_top_price)
            """)
            print("✅ tactics 表已就绪 (id自增 + 唯一索引)")

            # 2. tactics_zhtx 表（复合主键，无自增列）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tactics_zhtx (
                    date DATE,
                    symbol VARCHAR,
                    touch_type VARCHAR,
                    time_type VARCHAR,
                    direction VARCHAR,
                    小的_U形_datetime DATE,
                    小的_U形_point_time DATE,
                    小的_U形_u_price DOUBLE,
                    小的_U形_n_price DOUBLE,
                    小的_U形_k_num DOUBLE,
                    大的_U形_datetime DATE,
                    大的_U形_point_time DATE,
                    大的_U形_u_price DOUBLE,
                    大的_U形_n_price DOUBLE,
                    大的_U形_k_num DOUBLE,
                    tp_time DATE,
                    ht_time DATE,
                    signal_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, touch_type, time_type, direction)
                )
            """)
            print("✅ tactics_zhtx 表已就绪 (复合主键)")

        except Exception as e:
            print(f"❌ 表初始化失败: {e}")
        finally:
            conn.close()

    def drop_combined_table(self):
        """删除 tactics_zhtx 表（用于重置结构）"""
        conn = self._get_conn()
        try:
            conn.execute("DROP TABLE IF EXISTS tactics_zhtx")
            print("✅ 已删除 tactics_zhtx 表")
        except Exception as e:
            print(f"❌ 删除表失败: {e}")
        finally:
            conn.close()

    def clear_combined_table(self):
        """清空 tactics_zhtx 表数据（保留结构）"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM tactics_zhtx")
            print("✅ 已清空 tactics_zhtx 表数据")
        except Exception as e:
            print(f"❌ 清空表数据失败: {e}")
        finally:
            conn.close()

    def get_tactics_data(self, table_name='tactics', time_type='日线'):
        conn = self._get_conn()
        try:
            tables = conn.execute("SHOW TABLES").df()
            if table_name not in tables['name'].values:
                return pd.DataFrame()
            sql = f"""
                SELECT * FROM {table_name}
                WHERE time_type = ?
                ORDER BY date
            """
            df = conn.execute(sql, [time_type]).df()
            return df
        except Exception as e:
            print(f"⚠️ 读取 tactics 数据失败: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def save_shape_data(self, df, table_name='tactics_zhtx', unique_columns=None):
        if df.empty:
            return
        conn = self._get_conn()
        try:
            # 确保表存在（但不会删除重建）
            self._init_tables()
            df = df.where(pd.notnull(df), None)

            # 如果存在 'id' 列，删除它（表已无此列）
            if 'id' in df.columns:
                df = df.drop(columns=['id'])

            # 处理 unique_columns（用于去重）
            if isinstance(unique_columns, str):
                unique_columns = [col.strip() for col in unique_columns.split(',')]
            if unique_columns is None or not isinstance(unique_columns, list):
                raise ValueError("unique_columns must be provided as list or comma-separated string")

            # 根据唯一列删除旧记录
            for _, row in df.iterrows():
                where_clause = " AND ".join([f"{col} = ?" for col in unique_columns])
                params = [row[col] for col in unique_columns]
                delete_sql = f"DELETE FROM {table_name} WHERE {where_clause}"
                conn.execute(delete_sql, params)

            # 插入新数据
            columns = df.columns.tolist()
            placeholders = ", ".join(["?" for _ in columns])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            conn.executemany(insert_sql, df.values.tolist())
            print(f"✅ 保存 {len(df)} 条信号到 {table_name}")
        except Exception as e:
            print(f"❌ 保存信号失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()


_storage = None

def get_storage():
    global _storage
    if _storage is None:
        _storage = ShapeStorage()
    return _storage

def get_tactics_data(table_name='tactics', time_type='日线'):
    return get_storage().get_tactics_data(table_name, time_type)

def save_shape_data(df, table_name='tactics_zhtx', unique_columns=None):
    get_storage().save_shape_data(df, table_name, unique_columns)

def drop_combined_table():
    """删除组合图形表（重置结构）"""
    get_storage().drop_combined_table()

def clear_combined_table():
    """清空组合图形表数据"""
    get_storage().clear_combined_table()