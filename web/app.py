import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import amount

from flask import Flask, render_template, jsonify, request
import duckdb
import pandas as pd
import subprocess
import os
from datetime import datetime, timedelta

# 项目根目录
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'market.duckdb')


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

# ===== 修改：涨停股票识别（排除当天） =====
@app.route('/api/limit_up_stocks')
def get_limit_up_stocks():
    """获取最近12个交易日内有涨停的股票列表（排除今天涨停）"""
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
    
    # 2. 查询这些日期中涨跌幅 >= 9.8 的股票（涨停），并排除今天
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
              AND trade_date != CURRENT_DATE   -- ✅ 排除今天涨停
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
    
    # 获取涨停标记（最近12天内，排除今天）
    marker_sql = """
        SELECT trade_date, close_price, pct_chg
        FROM daily_quotes
        WHERE thscode = ?
          AND pct_chg >= 9.8
          AND trade_date >= (SELECT MAX(trade_date) - INTERVAL 12 DAY FROM daily_quotes)
          AND trade_date != CURRENT_DATE   -- ✅ 排除今天
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


# ===== 策略检测接口 =====
@app.route('/api/run_strategy', methods=['POST'])
def run_strategy():
    """
    执行策略检测
    """
    try:
        data = request.get_json()
        strategy_type = data.get('strategy_type', 'full')
        stock_list = data.get('stock_list', None)

        # 如果未提供股票列表，则获取当前涨停股票（排除今天）
        if not stock_list:
            db = get_db()
            # 直接查询涨停股票代码
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

        # 执行策略
        result_df = amount.run_strategy_on_stock_list(stock_list, lookback_days=300, strategy_type=strategy_type)

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