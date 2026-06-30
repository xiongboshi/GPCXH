import time
import akshare as ak
import pandas as pd
import ast
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Set
from 公用方法.发送邮箱 import send_email_notification
from collections import defaultdict

# 全局计数器：记录每只股票连续触发次数
_CONTINUOUS_TRIGGER_COUNT = defaultdict(int)



# 缓存文件路径
CACHE_FILE = 'stock_industry_cache.csv'
CACHE_EXPIRE_DAYS = 15  # 15天过期


def load_cache():
    """加载本地缓存（支持带 update_date 的新格式，也兼容旧格式）"""
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        df = pd.read_csv(CACHE_FILE, dtype={'code': str})
        cache = {}
        now = datetime.now()

        for _, row in df.iterrows():
            code = row['code']
            industry = row['industry']
            
            # 检查是否有 update_date 列
            if 'update_date' in row and pd.notna(row['update_date']):
                try:
                    update_time = datetime.strptime(str(row['update_date']), '%Y-%m-%d')
                    if now - update_time > timedelta(days=CACHE_EXPIRE_DAYS):
                        continue  # 过期，跳过
                except Exception:
                    pass  # 日期解析失败，当作不过期（保守策略）
            
            # 如果是旧缓存（无 update_date），默认认为未过期（或可设为立即过期）
            # 这里我们选择：**旧缓存视为有效，但下次更新会加上日期**
            cache[code] = industry

        return cache
    except Exception as e:
        print(f"⚠️ 缓存文件读取失败: {e}")
        return {}


def save_to_cache(code, industry):
    """保存到缓存，带 update_date，避免重复（覆盖更新）"""
    code = str(code).zfill(6)
    today = datetime.now().strftime('%Y-%m-%d')

    # 读取现有缓存（全部）
    if os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE, dtype={'code': str})
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    # 确保列存在
    if 'code' not in df.columns:
        df = pd.DataFrame(columns=['code', 'industry', 'update_date'])

    # 查找是否已存在
    if code in df['code'].values:
        # 更新已有行
        df.loc[df['code'] == code, ['industry', 'update_date']] = [industry, today]
    else:
        # 追加新行
        new_row = pd.DataFrame([{'code': code, 'industry': industry, 'update_date': today}])
        df = pd.concat([df, new_row], ignore_index=True)

    # 保存
    df.to_csv(CACHE_FILE, index=False, encoding='utf-8-sig')


# ========== 以下函数保持完全不变 ==========
def find_gp_hy_name(stock_code):
    """
    查找股票所属行业（带本地缓存）
    """
    # 标准化代码（确保6位）
    stock_code = str(stock_code).zfill(6)

    # 1. 先查缓存
    cache = load_cache()
    if stock_code in cache:
        print(f"✅ 从缓存获取 {stock_code} => {cache[stock_code]}")
        return cache[stock_code]

    # 2. 缓存未命中，调用 AkShare
    try:
        print(f"📡 正在查询 {stock_code} 行业信息...")
        gp_detail = ak.stock_individual_basic_info_xq(stock_code, token='7f647581bc6af53c66217c3a1e96485fb4481399')
        # print(gp_detail)  # 可注释掉避免刷屏
        
        # 提取 affiliate_industry 字段
        row = gp_detail[gp_detail['item'] == 'affiliate_industry']
        if row.empty:
            raise ValueError("未找到 affiliate_industry 字段")
            
        affiliate_industry_value = row['value'].iloc[0]
        
        # 解析行业名称
        if isinstance(affiliate_industry_value, str):
            industry_dict = ast.literal_eval(affiliate_industry_value)
        else:
            industry_dict = affiliate_industry_value
            
        industry_name = industry_dict.get('ind_name', '未知行业')
        
        # 3. 保存到缓存
        save_to_cache(stock_code, industry_name)
        print(f"💾 已缓存 {stock_code} => {industry_name}")
        return industry_name

    except Exception as e:
        print(f'❌ find_gp_hy_name({stock_code}) => err: {e}')
        return "未知行业"


