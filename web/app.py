import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import pandas as pd
import amount
import pickle

from flask import Flask, render_template, jsonify, request
import duckdb
import pandas as pd
import subprocess
from datetime import datetime, timedelta

from utils.连扳天梯 import get_limit_up_ladder
from utils.概率和行业 import enrich_ladder_data_from_db, build_full_market_mapping,CACHE_DIR, SECTOR_CACHE_PATH
from database.db_manager import DuckDBManager

from database.shape_storage import drop_combined_table,drop_enter_table
from database.shape_storage import get_storage  # 或直接 ShapeStorage



app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'market.duckdb')

def get_db():
    return duckdb.connect(DB_PATH)

# @app.route('/')
# def index():
#     return render_template('index.html')


@app.route('/')
def index():
    return render_template('base.html')  # 或重定向到某个默认功能

@app.route('/limit_up')
def limit_up():
    return render_template('limit_up.html')

@app.route('/tactics')
def tactics():
    return render_template('tactics.html')

@app.route('/combined')
def combined():
    return render_template('combined.html')

@app.route('/entry')
def entry():
    return render_template('entry.html')

@app.route('/ladder')
def ladder():
    return render_template('ladder.html')

@app.route('/update_data')
def update_data():
    return render_template('update_data.html')

@app.route('/limit_up_pool')
def limit_up_pool():
    return render_template('limit_up_pool.html')





@app.route('/api/search_stocks')
def search_stocks():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    df = db.execute("""
        SELECT thscode, name 
        FROM stock_list 
        WHERE thscode LIKE ? OR name LIKE ?
        ORDER BY thscode
        LIMIT 50
    """, [f'%{q}%', f'%{q}%']).df()
    db.close()
    return jsonify(df.to_dict(orient='records'))



