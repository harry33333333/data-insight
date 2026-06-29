#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generated_etl.py
用户行为数据 ETL 脚本：连接 PostgreSQL，执行聚合统计，输出 report_data.json
"""

import os
import sys
import json
import traceback

# ============================================================
# 【环境与连接避坑】必须在最开头设置编码，防止 Windows 下 psycopg2 乱码
# ============================================================
os.environ['PGCLIENTENCODING'] = 'UTF8'

import psycopg2
import psycopg2.extras


# ============================================================
# 数据契约（Data Contract）
# ============================================================
def build_empty_report():
    """构建符合契约的空报告骨架"""
    return {
        "overview": {
            "dau": 0,
            "uv": 0,
            "pv": 0,
            "avg_duration": 0.0,
        },
        "pv_ranks": [],
        "user_layers": [],
    }


def build_mock_report():
    """降级 Mock 报告，字段名严格匹配契约"""
    return {
        "overview": {
            "dau": 1200,
            "uv": 8500,
            "pv": 45000,
            "avg_duration": 120.5,
        },
        "pv_ranks": [
            {"domain": "主站", "page_name": "首页", "uv": 5200, "pv": 18000},
            {"domain": "主站", "page_name": "商品详情页", "uv": 4100, "pv": 12500},
            {"domain": "主站", "page_name": "搜索结果页", "uv": 3800, "pv": 9800},
            {"domain": "主站", "page_name": "个人中心", "uv": 2900, "pv": 6200},
            {"domain": "主站", "page_name": "购物车", "uv": 2100, "pv": 4500},
        ],
        "user_layers": [
            {"domain": "主站", "layer": "高频用户", "user_count": 1800},
            {"domain": "主站", "layer": "中频用户", "user_count": 3500},
            {"domain": "主站", "layer": "低频用户", "user_count": 3200},
        ],
    }


# ============================================================
# 数据库连接
# ============================================================
def get_connection():
    """使用环境变量连接 PostgreSQL"""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    database = os.environ.get("POSTGRES_DATABASE", "postgres")  # 必须用 POSTGRES_DATABASE

    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=database,
        client_encoding='UTF8',
    )
    conn.set_client_encoding('UTF8')
    return conn


# ============================================================
# 动态发现 user_behavior_ 前缀表
# ============================================================
def discover_tables(cursor):
    """发现所有 user_behavior_ 前缀的表名"""
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name LIKE 'user_behavior_%'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def get_table_columns(cursor, table_name):
    """获取指定表的列名列表"""
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return [row[0] for row in cursor.fetchall()]


def build_union_all(table_names):
    """将多张表用 UNION ALL 拼接，表名用双引号包裹以支持中文"""
    parts = []
    for t in table_names:
        parts.append(f'SELECT * FROM "{t}"')
    return " UNION ALL ".join(parts)


# ============================================================
# 核心查询
# ============================================================
def query_overview(cursor, union_sql, columns):
    """
    查询 Overview: dau, uv, pv, avg_duration
    """
    # 检测可用字段
    has_user_id = "user_id" in columns
    has_action_type = "action_type" in columns
    has_duration = "duration" in columns
    has_event_time = "event_time" in columns

    # 构建 PV 条件
    pv_condition = ""
    if has_action_type:
        pv_condition = "WHERE action_type = 'view'"

    # 计算总天数
    date_range_sql = ""
    if has_event_time:
        date_range_sql = f"""
            , date_info AS (
                SELECT
                    MIN(event_time::date) AS min_dt,
                    MAX(event_time::date) AS max_dt
                FROM ({union_sql}) AS ub
            )
        """

    # DAU 计算：日均活跃用户
    if has_event_time and has_user_id:
        dau_sql = f"""
            SELECT COALESCE(
                ROUND(AVG(daily_uv), 0)
            , 0)::int AS dau
            FROM (
                SELECT event_time::date AS dt,
                       COUNT(DISTINCT user_id) AS daily_uv
                FROM ({union_sql}) AS ub
                GROUP BY event_time::date
            ) daily
        """
    elif has_user_id:
        dau_sql = f"""
            SELECT COUNT(DISTINCT user_id)::int AS dau
            FROM ({union_sql}) AS ub
        """
    else:
        dau_sql = "SELECT 0::int AS dau"

    # UV 计算
    if has_user_id:
        uv_sql = f"""
            SELECT COUNT(DISTINCT user_id)::int AS uv
            FROM ({union_sql}) AS ub
        """
    else:
        uv_sql = "SELECT 0::int AS uv"

    # PV 计算
    if has_action_type:
        pv_sql = f"""
            SELECT COUNT(*)::int AS pv
            FROM ({union_sql}) AS ub
            WHERE action_type = 'view'
        """
    else:
        pv_sql = f"""
            SELECT COUNT(*)::int AS pv
            FROM ({union_sql}) AS ub
        """

    # 平均时长
    if has_duration:
        if has_action_type:
            avg_dur_sql = f"""
                SELECT COALESCE(
                    ROUND(AVG(duration)::numeric, 2)
                , 0.0)::float AS avg_duration
                FROM ({union_sql}) AS ub
                WHERE action_type = 'view'
            """
        else:
            avg_dur_sql = f"""
                SELECT COALESCE(
                    ROUND(AVG(duration)::numeric, 2)
                , 0.0)::float AS avg_duration
                FROM ({union_sql}) AS ub
            """
    else:
        avg_dur_sql = "SELECT 0.0::float AS avg_duration"

    # 执行各子查询
    cursor.execute(dau_sql)
    dau = cursor.fetchone()[0]

    cursor.execute(uv_sql)
    uv = cursor.fetchone()[0]

    cursor.execute(pv_sql)
    pv = cursor.fetchone()[0]

    cursor.execute(avg_dur_sql)
    avg_duration = float(cursor.fetchone()[0])

    return {
        "dau": int(dau) if dau else 0,
        "uv": int(uv) if uv else 0,
        "pv": int(pv) if pv else 0,
        "avg_duration": round(avg_duration, 2) if avg_duration else 0.0,
    }


def query_pv_ranks(cursor, union_sql, columns, top_n=5):
    """
    查询 PV 排行: domain, page_name, uv, pv
    """
    has_module_name = "module_name" in columns
    has_user_id = "user_id" in columns
    has_action_type = "action_type" in columns
    has_domain = "domain" in columns

    # 页面名称字段：优先 module_name，否则 page_name，否则 category
    page_field = None
    for candidate in ["module_name", "page_name", "category", "page"]:
        if candidate in columns:
            page_field = candidate
            break

    # domain 字段
    domain_field = None
    if has_domain:
        domain_field = "domain"

    if page_field is None:
        # 没有页面字段，返回空
        return []

    # 构建 PV 过滤
    pv_where = ""
    if has_action_type:
        pv_where = "WHERE action_type = 'view'"

    # 构建 domain 表达式
    domain_expr = f"'主站'" if domain_field is None else f'COALESCE("{domain_field}"::text, \'主站\')'

    # UV 表达式
    uv_expr = "COUNT(DISTINCT user_id)::int" if has_user_id else "0::int"

    sql = f"""
        SELECT
            {domain_expr} AS domain,
            "{page_field}"::text AS page_name,
            {uv_expr} AS uv,
            COUNT(*)::int AS pv
        FROM ({union_sql}) AS ub
        {pv_where}
        GROUP BY {domain_expr}, "{page_field}"::text
        ORDER BY pv DESC
        LIMIT {top_n}
    """

    cursor.execute(sql)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "domain": str(row[0]) if row[0] else "主站",
            "page_name": str(row[1]) if row[1] else "未知页面",
            "uv": int(row[2]) if row[2] else 0,
            "pv": int(row[3]) if row[3] else 0,
        })
    return result


def query_user_layers(cursor, union_sql, columns):
    """
    查询用户分层: domain, layer, user_count
    """
    has_user_id = "user_id" in columns
    has_action_type = "action_type" in columns
    has_event_time = "event_time" in columns
    has_domain = "domain" in columns

    if not has_user_id:
        return []

    # domain 字段
    domain_field = None
    if has_domain:
        domain_field = "domain"

    domain_expr = f"'主站'" if domain_field is None else f'COALESCE("{domain_field}"::text, \'主站\')'

    # 活跃天数
    if has_event_time:
        active_days_expr = "COUNT(DISTINCT event_time::date)"
    else:
        active_days_expr = "1"

    # PV 计算
    if has_action_type:
        pv_expr = "COUNT(CASE WHEN action_type = 'view' THEN 1 END)"
    else:
        pv_expr = "COUNT(*)"

    sql = f"""
        WITH user_aggregation AS (
            SELECT
                user_id,
                {domain_expr} AS domain,
                {active_days_expr} AS active_days,
                {pv_expr} AS total_pv
            FROM ({union_sql}) AS ub
            GROUP BY user_id, {domain_expr}
        ),
        user_layering AS (
            SELECT
                user_id,
                domain,
                CASE
                    WHEN active_days >= 5 OR total_pv >= 50 THEN '高频用户'
                    WHEN active_days >= 2 OR total_pv >= 10 THEN '中频用户'
                    ELSE '低频用户'
                END AS user_layer
            FROM user_aggregation
        )
        SELECT
            domain,
            user_layer,
            COUNT(DISTINCT user_id)::int AS user_count
        FROM user_layering
        GROUP BY domain, user_layer
        ORDER BY
            domain,
            CASE user_layer
                WHEN '高频用户' THEN 1
                WHEN '中频用户' THEN 2
                WHEN '低频用户' THEN 3
            END
    """

    cursor.execute(sql)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "domain": str(row[0]) if row[0] else "主站",
            "layer": str(row[1]) if row[1] else "未知",
            "user_count": int(row[2]) if row[2] else 0,
        })
    return result


# ============================================================
# 主流程
# ============================================================
def main():
    report = build_empty_report()
    use_mock = False

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. 发现 user_behavior_ 前缀表
        table_names = discover_tables(cursor)
        print(f"[INFO] 发现 {len(table_names)} 张 user_behavior_ 表: {table_names}")

        if not table_names:
            raise RuntimeError("未发现任何 user_behavior_ 前缀的表，启用 Mock 降级")

        # 2. 获取第一张表的列信息（假设各表结构一致）
        columns = get_table_columns(cursor, table_names[0])
        print(f"[INFO] 表 {table_names[0]} 的列: {columns}")

        if not columns:
            raise RuntimeError(f"表 {table_names[0]} 无列信息，启用 Mock 降级")

        # 3. 构建 UNION ALL 视图 SQL（表名用双引号包裹，支持中文表名）
        union_sql = build_union_all(table_names)

        # 4. 查询 Overview
        print("[INFO] 正在查询 Overview...")
        report["overview"] = query_overview(cursor, union_sql, columns)
        print(f"[INFO] Overview: {report['overview']}")

        # 5. 查询 PV 排行
        print("[INFO] 正在查询 PV 排行...")
        report["pv_ranks"] = query_pv_ranks(cursor, union_sql, columns, top_n=5)
        print(f"[INFO] PV 排行: {report['pv_ranks']}")

        # 6. 查询用户分层
        print("[INFO] 正在查询用户分层...")
        report["user_layers"] = query_user_layers(cursor, union_sql, columns)
        print(f"[INFO] 用户分层: {report['user_layers']}")

        cursor.close()
        conn.close()
        print("[INFO] 数据库查询完成，连接已关闭。")

    except Exception as e:
        use_mock = True
        print(f"[WARN] 数据库处理异常: {e}")
        traceback.print_exc()
        print("[WARN] 启用 Mock 降级逻辑...")
        report = build_mock_report()

    # ============================================================
    # 最终校验：确保输出严格符合契约
    # ============================================================
    # 校验 overview
    ov = report.get("overview", {})
    report["overview"] = {
        "dau": int(ov.get("dau", 0)),
        "uv": int(ov.get("uv", 0)),
        "pv": int(ov.get("pv", 0)),
        "avg_duration": float(ov.get("avg_duration", 0.0)),
    }

    # 校验 pv_ranks
    validated_pv_ranks = []
    for item in report.get("pv_ranks", []):
        validated_pv_ranks.append({
            "domain": str(item.get("domain", "主站")),
            "page_name": str(item.get("page_name", "未知页面")),
            "uv": int(item.get("uv", 0)),
            "pv": int(item.get("pv", 0)),
        })
    report["pv_ranks"] = validated_pv_ranks

    # 校验 user_layers
    validated_user_layers = []
    for item in report.get("user_layers", []):
        validated_user_layers.append({
            "domain": str(item.get("domain", "主站")),
            "layer": str(item.get("layer", "未知")),
            "user_count": int(item.get("user_count", 0)),
        })
    report["user_layers"] = validated_user_layers

    # ============================================================
    # 写入 report_data.json
    # ============================================================
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[INFO] 报告已写入: {output_path}")
    print(f"[INFO] 是否使用 Mock 数据: {use_mock}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()