def is_top_industry(stock_code, date, gp_zt_arr, gp_zt_ph_arr):
    """
    判断个股所属的板块是否是涨幅前几的板块
    """
    try:
        if len(gp_zt_ph_arr) <= 0:
            industry_counts = Counter()
            if gp_zt_arr:
                for gp_code in gp_zt_arr:
                    industry_name = find_gp_hy_name(gp_code)
                    industry_counts[industry_name] += 1
            top_10_industries = industry_counts.most_common(10)
            gp_zt_ph_arr.extend([industry for industry, _ in top_10_industries])
            print("📈 涨停数前10行业:", gp_zt_ph_arr)

        content_em = ak.stock_board_industry_summary_ths()
        top_up_industries = content_em.nlargest(3, '上涨家数')['板块'].tolist()
        top_zdf_industries = content_em.nlargest(5, '涨跌幅')['板块'].tolist()

        industry_name = find_gp_hy_name(stock_code)

        is_top = (
            industry_name in gp_zt_ph_arr or
            industry_name in top_up_industries or
            industry_name in top_zdf_industries
        )
        print(f"🔍 {stock_code} 所属行业 '{industry_name}' 是否热门: {is_top}")
        return is_top

    except Exception as e:
        print('is_top_3_industry()=>err:', str(e))
        return False
    






import pandas as pd
from typing import List, Set
import akshare as ak

def check_continuous_buy_blocks_per_stock(
    watch_stocks: List[str],
    min_consecutive: int = 5,
    min_total_hands: int = 30000,
    email_config: dict = None  # 新增：邮件配置
) -> Set[str]:
    """
    对每只监控股票，独立分析其大单流：
    - 提取该股所有大单（按时间排序）
    - 寻找连续的「买盘」段（中间不能有该股的卖盘）
    - 若某段长度 ≥ min_consecutive 且总手数 ≥ min_total_hands，则触发
    
    ✅ 使用 (时间秒, 方向, 成交量, 价格, 成交额) 做严格去重，避免同花顺网页重复推送干扰
    ✅ 其他股票的大单不会影响连续性判断
    """
    try:
        # print("📡 正在获取大单追踪数据...")
        big_df = ak.stock_fund_flow_big_deal()
        
        if big_df.empty:
            print("⚠️ 大单数据为空")
            return set()
        
        # 打印列名便于调试
        # print("📊 列名:", big_df.columns.tolist())
        
        # 标准化股票代码
        def normalize_code(code):
            return str(code).strip().replace('.SH', '').replace('.SZ', '').replace('sh.', '').replace('sz.', '').zfill(6)
        
        big_df['股票代码'] = big_df['股票代码'].apply(normalize_code)
        watch_set = {normalize_code(code) for code in watch_stocks}
        
        # 只保留监控股票
        filtered_df = big_df[big_df['股票代码'].isin(watch_set)].copy()
        if filtered_df.empty:
            # print("✅ 监控股票今日无大单记录")
            return set()
        
        
        # 标准化时间
        filtered_df['成交时间'] = pd.to_datetime(filtered_df['成交时间'], errors='coerce')
        filtered_df = filtered_df.dropna(subset=['成交时间']).copy()
        
        # === 关键：构造去重键 ===
        def make_dedup_key(row):
            # 时间精确到秒（同花顺时间戳通常无毫秒）
            time_sec = row['成交时间'].strftime('%Y-%m-%d %H:%M:%S')
            key_parts = [
                row['股票代码'],
                time_sec,
                row['大单性质'],
                str(int(row['成交量']))  # 转为整数字符串避免浮点误差
            ]
            # 价格保留2位小数（防止浮点精度问题）
            key_parts.append(f"{row['成交价格']:.2f}")
            # 成交额也保留2位小数
            key_parts.append(f"{row['成交额']:.2f}")
            return "|".join(key_parts)
        
        filtered_df['dedup_key'] = filtered_df.apply(make_dedup_key, axis=1)
        # 全局去重（同一监控股池内）
        filtered_df = filtered_df.drop_duplicates(subset=['dedup_key']).copy()
        filtered_df = filtered_df.sort_values('成交时间', ascending=True).reset_index(drop=True)
        
        qualified = set()
        
        for stock in watch_set:
            stock_df = filtered_df[filtered_df['股票代码'] == stock].copy()
            if stock_df.empty:
                continue
            
            # 提取必要字段（顺序必须一致）
            trades = stock_df[['大单性质', '成交量', '成交时间', '股票代码','涨跌幅']].values
            # print(f"\n🔍 股票 {stock} 去重后大单流 ({len(trades)} 笔):")
            # print(trades[:10])  # 只打印前10笔避免刷屏
            
            i = 0
            found = False
            while i < len(trades):
                if trades[i][0] == '买盘':
                    j = i
                    total_volume = 0
                    # 向前扩展连续买盘
                    while j < len(trades) and trades[j][0] == '买盘':
                        total_volume += trades[j][1]
                        j += 1
                    
                    length = j - i
                    total_hands = total_volume / 100.0
                    
                    # ✅ 修复：必须是 <=，不是 <=
                    if length <= min_consecutive and total_hands >= min_total_hands:
                        last_time = trades[j - 1][2]  # j-1 是最后一笔买盘
                        print(f"🔥 股票 {stock} 发现连续 {length} 笔买盘，共 {total_hands:,.0f} 手 (≥{min_total_hands}) @ {last_time}")
                        qualified.add(stock)
                        found = True
                        break  # 找到一个即可
                    
                    i = j  # 跳过已处理的连续段
                else:
                    i += 1
            
            # if not found:
            #     print(f"📊 股票 {stock} 无满足条件的连续买盘段")
        
        # if not qualified:
        #     print(f"✅ 无监控股票满足「连续≥{min_consecutive}笔买盘且≥{min_total_hands}手」条件")
        
        return qualified
        
    except Exception as e:
        print(f"❌ 连续买盘检测失败: {e}")
        import traceback
        traceback.print_exc()
        return set()
    









