from flask import Flask, render_template, jsonify, request
import duckdb
import pandas as pd
import subprocess
import os
from datetime import datetime, timedelta

app = Flask(__name__)
DB_PATH = "../database/market.duckdb"

def get_db():
    return duckdb.connect(DB_PATH)

@app.route('/')
def index():
    return render_template('index.html')

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
    records = df.to_dict(orient='records')
    for r in records:
        r['trade_date'] = str(r['trade_date'])
    return jsonify(records)

# ===== 新增：涨停股票识别 =====
@app.route('/api/limit_up_stocks')
def get_limit_up_stocks():
    """获取最近12个交易日内有涨停的股票列表"""
    db = get_db()
    
    # 1. 获取最近12个交易日的日期
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
    
    # 2. 查询这些日期中涨跌幅 >= 9.8 的股票（涨停）
    # 返回每个股票最近一次涨停日期和价格
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
        )
        SELECT 
            lu.thscode,
            sl.name,
            lu.trade_date,
            lu.close_price,
            lu.pct_chg
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
    # 日期转为字符串
    for r in records:
        r['trade_date'] = str(r['trade_date'])
    
    return jsonify({'stocks': records, 'dates': [str(d) for d in date_list]})

@app.route('/api/kline_with_marker')
def get_kline_with_marker():
    """获取K线数据并标记涨停位置"""
    code = request.args.get('code')
    limit = request.args.get('limit', 500, type=int)
    if not code:
        return jsonify({'error': '缺少code参数'}), 400
    
    db = get_db()
    # 获取K线数据
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
    
    # 获取涨停标记（最近12天内）
    marker_sql = """
        SELECT trade_date, close_price, pct_chg
        FROM daily_quotes
        WHERE thscode = ?
          AND pct_chg >= 9.8
          AND trade_date >= (SELECT MAX(trade_date) - INTERVAL 12 DAY FROM daily_quotes)
        ORDER BY trade_date
    """
    markers_df = db.execute(marker_sql, [code]).df()
    db.close()
    
    records = df.to_dict(orient='records')
    for r in records:
        r['trade_date'] = str(r['trade_date'])
    
    markers = []
    if not markers_df.empty:
        for _, row in markers_df.iterrows():
            markers.append({
                'trade_date': str(row['trade_date']),
                'price': float(row['close_price']),
                'pct_chg': float(row['pct_chg'])
            })
    
    return jsonify({'data': records, 'markers': markers})

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