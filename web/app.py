from flask import Flask, render_template, jsonify, request
import duckdb
import pandas as pd
import subprocess
import os

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
        return {
            'success': True,
            'output': result.stdout,
            'error': result.stderr
        }
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