#========================================
#数据更新
#=======================================
@app.route('/api/update_sector_cache', methods=['POST'])
def update_sector_cache():
    """
    强制更新板块映射缓存（从同花顺API重新拉取）
    """
    try:
        API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"  # 建议从环境变量读取
        mapping = build_full_market_mapping(
            API_KEY,
            include_concept=True,
            include_industry=True,
            force_refresh=True
        )
        if mapping:
            return jsonify({
                'success': True,
                'message': f'板块映射更新成功，共 {len(mapping)} 只股票',
                'count': len(mapping)
            })
        else:
            return jsonify({'success': False, 'message': '更新失败，返回空映射'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/apply_sector_to_db', methods=['POST'])
def apply_sector_to_db():
    try:
        # 检查缓存文件是否存在
        if not os.path.exists(SECTOR_CACHE_PATH):
            return jsonify({'success': False, 'error': '缓存文件不存在，请先生成映射'}), 400

        # 加载缓存
        with open(SECTOR_CACHE_PATH, 'rb') as f:
            mapping = pickle.load(f)

        # 转换为 (concept, industry) 格式
        update_data = {}
        for thscode, info in mapping.items():
            update_data[thscode] = (info.get('concept', ''), info.get('industry', ''))

        # 更新数据库（stock_list）
        manager = DuckDBManager("database/market.duckdb")
        updated_stocks = manager.update_stock_concept_industry(update_data)

        # 重新计算行业K线（基于最新 industry 字段）
        industry_count = manager.update_industry_daily()  # 使用默认日期范围（最近200天）

        manager.close()

        return jsonify({
            'success': True,
            'updated_stocks': updated_stocks,
            'updated_industry': industry_count,
            'message': f'成功更新 {updated_stocks} 只股票的板块信息，并重新计算 {industry_count} 条行业K线'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
#================================
#涨停池 API 路由
#================================
@app.route('/api/limit_up_pool')
def get_limit_up_pool():
    try:
        days = request.args.get('days', 10, type=int)
        date_filter = request.args.get('date')  # 可选，格式 YYYY-MM-DD
        
        API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"
        
        pool_data = get_recent_limit_up_pool(API_KEY, days=days)
        if not pool_data:
            return jsonify({'success': True, 'data': [], 'count': 0})
        
        # 获取股票列表信息
        manager = DuckDBManager("database/market.duckdb")
        df_stocks = manager.get_all_stocks_df()
        manager.close()
        
        stock_info_map = {}
        for _, row in df_stocks.iterrows():
            stock_info_map[row['thscode']] = {
                'concept': row.get('concept', ''),
                'industry': row.get('industry', '')
            }
        
        # 处理每个条目
        for item in pool_data:
            thscode = item.get('thscode')
            info = stock_info_map.get(thscode, {})
            item['concept'] = info.get('concept', '')
            item['industry'] = info.get('industry', '')
            
            # ★ 强制日期格式为 YYYY-MM-DD
            if 'trade_date' in item:
                if isinstance(item['trade_date'], (pd.Timestamp, datetime)):
                    item['trade_date'] = item['trade_date'].strftime('%Y-%m-%d')
                elif isinstance(item['trade_date'], str):
                    # 如果已经字符串，但可能包含时间，截取前10位
                    item['trade_date'] = item['trade_date'][:10]
        
        # 按日期排序（最新在前）
        pool_data.sort(key=lambda x: x.get('trade_date', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'data': pool_data,
            'count': len(pool_data)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    




#====================================
#板块排行统计 API
#====================================
@app.route('/api/limit_up_pool_stats')
def get_limit_up_pool_stats():
    """
    获取涨停池的板块排行统计
    """
    try:
        days = request.args.get('days', 10, type=int)
        
        # 先获取涨停池数据
        API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"
        pool_data = get_recent_limit_up_pool(API_KEY, days=days)
        
        if not pool_data:
            return jsonify({'success': True, 'stats': []})
        
        # 统计各行业的涨停次数和涉及的股票
        industry_stats = {}
        for item in pool_data:
            industry = item.get('industry', '未分类')
            if not industry:
                industry = '未分类'
            # 取第一个行业（如果多个）
            main_industry = industry.split(',')[0].strip()
            
            if main_industry not in industry_stats:
                industry_stats[main_industry] = {
                    'count': 0,
                    'stocks': set(),
                    'total_board': 0
                }
            industry_stats[main_industry]['count'] += 1
            industry_stats[main_industry]['stocks'].add(item.get('thscode'))
            industry_stats[main_industry]['total_board'] += item.get('continue_day_cnt', 0)
        
        # 转换为列表并排序
        result = []
        for industry, stats in industry_stats.items():
            result.append({
                'industry': industry,
                'count': stats['count'],
                'stock_count': len(stats['stocks']),
                'total_board': stats['total_board'],
                'avg_board': round(stats['total_board'] / stats['count'], 2) if stats['count'] > 0 else 0
            })
        
        result.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            'success': True,
            'stats': result[:20]  # 返回前20
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



#===================================
#返回K线数据
#===================================
@app.route('/api/kline')
def get_kline():
    code = request.args.get('code')
    limit = request.args.get('limit', 500, type=int)
    if not code:
        return jsonify({'error': '缺少code参数'}), 400
    db = get_db()
    sql = """
        SELECT trade_date, open_price, high_price, low_price, close_price, volume, pct_chg
        FROM daily_quotes
        WHERE thscode = ?
        ORDER BY trade_date ASC
        LIMIT ?
    """
    df = db.execute(sql, [code, limit]).df()
    db.close()
    if df.empty:
        return jsonify({'error': '无数据'}), 404

    # 计算均线
    df = calc_moving_averages(df)

    records = df.to_dict(orient='records')
    for r in records:
        r['trade_date'] = str(r['trade_date'])
        # 均线值保留两位小数
        for key in ['ma5', 'ma10', 'ma20', 'ma60']:
            if key in r and pd.notna(r[key]):
                r[key] = round(r[key], 2)
            else:
                r[key] = None
    return jsonify(records)



@app.route('/api/limit_up_stocks')
def get_limit_up_stocks():
    db = get_db()
    date_sql = """
        SELECT DISTINCT trade_date 
        FROM daily_quotes 
        ORDER BY trade_date DESC 
        LIMIT 12
    """
    dates_df = db.execute(date_sql).df()
    if dates_df.empty:
        db.close()
        return jsonify({'stocks': [], 'dates': []})
    date_list = dates_df['trade_date'].tolist()
    date_str = "', '".join([str(d) for d in date_list])
    sql = f"""
        WITH limit_up AS (
            SELECT 
                thscode,
                trade_date,
                close_price,
                pct_chg,
                ROW_NUMBER() OVER (PARTITION BY thscode ORDER BY trade_date DESC) as rn
            FROM daily_quotes
            WHERE trade_date IN ('{date_str}')
              AND pct_chg >= 9.8
              AND trade_date != CURRENT_DATE
        )
        SELECT 
            lu.thscode,
            sl.name,
            lu.trade_date,
            lu.close_price,
            lu.pct_chg,
            sl.concept,
            sl.industry
        FROM limit_up lu
        LEFT JOIN stock_list sl ON lu.thscode = sl.thscode
        WHERE lu.rn = 1
        ORDER BY lu.trade_date DESC, lu.thscode
    """
    df = db.execute(sql).df()
    db.close()
    if df.empty:
        return jsonify({'stocks': [], 'dates': date_list})
    records = df.to_dict(orient='records')
    for r in records:
        r['trade_date'] = str(r['trade_date'])
    return jsonify({'stocks': records, 'dates': [str(d) for d in date_list]})



@app.route('/api/kline_with_marker')
def get_kline_with_marker():
    code = request.args.get('code')
    limit = request.args.get('limit', 500, type=int)
    if not code:
        return jsonify({'error': '缺少code参数'}), 400
    db = get_db()
    sql = """
        SELECT trade_date, open_price, high_price, low_price, close_price, volume, pct_chg
        FROM daily_quotes
        WHERE thscode = ?
        ORDER BY trade_date ASC
        LIMIT ?
    """
    df = db.execute(sql, [code, limit]).df()
    if df.empty:
        db.close()
        return jsonify({'error': '无数据'}), 404

    # 计算均线
    df = calc_moving_averages(df)

    # 获取涨停标记
    marker_sql = """
        SELECT trade_date, close_price, pct_chg
        FROM daily_quotes
        WHERE thscode = ?
          AND pct_chg >= 9.8
          AND trade_date >= (SELECT MAX(trade_date) - INTERVAL 12 DAY FROM daily_quotes)
          AND trade_date != CURRENT_DATE
        ORDER BY trade_date
    """
    markers_df = db.execute(marker_sql, [code]).df()
    db.close()

    records = df.to_dict(orient='records')
    for r in records:
        r['trade_date'] = str(r['trade_date'])
        for key in ['ma5', 'ma10', 'ma20', 'ma60']:
            if key in r and pd.notna(r[key]):
                r[key] = round(r[key], 2)
            else:
                r[key] = None

    markers = []
    if not markers_df.empty:
        for _, row in markers_df.iterrows():
            markers.append({
                'trade_date': str(row['trade_date']),
                'price': float(row['close_price']),
                'pct_chg': float(row['pct_chg'])
            })
    return jsonify({'data': records, 'markers': markers})





@app.route('/api/run_strategy', methods=['POST'])
def run_strategy():
    try:
        data = request.get_json()
        strategy_type = data.get('strategy_type', 'full')
        stock_list = data.get('stock_list', None)

        if not stock_list:
            db = get_db()
            date_sql = """
                SELECT DISTINCT trade_date 
                FROM daily_quotes 
                ORDER BY trade_date DESC 
                LIMIT 12
            """
            dates_df = db.execute(date_sql).df()
            if dates_df.empty:
                db.close()
                return jsonify({'success': False, 'message': '没有交易日数据'}), 400
            date_list = dates_df['trade_date'].tolist()
            date_str = "', '".join([str(d) for d in date_list])
            sql = f"""
                WITH limit_up AS (
                    SELECT 
                        thscode,
                        ROW_NUMBER() OVER (PARTITION BY thscode ORDER BY trade_date DESC) as rn
                    FROM daily_quotes
                    WHERE trade_date IN ('{date_str}')
                      AND pct_chg >= 9.8
                      AND trade_date != CURRENT_DATE
                )
                SELECT thscode
                FROM limit_up
                WHERE rn = 1
            """
            df = db.execute(sql).df()
            db.close()
            stock_list = df['thscode'].tolist() if not df.empty else []

        if not stock_list:
            return jsonify({'success': False, 'message': '没有可检测的股票'}), 400

        result_df = amount.run_strategy_on_stock_list(stock_list, lookback_days=250, strategy_type=strategy_type)

        if result_df.empty:
            return jsonify({'success': True, 'signals': [], 'count': 0, 'message': '未检测到信号'})
        else:
            signals = result_df.to_dict(orient='records')
            for s in signals:
                for k, v in s.items():
                    if isinstance(v, pd.Timestamp):
                        s[k] = v.strftime('%Y-%m-%d')
            return jsonify({'success': True, 'signals': signals, 'count': len(signals)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'策略执行异常: {str(e)}'}), 500

@app.route('/api/tactics')
def get_tactics():
    db = get_db()
    try:
        tables = db.execute("SHOW TABLES").df()
        if 'tactics' not in tables['name'].values:
            db.close()
            return jsonify([])
        df = db.execute("""
            SELECT t.symbol, t.date, t.direction, t.u形图形_内突_u_point, t.u形图形_内突_u_price, 
                   t.u形图形_内突_u_k_num, t.u形图形_内突_u_bot_price, t.u形图形_内突_u_top_price, t.time_type,
                   sl.concept, sl.industry
            FROM tactics t
            LEFT JOIN stock_list sl ON t.symbol = sl.thscode
            ORDER BY t.date DESC
        """).df()
        db.close()
        if df.empty:
            return jsonify([])
        records = df.to_dict(orient='records')
        for r in records:
            for col in ['date', 'u形图形_内突_u_point']:
                if r.get(col) is not None:
                    r[col] = str(r[col])
        return jsonify(records)
    except Exception as e:
        print(f"❌ /api/tactics 异常: {e}")
        db.close()
        return jsonify([])




@app.route('/api/kline_with_tactics')
def get_kline_with_tactics():
    code = request.args.get('code')
    limit = request.args.get('limit', 500, type=int)
    date_point = request.args.get('date_point')
    u_point = request.args.get('u_point')
    if not code:
        return jsonify({'error': '缺少code参数'}), 400

    db = get_db()
    try:
        sql = """
            SELECT trade_date, open_price, high_price, low_price, close_price, volume, pct_chg
            FROM daily_quotes
            WHERE thscode = ?
            ORDER BY trade_date ASC
            LIMIT ?
        """
        df = db.execute(sql, [code, limit]).df()
        if df.empty:
            db.close()
            return jsonify({'error': '无数据'}), 404

        # 计算均线
        df = calc_moving_averages(df)

        markers = []
        if date_point:
            date_df = db.execute("""
                SELECT close_price FROM daily_quotes
                WHERE thscode = ? AND trade_date = ?
            """, [code, date_point]).df()
            if not date_df.empty:
                markers.append({
                    'trade_date': date_point,
                    'price': float(date_df.iloc[0]['close_price']),
                    'type': 'date',
                    'label': '策略日'
                })
        if u_point:
            u_df = db.execute("""
                SELECT close_price FROM daily_quotes
                WHERE thscode = ? AND trade_date = ?
            """, [code, u_point]).df()
            if not u_df.empty:
                markers.append({
                    'trade_date': u_point,
                    'price': float(u_df.iloc[0]['close_price']),
                    'type': 'u_point',
                    'label': 'U形点'
                })

        db.close()
        records = df.to_dict(orient='records')
        for r in records:
            r['trade_date'] = str(r['trade_date'])
            for key in ['ma5', 'ma10', 'ma20', 'ma60']:
                if key in r and pd.notna(r[key]):
                    r[key] = round(r[key], 2)
                else:
                    r[key] = None

        return jsonify({'data': records, 'markers': markers})
    except Exception as e:
        db.close()
        return jsonify({'error': str(e)}), 500
    


# ===================================
#涨停池数据获取
#====================================
def fetch_limit_up_pool_with_retry(api_key, date_ms, page=1, size=200, max_retries=3):
    """
    带重试机制的涨停池获取函数
    """
    url = "https://fuyao.aicubes.cn/api/a-share/special-data/limit-up-pool"
    params = {
        'page': page,
        'size': size,
        'sort_field': 'limit_up_time',
        'sort_dir': 'desc'
    }
    if date_ms:
        params['date_ms'] = date_ms
    
    headers = {"X-api-key": api_key}
    
    # 使用带重试的 Session
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=1,  # 重试间隔 1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get('code') != 0:
                print(f"⚠️ API 错误: {data.get('message')}")
                return None
            return data.get('data', {})
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionResetError) as e:
            if attempt < max_retries:
                wait = (attempt + 1) * 2  # 2s, 4s, 6s
                print(f"⏳ 请求失败 ({e})，{wait}s 后重试 (尝试 {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            else:
                print(f"❌ 获取涨停池失败，已重试 {max_retries} 次: {e}")
                return None
        except Exception as e:
            print(f"❌ 获取涨停池异常: {e}")
            return None
    return None


def get_recent_limit_up_pool(api_key, days=10):
    """
    获取最近 N 天的涨停股票池数据（包含今天，带重试和错误处理）
    """
    all_items = []
    
    # 获取最近 days 天的交易日（从 daily_quotes 获取）
    db = get_db()
    dates_df = db.execute("""
        SELECT DISTINCT trade_date 
        FROM daily_quotes 
        ORDER BY trade_date DESC 
        LIMIT ?
    """, [days]).df()
    db.close()
    
    date_set = set()
    if not dates_df.empty:
        # 确保转换为字符串 YYYY-MM-DD
        for d in dates_df['trade_date']:
            if isinstance(d, (pd.Timestamp, datetime)):
                date_set.add(d.strftime('%Y-%m-%d'))
            else:
                date_set.add(str(d))
    
    # 强制添加今天（字符串格式）
    today_str = datetime.now().date().strftime('%Y-%m-%d')
    date_set.add(today_str)
    print(f"ℹ️ 添加今天 {today_str} 到查询列表（日线数据可能未更新）")
    
    # 按日期降序排序（所有元素都是字符串，可以安全排序）
    date_list = sorted(date_set, reverse=True)[:days]
    
    for date_str in date_list:
        # 转换为毫秒时间戳
        dt = pd.to_datetime(date_str)
        date_ms = int(dt.timestamp() * 1000)
        
        page = 1
        while True:
            result = fetch_limit_up_pool_with_retry(api_key, date_ms=date_ms, page=page, size=200)
            if not result:
                break
            items = result.get('item', [])
            if not items:
                break
            for item in items:
                item['trade_date'] = date_str  # 直接使用字符串
            all_items.extend(items)
            
            pagination = result.get('pagination', {})
            if page >= pagination.get('pages', 1):
                break
            page += 1
        
        time.sleep(1.0)  # 避免请求过快
    
    return all_items






#===================================
#连扳天梯
#===================================
@app.route('/api/ladder')
def get_ladder():
    try:
        days = request.args.get('days', 30, type=int)
        target_date = request.args.get('date')  # 可选，格式 YYYY-MM-DD
        API_KEY = "sk-fuyao-sNNYGRAebGYCgzOovqNydUfa4Zajhslk"
        df_ladder = get_limit_up_ladder(API_KEY, as_dataframe=True)
        # 从数据库填充板块
        manager = DuckDBManager("database/market.duckdb")
        df_enriched = enrich_ladder_data_from_db(df_ladder, manager)
        manager.close()
        
        # 如果指定了日期，过滤
        if target_date:
            # 将日期转为统一格式匹配
            df_enriched['date_str'] = df_enriched['date'].dt.strftime('%Y-%m-%d')
            df_enriched = df_enriched[df_enriched['date_str'] == target_date]
            df_enriched = df_enriched.drop(columns=['date_str'])
        
        records = df_enriched.to_dict(orient='records')
        for r in records:
            if 'date' in r and hasattr(r['date'], 'strftime'):
                r['date'] = r['date'].strftime('%Y-%m-%d')
        return jsonify({'success': True, 'data': records, 'count': len(records)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    

#=====================================
#更新行业历史k线
#=====================================
@app.route('/api/update_industry_kline', methods=['POST'])
def update_industry_kline():
    """手动更新行业K线"""
    try:
        manager = DuckDBManager("database/market.duckdb")
        count = manager.update_industry_daily()
        manager.close()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


#==================================
#查询行业历史K线数据进行图表展示
#==================================
@app.route('/api/industry_kline')
def get_industry_kline():
    industry = request.args.get('industry')
    limit = request.args.get('limit', 500, type=int)
    if not industry:
        return jsonify({'error': '缺少industry参数'}), 400
    manager = DuckDBManager("database/market.duckdb")
    df = manager.get_industry_kline(industry, limit=limit)
    manager.close()
    if df.empty:
        return jsonify({'error': '无行业数据'}), 404

    # 计算均线
    df = calc_moving_averages(df, periods=[5, 10, 20, 60])

    records = df.to_dict(orient='records')
    for r in records:
        r['trade_date'] = str(r['trade_date'])
        for key in ['ma5', 'ma10', 'ma20', 'ma60']:
            if key in r and pd.notna(r[key]):
                r[key] = round(r[key], 2)
            else:
                r[key] = None
    return jsonify(records)



#=================================
#清空 组合策略 表
#=================================
@app.route('/api/clear_tactics', methods=['POST'])
def clear_tactics():
    """清空 tactics 表"""
    db = get_db()
    try:
        # 确保 tactics 表存在（如果数据库被删除，先创建表）
        storage = get_storage()
        storage._init_tables()  # 这会执行 CREATE TABLE IF NOT EXISTS
        
        db.execute("DELETE FROM tactics")
        db.close()
        return jsonify({'success': True, 'message': 'tactics 表已清空'})
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500
    


#==================================
#添加均线计算函数
#==================================
def calc_moving_averages(df, periods=[5, 10, 20, 60]):
    """
    计算指定周期的移动平均线
    df: 包含 'close_price' 和 'trade_date' 的 DataFrame，且已按日期升序排列
    periods: 均线周期列表
    返回: 添加了 ma{period} 列的 DataFrame
    """
    df = df.copy()
    for p in periods:
        df[f'ma{p}'] = df['close_price'].rolling(window=p).mean()
    return df


    



@app.route('/api/run_strategy_parallel', methods=['POST'])
def run_strategy_parallel():
    """
    多线程并行执行策略检测
    """
    try:
        data = request.get_json()
        strategy_type = data.get('strategy_type', 'full')
        stock_list = data.get('stock_list', None)
        num_workers = data.get('num_workers', 8)   # 可从前端传入

        if not stock_list:
            # 获取涨停股票列表（同原逻辑）
            db = get_db()
            date_sql = """
                SELECT DISTINCT trade_date 
                FROM daily_quotes 
                ORDER BY trade_date DESC 
                LIMIT 12
            """
            dates_df = db.execute(date_sql).df()
            if dates_df.empty:
                db.close()
                return jsonify({'success': False, 'message': '没有交易日数据'}), 400
            date_list = dates_df['trade_date'].tolist()
            date_str = "', '".join([str(d) for d in date_list])
            sql = f"""
                WITH limit_up AS (
                    SELECT 
                        thscode,
                        ROW_NUMBER() OVER (PARTITION BY thscode ORDER BY trade_date DESC) as rn
                    FROM daily_quotes
                    WHERE trade_date IN ('{date_str}')
                      AND pct_chg >= 9.8
                      AND trade_date != CURRENT_DATE
                )
                SELECT thscode
                FROM limit_up
                WHERE rn = 1
            """
            df = db.execute(sql).df()
            db.close()
            stock_list = df['thscode'].tolist() if not df.empty else []

        if not stock_list:
            return jsonify({'success': False, 'message': '没有可检测的股票'}), 400

        # 执行并行策略
        result_df = amount.run_strategy_on_stock_list_parallel(
            stock_list,
            lookback_days=250,
            strategy_type=strategy_type,
            num_workers=num_workers
        )

        if result_df.empty:
            return jsonify({'success': True, 'signals': [], 'count': 0, 'message': '未检测到信号'})
        else:
            signals = result_df.to_dict(orient='records')
            for s in signals:
                for k, v in s.items():
                    if isinstance(v, pd.Timestamp):
                        s[k] = v.strftime('%Y-%m-%d')
            return jsonify({'success': True, 'signals': signals, 'count': len(signals)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'策略执行异常: {str(e)}'}), 500
    


from database.shape_storage import clear_combined_table

@app.route('/api/clear_combined', methods=['POST'])
def clear_combined():
    try:
        clear_combined_table()  # 调用我们修改过的函数，它会自动处理表不存在的情况
        return jsonify({'success': True, 'message': '组合图形表已清空'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/api/run_combined', methods=['POST'])
def run_combined():
    try:
        # 删除旧表，重建新结构
        drop_combined_table()

        data = request.get_json()
        strategy_type = data.get('strategy_type', 'full')
        stock_list = data.get('stock_list', None)

        if not stock_list:
            db = get_db()
            df = db.execute("SELECT DISTINCT symbol FROM tactics").df()
            db.close()
            stock_list = df['symbol'].tolist() if not df.empty else []

        if not stock_list:
            return jsonify({'success': False, 'message': '没有股票可检测，请先生成基础U形'}), 400

        result_df = amount.run_combined_strategy_on_stock_list_parallel(stock_list, strategy_type=strategy_type)

        if result_df.empty:
            return jsonify({'success': True, 'signals': [], 'count': 0})
        else:
            signals = result_df.to_dict(orient='records')
            for s in signals:
                for k, v in s.items():
                    if isinstance(v, pd.Timestamp):
                        s[k] = v.strftime('%Y-%m-%d')
            return jsonify({'success': True, 'signals': signals, 'count': len(signals)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'组合图形执行异常: {str(e)}'}), 500
    


@app.route('/api/combined')
def get_combined():
    db = get_db()
    try:
        tables = db.execute("SHOW TABLES").df()
        if 'tactics_zhtx' not in tables['name'].values:
            db.close()
            return jsonify([])
        df = db.execute("""
            SELECT c.symbol, c.touch_type, c.direction, c.tp_time, c.ht_time, 
                   c.小的_U形_u_price, c.大的_U形_datetime,
                   c.大的_U形_u_price, c.大的_U形_point_time, c.小的_U形_point_time,
                   sl.concept, sl.industry
            FROM tactics_zhtx c
            LEFT JOIN stock_list sl ON c.symbol = sl.thscode
            ORDER BY c.symbol, c.direction
        """).df()
        db.close()
        if df.empty:
            return jsonify([])
        records = df.to_dict(orient='records')
        for r in records:
            for col in ['tp_time', 'ht_time', '大的_U形_datetime', '大的_U形_point_time', '小的_U形_point_time']:
                if r.get(col) is not None:
                    r[col] = str(r[col])
        return jsonify(records)
    except Exception as e:
        print(f"❌ /api/combined 异常: {e}")
        db.close()
        return jsonify([])




@app.route('/api/run_combined_parallel', methods=['POST'])
def run_combined_parallel():
    """
    多线程并行执行组合图形策略
    """
    try:
        # 先清空组合图形表（确保数据干净）
        drop_combined_table()
        
        data = request.get_json()
        strategy_type = data.get('strategy_type', 'full')
        num_workers = data.get('num_workers', 8)   # 默认8线程

        # 获取所有有基础图形的股票（从 tactics 表）
        db = get_db()
        df = db.execute("SELECT DISTINCT symbol FROM tactics").df()
        db.close()
        stock_list = df['symbol'].tolist() if not df.empty else []

        if not stock_list:
            return jsonify({'success': False, 'message': '没有股票可检测，请先生成基础U形'}), 400

        # 执行并行组合图形策略
        result_df = amount.run_combined_strategy_on_stock_list_parallel(
            stock_list, 
            strategy_type=strategy_type,
            num_workers=num_workers
        )

        if result_df.empty:
            return jsonify({'success': True, 'signals': [], 'count': 0})
        else:
            signals = result_df.to_dict(orient='records')
            for s in signals:
                for k, v in s.items():
                    if isinstance(v, pd.Timestamp):
                        s[k] = v.strftime('%Y-%m-%d')
            return jsonify({'success': True, 'signals': signals, 'count': len(signals)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'组合图形并行执行异常: {str(e)}'}), 500
    



# 导入入场判断函数
from amount import run_entry_check_parallel

@app.route('/api/check_entry', methods=['POST'])
def check_entry():
    try:
        # 先清空入场信号表（确保数据干净）
        drop_enter_table()
        print("🗑️ 已删除旧入场信号表")

        data = request.get_json(silent=True) or {}
        days = data.get('days', 12)
        results = run_entry_check_parallel(days_after=days)
        return jsonify({'success': True, 'data': results, 'count': len(results)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ========== 后台维护接口 ==========
def run_script(script_path, input_text, timeout=300):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_script = os.path.join(base_dir, script_path)
    if not os.path.exists(full_script):
        return {'success': False, 'error': f'脚本不存在: {full_script}'}
    env = os.environ.copy()
    env['PYTHONPATH'] = base_dir
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        result = subprocess.run(
            ['python', full_script],
            input=input_text,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=base_dir,
            env=env,
            timeout=timeout
        )
        return {'success': True, 'output': result.stdout, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': f'执行超时（超过{timeout}秒）'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/api/update_kline', methods=['POST'])
def update_kline():
    result = run_script('database/update_kline.py', '2\n')
    return jsonify(result)

@app.route('/api/update_snapshot', methods=['POST'])
def update_snapshot():
    result = run_script('database/update_snapshot.py', '1\n')
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)