def check_continuous_buy_blocks_per_stock_with_email(
    watch_stocks: List[str],
    min_consecutive: int = 5,
    min_total_hands: int = 30000,
    email_config: dict = None,
    max_email_triggers: int = 10  # 新增参数：最大连续邮件次数
) -> Set[str]:
    """
    增强版：发现符合条件的连续买盘后，自动发送邮件通知
    支持防刷屏：同一股票连续触发超过 max_email_triggers 次则不再发邮件
    """
    global _CONTINUOUS_TRIGGER_COUNT
    
    qualified = check_continuous_buy_blocks_per_stock(watch_stocks, min_consecutive, min_total_hands)
    
    # 初始化本次需要发邮件的股票集合
    stocks_to_email = set()
    
    # 更新计数器 & 筛选可发邮件的股票
    for stock in watch_stocks:
        if stock in qualified:
            # 触发：计数 +1
            _CONTINUOUS_TRIGGER_COUNT[stock] += 1
            # 未超限才加入邮件列表
            if _CONTINUOUS_TRIGGER_COUNT[stock] <= max_email_triggers:
                stocks_to_email.add(stock)
            # 可选：打印日志（调试用）
            # print(f"[DEBUG] {stock} 连续触发第 {_CONTINUOUS_TRIGGER_COUNT[stock]} 次")
        else:
            # 未触发：重置计数器
            _CONTINUOUS_TRIGGER_COUNT[stock] = 0

    # 发送邮件（仅当有可通知的股票）
    if stocks_to_email and email_config:
        subject = f"【大单监控】{len(stocks_to_email)} 只股票满足连续买盘条件！"
        body_lines = [
            f"时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"监控股票池: {', '.join(watch_stocks)}",
            f"触发条件: 连续 ≥{min_consecutive} 笔买盘 且 总手数 ≥{min_total_hands:,} 手",
            f"防刷屏设置: 同一股票最多连续通知 {max_email_triggers} 次",
            "",
            "本次触发股票:",
        ]
        for stock in sorted(stocks_to_email):
            count = _CONTINUOUS_TRIGGER_COUNT[stock]
            suffix = f" (第{count}次)" if count > 1 else ""
            body_lines.append(f"  • {stock}{suffix}")
        body_lines.extend([
            "",
            "请尽快核查交易机会！",
            "---",
            "由量化监控系统自动发送"
        ])
        body = "\n".join(body_lines)
        
        send_email_notification(
            to_emails=email_config['to_emails'],
            subject=subject,
            body=body,
            smtp_server=email_config.get('smtp_server', 'smtp.qq.com'),
            smtp_port=email_config.get('smtp_port', 465),
            sender_email=email_config['sender_email'],
            sender_password=email_config['sender_password']
        )
    
    return qualified