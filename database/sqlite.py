import sqlite3
from sqlite3 import Error

import pandas as pd

class SQLiteDB:
    def __init__(self, db_file):
        """ 初始化数据库连接 """
        self.conn = None
        try:
            self.conn = sqlite3.connect(db_file)
            self.cursor = self.conn.cursor()
            # print(f"SQLite database connected: {db_file}")
        except Error as e:
            print(e)

    def create_table(self, table_name, fields):
        """ 创建表，fields 为字段和类型的字典 """
        field_strings = ', '.join([f"{field} {ftype}" for field, ftype in fields.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({field_strings});"
        self.execute_query(query)
        

    def delete_table(self, table_name):
        """ 删除表 """
        query = f"DROP TABLE IF EXISTS {table_name};"
        self.execute_query(query)

    def count_rows(self, table_name):
        """返回指定表中的行数"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def insert_row(self, table_name, data):
        """ 插入数据行, data 为字典类型 """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
        self.execute_query(query, tuple(data.values()))

    def update_row(self, table_name, row_id, updates):
        """ 更新数据行, updates 为字典类型 """
        update_string = ', '.join([f"{column} = ?" for column in updates.keys()])
        params = list(updates.values()) + [row_id]
        query = f"UPDATE {table_name} SET {update_string} WHERE id = ?;"
        self.execute_query(query, params)

    def delete_row_by_value(self, table_name, time_type_value):
        """ 删除指定表中time_type字段等于给定值的数据。  """
        sql = "DELETE FROM {} WHERE time_type = ?".format(table_name)  
        cursor = self.conn.cursor()  
        cursor.execute(sql, (time_type_value,))  
        self.conn.commit()  # 提交事务  
        
    def delete_row(self, table_name, row_id):
        """ 根据id删除行 """
        query = f"DELETE FROM {table_name} WHERE id = ?;"
        self.execute_query(query, (row_id,))
        
    def executemany(self, query, data):
        """执行批量数据库插入"""
        try:
            self.cursor.executemany(query, data)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def execute_query(self, query, params=None):  
        """ 执行SQL查询并返回成功或失败 """  
        try:  
            c = self.conn.cursor()  
            if params:  
                c.execute(query, params)  
            else:  
                c.execute(query)  
            self.conn.commit()  
            return True  
        except Error as e:  
            print(f"Error executing query: {e}")  
            return False  

    
    def executequery(self, query):  
        """ 执行SQL查询 """
        cur = self.conn.cursor()  
        cur.execute(query)  
        columns = [description[0] for description in cur.description]  
        data = cur.fetchall()  
        cur.close()  
        return columns, data  
    

    def fetch_data(self, query, params=None):
        """ 查询数据 """
        cursor = self.conn.cursor()
        result = None
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
        except Error as e:
            print(e)
        return result
    
    
    def fetchall(self, sql, params=()):  
        """ 查询数据 """
        self.cursor.execute(sql, params)  
        return self.cursor.fetchall()  
    
    def check_table_exists(self, table_name):
        '''
        查询表是否存在
        '''
        cursor = self.conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")  
        table_exists = cursor.fetchone() is not None
        return table_exists
    

    def close(self):
        """ 关闭数据库连接 """
        if self.conn:
            self.conn.close()
            # print("Database connection is closed.")
            
            
    
    def fetch_all_data(self, table_name, conditions=None):
        """ 查询所有数据，条件是可选的，返回pd类型的数据 """
        query = f"SELECT * FROM {table_name}"

        # Add conditions if provided
        if conditions:
            query += f" WHERE {conditions}"

        try:
            # Use pandas to execute the query and return the result as a DataFrame
            df = pd.read_sql_query(query, self.conn)
            return df
        except Error as e:
            print(f"Error fetching data: {e}")
            return None

# 使用示例
# db = SQLiteDB('my_database.db')
# db.create_table('users', {'id': 'INTEGER PRIMARY KEY', 'name': 'TEXT NOT NULL', 'age': 'INTEGER'})
# db.insert_row('users', {'name': 'Alice', 'age': 30})
# db.update_row('users', 1, {'name': 'Alice', 'age': 31})
# print(db.fetch_data("SELECT * FROM users"))
# db.delete_row('users', 1)
# db.delete_table('users')
# db.close()
