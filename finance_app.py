import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
from openai import OpenAI

st.set_page_config(page_title="个人理财储蓄助手 · 极简记账本", layout="wide")

# [新增] 全局自定义 CSS 样式（集成 Font Awesome 6 专业图标库）
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

<style>
    /* ============================================================
       设计系统 · Design System
       ============================================================ */

    /* === 色彩令牌 === */
    :root {
        --color-primary:      #1a56db;   /* 主色：深邃蓝 */
        --color-primary-lt:   #3b82f6;   /* 主色浅 */
        --color-accent:       #0891b2;   /* 强调：青蓝 */
        --color-success:      #059669;   /* 成功/收入 */
        --color-warning:      #d97706;   /* 警告 */
        --color-danger:       #dc2626;   /* 危险/超支 */
        --color-bg:           #f8fafc;   /* 页面背景 */
        --color-card:         #ffffff;   /* 卡片背景 */
        --color-sidebar:      #f1f5f9;   /* 侧边栏 */
        --color-text:         #1e293b;   /* 正文 */
        --color-text-muted:   #64748b;   /* 次要文字 */
        --color-border:       #e2e8f0;   /* 边框 */
        --radius-sm:          8px;
        --radius-md:          12px;
        --radius-lg:          16px;
        --shadow-sm:          0 1px 3px rgba(0,0,0,.04);
        --shadow-md:          0 4px 12px rgba(0,0,0,.06);
        --shadow-lg:          0 8px 24px rgba(0,0,0,.08);
        --transition:         all .25s cubic-bezier(.4,0,.2,1);
    }

    /* === 全局 === */
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* === 标题层级 === */
    h1 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem !important;
    }
    h1 i {
        color: var(--color-primary);
        margin-right: 10px;
        font-size: 1.6rem;
    }
    h2 {
        font-size: 1.4rem !important;
        font-weight: 600 !important;
        color: #1e293b !important;
        letter-spacing: -0.01em;
    }
    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }

    /* === 分隔线 === */
    hr, .stDivider {
        border-color: var(--color-border) !important;
        margin: 1.5rem 0 !important;
    }

    /* === 卡片容器 === */
    div[data-testid="stMetric"] {
        background: var(--color-card);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 1.25rem 1rem;
        box-shadow: var(--shadow-sm);
        transition: var(--transition);
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: var(--color-text-muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: var(--color-text) !important;
    }

    /* === 表格 === */
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        background: var(--color-card);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--color-border);
        padding: 0.5rem;
    }
    [data-testid="stDataFrame"] th,
    [data-testid="stTable"] th {
        background: #f8fafc !important;
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 2px solid var(--color-border) !important;
        padding: 0.75rem 1rem !important;
    }
    [data-testid="stDataFrame"] td,
    [data-testid="stTable"] td {
        padding: 0.65rem 1rem !important;
        font-size: 0.9rem;
    }

    /* === 侧边栏 === */
    [data-testid="stSidebar"] {
        background: var(--color-sidebar);
        border-right: 1px solid var(--color-border);
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 8px 12px;
        border-radius: var(--radius-sm);
        transition: var(--transition);
        font-size: 0.9rem;
        margin-bottom: 2px;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #e2e8f0;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-selected="true"] span {
        background: var(--color-primary) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        padding: 0.75rem;
        margin: 0.25rem 0;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }

    /* === 按钮 === */
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: var(--transition) !important;
        border: none !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(26,86,219,.25);
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* === 信息提示 === */
    .stAlert {
        border-radius: var(--radius-sm) !important;
        border: none !important;
        font-size: 0.9rem;
    }

    /* === 表单输入 === */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        border-radius: var(--radius-sm) !important;
        border-color: var(--color-border) !important;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within {
        border-color: var(--color-primary) !important;
        box-shadow: 0 0 0 3px rgba(26,86,219,.1) !important;
    }

    /* === 进度条 === */
    .stProgress > div > div {
        border-radius: 20px;
    }

    /* ===== Font Awesome 图标样式 ===== */
    .fa-icon-primary   { color: #1a56db; }
    .fa-icon-success   { color: #059669; }
    .fa-icon-danger    { color: #dc2626; }
    .fa-icon-warning   { color: #d97706; }
    .fa-icon-muted     { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# ---------- 数据库初始化 ----------
conn = sqlite3.connect("finance.db")
cursor = conn.cursor()

# [修改] 建表时包含 description 字段
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        category TEXT,
        amount REAL,
        date TEXT,
        description TEXT DEFAULT '',
        user_id INTEGER DEFAULT 1
    )
""")

# [修改] 兼容旧表：如果 transactions 表不存在 description 列则添加
cursor.execute("PRAGMA table_info(transactions)")
columns = [col[1] for col in cursor.fetchall()]
if "description" not in columns:
    cursor.execute("ALTER TABLE transactions ADD COLUMN description TEXT DEFAULT ''")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_month TEXT,
        amount REAL,
        user_id INTEGER DEFAULT 1
    )
""")

# [新增] 类别预算表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS category_budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        year_month TEXT,
        amount REAL,
        user_id INTEGER DEFAULT 1
    )
""")

# [新增] 快捷按钮表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS quick_buttons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        amount REAL,
        is_default INTEGER DEFAULT 0,
        user_id INTEGER DEFAULT 1
    )
""")

# 初始化默认按钮（如果表为空）
cursor.execute("SELECT COUNT(*) FROM quick_buttons")
if cursor.fetchone()[0] == 0:
    defaults = [
        ("🍜 早餐+30", "餐饮", 30),
        ("🚇 地铁+10", "交通", 10),
        ("☕ 咖啡+25", "餐饮", 25),
        ("🛒 购物+100", "购物", 100),
        ("🍱 外卖+35", "餐饮", 35),
        ("🎬 电影+50", "娱乐", 50),
    ]
    for name, cat, amt in defaults:
        cursor.execute(
            "INSERT INTO quick_buttons (name, category, amount, is_default, user_id) VALUES (?, ?, ?, 1, 1)",
            (name, cat, amt)
        )

# [新增] 负债管理表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debt_type TEXT,
        total_amount REAL,
        annual_rate REAL,
        borrowed_date TEXT,
        due_date TEXT,
        status TEXT DEFAULT '进行中',
        description TEXT DEFAULT '',
        user_id INTEGER DEFAULT 1
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS debt_repayments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debt_id INTEGER,
        repayment_amount REAL,
        repayment_date TEXT,
        description TEXT DEFAULT '',
        user_id INTEGER DEFAULT 1
    )
""")

conn.commit()
conn.close()

today = date.today()
year_month = today.strftime("%Y-%m")

# ---------- 侧边栏：页面导航 ----------
st.sidebar.markdown("---")
# 用 session_state 管理页面切换，支持从快捷录入区域跳转到自定义页
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "🏠 记账主页"
page = st.sidebar.radio(
    "导航",
    ["🏠 记账主页", "📊 数据分析", "📋 月度报告", "⚙️ 自定义快捷按钮", "📉 负债管理"],
    index=["🏠 记账主页", "📊 数据分析", "📋 月度报告", "⚙️ 自定义快捷按钮", "📉 负债管理"].index(st.session_state["nav_page"])
)
st.session_state["nav_page"] = page

# ---------- 侧边栏：预算 ----------
st.sidebar.markdown("---")

conn = sqlite3.connect("finance.db")
cursor = conn.cursor()
cursor.execute(
    "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='支出' AND substr(date, 1, 7)=?",
    (year_month,)
)
monthly_expense = cursor.fetchone()[0]

cursor.execute("SELECT amount FROM budget WHERE year_month=? AND user_id=?", (year_month, 1))
budget_row = cursor.fetchone()
conn.close()

st.sidebar.subheader("月度预算")
budget_input = st.sidebar.number_input("设置本月预算总金额（元）", min_value=0, value=3000)
if st.sidebar.button("保存预算"):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM budget WHERE year_month=? AND user_id=?", (year_month, 1))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE budget SET amount=? WHERE year_month=? AND user_id=?", (budget_input, year_month, 1))
    else:
        cursor.execute("INSERT INTO budget (year_month, amount, user_id) VALUES (?, ?, ?)", (year_month, budget_input, 1))
    conn.commit()
    conn.close()
    st.sidebar.success("预算已保存！")

st.sidebar.markdown("---")
st.sidebar.markdown("### 预算执行")
if budget_row:
    budget_amount = budget_row[0]
    remaining = budget_amount - monthly_expense
    st.sidebar.metric("本月预算", f"¥{budget_amount:.2f}")
    st.sidebar.metric("实际支出", f"¥{monthly_expense:.2f}")
    st.sidebar.metric("剩余", f"¥{remaining:.2f}")
    if monthly_expense > budget_amount:
        st.sidebar.error(f"已超支 ¥{monthly_expense - budget_amount:.2f} 元")
else:
    st.sidebar.info("未设置本月预算")

# [新增] 侧边栏：类别预算管理
st.sidebar.markdown("---")
st.sidebar.subheader("类别预算管理")

# 查询当前月份已有的类别预算
conn = sqlite3.connect("finance.db")
cursor = conn.cursor()
cursor.execute(
    "SELECT category, amount FROM category_budget WHERE year_month=? AND user_id=? ORDER BY category",
    (year_month, 1)
)
cat_budgets = cursor.fetchall()
conn.close()

if cat_budgets:
    for cat, amt in cat_budgets:
        st.sidebar.text(f"{cat}：¥{amt:.2f}")
else:
    st.sidebar.caption("暂无类别预算")

cat_select = st.sidebar.selectbox(
    "选择类别",
    ["餐饮", "购物", "交通", "娱乐", "住宿", "医疗", "教育", "通讯", "人情", "其他"],
    key="cat_budget_select"
)
cat_amount = st.sidebar.number_input("类别预算金额（元）", min_value=0, value=0, key="cat_budget_amount")
if st.sidebar.button("保存类别预算"):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM category_budget WHERE category=? AND year_month=? AND user_id=?",
        (cat_select, year_month, 1)
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            "UPDATE category_budget SET amount=? WHERE category=? AND year_month=? AND user_id=?",
            (cat_amount, cat_select, year_month, 1)
        )
    else:
        cursor.execute(
            "INSERT INTO category_budget (category, year_month, amount, user_id) VALUES (?, ?, ?, ?)",
            (cat_select, year_month, cat_amount, 1)
        )
    conn.commit()
    conn.close()
    st.sidebar.success(f"{cat_select} 类别预算已保存！")

# ========== 页面内容 ==========
if page == "🏠 记账主页":
    st.markdown('<h1><i class="fa-solid fa-book-open"></i> 我的记账本</h1>', unsafe_allow_html=True)
    st.caption("记录每一笔收支，轻松掌握个人财务")

    # [新增] 仪表盘区域
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='收入' AND substr(date, 1, 7)=?",
        (year_month,)
    )
    monthly_income = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='支出' AND substr(date, 1, 7)=?",
        (year_month,)
    )
    monthly_expense_dash = cursor.fetchone()[0]
    cursor.execute("SELECT amount FROM budget WHERE year_month=? AND user_id=?", (year_month, 1))
    budget_dash = cursor.fetchone()
    conn.close()

    monthly_balance = monthly_income - monthly_expense_dash

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("本月收入", f"¥{monthly_income:.2f}")
    col2.metric("本月支出", f"¥{monthly_expense_dash:.2f}")

    balance_delta = f"¥{monthly_balance:.2f}"
    if monthly_balance >= 0:
        col3.metric("本月结余", f"¥{monthly_balance:.2f}", delta=balance_delta)
    else:
        col3.metric("本月结余", f"¥{monthly_balance:.2f}", delta=balance_delta, delta_color="inverse")

    if budget_dash:
        budget_remaining = budget_dash[0] - monthly_expense_dash
        remaining_delta = f"¥{budget_remaining:.2f}"
        if budget_remaining >= 0:
            col4.metric("预算剩余", f"¥{budget_remaining:.2f}", delta=remaining_delta)
        else:
            col4.metric("预算剩余", f"¥{budget_remaining:.2f}", delta=remaining_delta, delta_color="inverse")
    else:
        col4.metric("预算剩余", "未设置预算")

    # [新增] 总负债余额
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(SUM(d.total_amount - COALESCE(r.repaid, 0)), 0) "
        "FROM debts d "
        "LEFT JOIN (SELECT debt_id, SUM(repayment_amount) AS repaid FROM debt_repayments GROUP BY debt_id) r "
        "ON d.id = r.debt_id "
        "WHERE d.status = '进行中'"
    )
    total_debt = cursor.fetchone()[0]
    conn.close()
    col5.metric("总负债余额", f"¥{total_debt:.2f}")

    # [新增] 快捷录入（从数据库读取按钮）
    st.markdown("---")
    st.markdown('<h2><i class="fa-solid fa-bolt"></i> 快捷录入</h2>', unsafe_allow_html=True)

    def quick_insert(name, category, amount):
        """向数据库插入一条快捷支出记录"""
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (type, category, amount, date, description, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            ("支出", category, amount, today.strftime("%Y-%m-%d"), "快捷录入", 1)
        )
        conn.commit()
        conn.close()
        st.toast(f"✅ 已记录 {name} ¥{amount:.2f}", icon="💰")

    # 从数据库读取所有快捷按钮
    conn = sqlite3.connect("finance.db")
    btn_df = pd.read_sql_query(
        "SELECT id, name, category, amount FROM quick_buttons WHERE user_id=1 ORDER BY id",
        conn
    )
    conn.close()

    if not btn_df.empty:
        cols = st.columns(3)
        for i, (_, row) in enumerate(btn_df.iterrows()):
            btn_id = int(row["id"])
            if cols[i % 3].button(row["name"], key=f"qbtn_{btn_id}"):
                quick_insert(row["name"], row["category"], row["amount"])
    else:
        st.info("暂无快捷按钮，请去自定义页面添加")

    # [新增] 跳转到自定义页的按钮
    if st.button("✎ 自定义", key="goto_mgmt"):
        st.session_state["nav_page"] = "⚙️ 自定义快捷按钮"
        st.rerun()

    # 记账表单
    st.markdown("---")
    st.markdown('<h2><i class="fa-solid fa-pen-to-square"></i> 记账表单</h2>', unsafe_allow_html=True)
    trans_type = st.radio("类型", ["支出", "收入"], index=0, key="trans_type_radio")
    if trans_type == "支出":
        category_options = ["餐饮", "购物", "交通", "娱乐", "住宿", "医疗", "教育", "通讯", "人情", "其他"]
    else:
        category_options = ["工资", "奖金", "兼职", "理财", "红包", "报销", "其他"]
    with st.form("记账表单"):
        category = st.selectbox("类别", category_options, index=0)
        amount = st.number_input("金额（元）", min_value=0, step=1)
        trans_date = st.date_input("日期", value=today)
        # [修改] 新增备注输入框
        description = st.text_input("备注（可选）", placeholder="例如：中午和朋友聚餐")
        submitted = st.form_submit_button("记一笔")

    if submitted:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        # [修改] INSERT 增加 description 字段
        cursor.execute(
            "INSERT INTO transactions (type, category, amount, date, description, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (trans_type, category, amount, trans_date.strftime("%Y-%m-%d"), description, 1)
        )
        conn.commit()
        conn.close()
        st.success("✓ 记账成功！")

    st.markdown("---")

    # 当前总余额
    st.markdown('<h2><i class="fa-solid fa-coins"></i> 当前总余额</h2>', unsafe_allow_html=True)
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN type='收入' THEN amount ELSE 0 END), 0) - "
        "COALESCE(SUM(CASE WHEN type='支出' THEN amount ELSE 0 END), 0) "
        "FROM transactions"
    )
    balance = cursor.fetchone()[0]
    st.metric("当前总余额", f"¥{balance:.2f}")

    st.markdown("---")

    # [修改] 本月支出按类别汇总（增加预算和进度列）
    st.markdown('<h2><i class="fa-solid fa-table"></i> 本月支出分类汇总</h2>', unsafe_allow_html=True)
    cursor.execute(
        "SELECT category, SUM(amount) FROM transactions "
        "WHERE type='支出' AND substr(date, 1, 7)=? "
        "GROUP BY category",
        (year_month,)
    )
    rows = cursor.fetchall()

    # 查询当前月份所有类别预算
    cursor.execute(
        "SELECT category, amount FROM category_budget WHERE year_month=? AND user_id=?",
        (year_month, 1)
    )
    budget_map = dict(cursor.fetchall())
    conn.close()

    if rows:
        summary_data = []
        for cat, spent in rows:
            budget_amt = budget_map.get(cat, None)
            if budget_amt is not None:
                pct = min(spent / budget_amt * 100, 100) if budget_amt > 0 else 0
                budget_display = f"¥{budget_amt:.2f}"
                progress_display = f"{spent / budget_amt * 100:.0f}%" if budget_amt > 0 else "0%"
            else:
                budget_display = "未设置"
                progress_display = "-"
            summary_data.append({
                "类别": cat,
                "已花金额": f"¥{spent:.2f}",
                "预算": budget_display,
                "进度": progress_display
            })

        # 显示表格
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        # [修改] 使用 st.markdown 自定义 HTML 进度条，颜色区分超支
        for cat, spent in rows:
            budget_amt = budget_map.get(cat, None)
            if budget_amt is not None and budget_amt > 0:
                pct = spent / budget_amt
                display_pct = min(pct, 1.0) * 100
                if pct > 1.0:
                    color = "#ff4444"
                    label = "已超支"
                else:
                    color = "#4caf50"
                    label = f"{pct * 100:.0f}%"
                st.markdown(
                    f'<div style="margin-bottom:4px;">'
                    f'<span style="font-size:14px;display:inline-block;width:60px;">{cat}</span>'
                    f'<span style="display:inline-block;width:calc(100% - 130px);vertical-align:middle;">'
                    f'<div style="background:#e0e0e0;border-radius:10px;width:100%;height:20px;">'
                    f'<div style="background:{color};border-radius:10px;width:{display_pct}%;height:20px;"></div>'
                    f'</div></span>'
                    f'<span style="font-size:14px;display:inline-block;width:60px;text-align:right;color:{color};">{label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.text("本月暂无支出")

    st.markdown("---")

    # [修改] 交易记录（带筛选/搜索功能）
    st.markdown('<h2><i class="fa-solid fa-clock-rotate-left"></i> 交易记录</h2>', unsafe_allow_html=True)

    # 查询所有可选月份和类别（用于筛选下拉框）
    conn = sqlite3.connect("finance.db")
    all_records_df = pd.read_sql_query(
        "SELECT date, type, category, amount, description FROM transactions ORDER BY date DESC",
        conn
    )
    conn.close()

    if not all_records_df.empty:
        all_records_df.columns = ["日期", "类型", "类别", "金额（元）", "备注"]
        all_records_df["备注"] = all_records_df["备注"].fillna("-")

        # 筛选栏
        month_options = sorted(all_records_df["日期"].apply(lambda x: x[:7]).unique(), reverse=True)
        category_options = sorted(all_records_df["类别"].unique())

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            selected_month = st.selectbox("月份筛选", ["全部月份"] + month_options)
        with fc2:
            selected_category = st.selectbox("类别筛选", ["全部类别"] + category_options)
        with fc3:
            keyword = st.text_input("关键词搜索", placeholder="搜索备注或类别...")

        # 应用筛选
        filtered_df = all_records_df.copy()
        if selected_month != "全部月份":
            filtered_df = filtered_df[filtered_df["日期"].str.startswith(selected_month)]
        if selected_category != "全部类别":
            filtered_df = filtered_df[filtered_df["类别"] == selected_category]
        if keyword.strip():
            kw = keyword.strip().lower()
            filtered_df = filtered_df[
                filtered_df["类别"].str.lower().str.contains(kw) |
                filtered_df["备注"].str.lower().str.contains(kw)
            ]

        filtered_df["金额（元）"] = filtered_df["金额（元）"].apply(lambda x: f"¥{x:.2f}")

        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.text("没有找到符合条件的交易记录")
    else:
        st.text("暂无交易记录")


# ========== 页面：数据分析 ==========
elif page == "📊 数据分析":
    st.markdown('<h1><i class="fa-solid fa-chart-line"></i> 数据分析</h1>', unsafe_allow_html=True)
    st.caption("支出与收入趋势及结构分析")

    # 预计算过去6个月列表（两个标签页共用）
    months = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")

    tab1, tab2 = st.tabs(["支出分析", "收入分析"])

    # ===== Tab 1：支出分析 =====
    with tab1:
        # 月度支出趋势图
        st.markdown('<h2><i class="fa-solid fa-arrow-trend-up"></i> 过去6个月支出趋势</h2>', unsafe_allow_html=True)
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT substr(date, 1, 7) AS ym, SUM(amount) FROM transactions "
            "WHERE type='支出' AND substr(date, 1, 7) IN ({}) "
            "GROUP BY ym".format(",".join("?" * len(months))),
            months
        )
        exp_rows = dict(cursor.fetchall())
        conn.close()

        exp_trend = []
        has_exp = False
        for ym in months:
            val = exp_rows.get(ym, 0)
            exp_trend.append({"月份": ym, "支出总金额（元）": val})
            if val > 0:
                has_exp = True

        if has_exp:
            fig1 = px.line(pd.DataFrame(exp_trend), x="月份", y="支出总金额（元）", markers=True)
            fig1.update_traces(line=dict(width=2, color="#ff6b6b"), marker=dict(size=8, color="#ff6b6b"))
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("暂无支出数据，无法绘制趋势图")

        st.markdown("---")

        # 本月支出结构饼图
        st.markdown('<h2><i class="fa-solid fa-chart-pie"></i> 本月支出结构</h2>', unsafe_allow_html=True)
        conn = sqlite3.connect("finance.db")
        exp_pie = pd.read_sql_query(
            "SELECT category, SUM(amount) AS total FROM transactions "
            "WHERE type='支出' AND substr(date, 1, 7)=? "
            "GROUP BY category",
            conn,
            params=(year_month,)
        )
        conn.close()

        if not exp_pie.empty:
            fig2 = px.pie(exp_pie, names="category", values="total", title="本月支出结构", hole=0.3)
            fig2.update_traces(textinfo="label+percent")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("本月暂无支出，无法生成饼图")

    # ===== Tab 2：收入分析 =====
    with tab2:
        # 月度收入趋势图
        st.markdown('<h2><i class="fa-solid fa-arrow-trend-up"></i> 过去6个月收入趋势</h2>', unsafe_allow_html=True)
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT substr(date, 1, 7) AS ym, SUM(amount) FROM transactions "
            "WHERE type='收入' AND substr(date, 1, 7) IN ({}) "
            "GROUP BY ym".format(",".join("?" * len(months))),
            months
        )
        inc_rows = dict(cursor.fetchall())
        conn.close()

        inc_trend = []
        has_inc = False
        for ym in months:
            val = inc_rows.get(ym, 0)
            inc_trend.append({"月份": ym, "收入总金额（元）": val})
            if val > 0:
                has_inc = True

        if has_inc:
            fig3 = px.line(pd.DataFrame(inc_trend), x="月份", y="收入总金额（元）", markers=True)
            fig3.update_traces(line=dict(width=2, color="#4caf50"), marker=dict(size=8, color="#4caf50"))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("暂无收入数据，无法绘制趋势图")

        st.markdown("---")

        # 本月收入结构饼图
        st.markdown('<h2><i class="fa-solid fa-chart-pie"></i> 本月收入结构</h2>', unsafe_allow_html=True)
        conn = sqlite3.connect("finance.db")
        inc_pie = pd.read_sql_query(
            "SELECT category, SUM(amount) AS total FROM transactions "
            "WHERE type='收入' AND substr(date, 1, 7)=? "
            "GROUP BY category",
            conn,
            params=(year_month,)
        )
        conn.close()

        if not inc_pie.empty:
            fig4 = px.pie(inc_pie, names="category", values="total", title="本月收入结构", hole=0.3)
            fig4.update_traces(textinfo="label+percent")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("本月暂无收入，无法生成图表")

    # AI 省钱建议
    st.markdown("---")
    st.markdown('<h2><i class="fa-solid fa-robot"></i> AI 省钱建议</h2>', unsafe_allow_html=True)

    if st.button("AI 省钱建议", key="ai_advice"):
        # 查询最近30天的支出记录
        cutoff_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        conn = sqlite3.connect("finance.db")
        ai_df = pd.read_sql_query(
            "SELECT date, category, amount, description FROM transactions "
            "WHERE type='支出' AND date >= ? ORDER BY date DESC",
            conn,
            params=(cutoff_date,)
        )
        conn.close()

        if ai_df.empty:
            st.warning("最近30天没有支出记录，无法生成建议。")
        else:
            records_text = ""
            for _, row in ai_df.iterrows():
                desc = f" ({row['description']})" if row['description'] else ""
                records_text += f"{row['date']} | {row['category']} | ¥{row['amount']:.2f}{desc}\n"

            api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                st.error("未配置 DEEPSEEK_API_KEY，请在 Streamlit Cloud 的 Settings > Secrets 中添加，或本地创建 .streamlit/secrets.toml 文件。")
            else:
                with st.spinner("AI 正在分析您的支出习惯，请稍候…"):
                    try:
                        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": "你是一位专业的理财顾问。请根据用户的消费记录，给出3条具体、可操作的省钱建议。每条建议不超过30字。用编号1. 2. 3. 列出，每条之间换行分隔。"},
                                {"role": "user", "content": f"以下是我最近30天的支出记录：\n{records_text}\n请给我3条省钱建议。"}
                            ],
                            temperature=0.7,
                            max_tokens=300
                        )
                        suggestion = response.choices[0].message.content
                        st.success("AI 省钱建议如下：")
                        st.markdown(suggestion)
                    except Exception as e:
                        st.error(f"AI 调用失败：{e}")


# ========== 页面：月度报告 ==========
elif page == "📋 月度报告":
    st.markdown('<h1><i class="fa-solid fa-file-invoice"></i> 月度财务报告</h1>', unsafe_allow_html=True)
    st.caption("基于 AI 自动生成本月财务分析报告")

    st.markdown("---")

    if st.button("生成月度报告", key="gen_report"):
        # 查询本月所有支出记录
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        # 本月总支出
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='支出' AND substr(date, 1, 7)=?",
            (year_month,)
        )
        total_expense = cursor.fetchone()[0]

        # 按类别汇总
        cursor.execute(
            "SELECT category, SUM(amount) FROM transactions "
            "WHERE type='支出' AND substr(date, 1, 7)=? "
            "GROUP BY category ORDER BY SUM(amount) DESC",
            (year_month,)
        )
        cat_rows = cursor.fetchall()

        # 查询类别预算
        cursor.execute(
            "SELECT category, amount FROM category_budget WHERE year_month=? AND user_id=?",
            (year_month, 1)
        )
        budget_map = dict(cursor.fetchall())
        conn.close()

        if total_expense == 0:
            st.warning("本月暂无支出，无法生成报告")
        else:
            # 构建结构化数据文本
            data_text = f"本月总支出：¥{total_expense:.2f}\n\n"
            data_text += "按类别汇总：\n"
            for cat, amt in cat_rows:
                data_text += f"  - {cat}：¥{amt:.2f}"
                if cat in budget_map:
                    data_text += f"（预算 ¥{budget_map[cat]:.2f}"
                    diff = budget_map[cat] - amt
                    if diff < 0:
                        data_text += f"，超支 ¥{-diff:.2f}）\n"
                    else:
                        data_text += f"，剩余 ¥{diff:.2f}）\n"
                else:
                    data_text += "（未设置预算）\n"

            api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                st.error("未配置 DEEPSEEK_API_KEY，请在 Streamlit Cloud 的 Settings > Secrets 中添加，或本地创建 .streamlit/secrets.toml 文件。")
            else:
                with st.spinner("AI 正在生成月度财务报告，请稍候…"):
                    try:
                        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": "你是一位专业的财务分析师，擅长根据用户的消费数据生成简洁、实用的月度财务报告。请严格按照用户要求的 Markdown 格式输出。"},
                                {"role": "user", "content": f"""请根据以下数据生成本月财务报告：

{data_text}

请严格按照以下 Markdown 格式输出：

# 📊 本月财务报告（{year_month}）
## 一、总体概况
- 本月总支出：XXX元
- 支出最多的类别：XXX（XX元）
## 二、预算执行情况
- 超支类别：XXX（超支XX元），如果没有超支则写"本月无超支类别"
- 健康类别：XXX（预算剩余XX元），列出预算剩余最多的2个类别
## 三、改进建议
1. 第一条建议
2. 第二条建议
3. 第三条建议"""}
                            ],
                            temperature=0.7,
                            max_tokens=600
                        )
                        report = response.choices[0].message.content
                        st.success("报告已生成：")
                        st.markdown(report)
                    except Exception as e:
                        st.error(f"报告生成失败，请稍后重试。错误信息：{e}")


# ========== 页面：自定义快捷按钮 ==========
elif page == "⚙️ 自定义快捷按钮":
    st.markdown('<h1><i class="fa-solid fa-sliders"></i> 自定义快捷按钮</h1>', unsafe_allow_html=True)
    st.caption("在这里添加或删除首页的快捷录入按钮")

    st.markdown("---")

    # 显示当前所有按钮
    conn = sqlite3.connect("finance.db")
    mgmt_df = pd.read_sql_query(
        "SELECT id, name, category, amount, is_default FROM quick_buttons WHERE user_id=1 ORDER BY id",
        conn
    )
    conn.close()

    if not mgmt_df.empty:
        # 表格形式展示
        display_df = mgmt_df[["name", "category", "amount"]].copy()
        display_df.columns = ["名称", "类别", "金额"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown('<h2><i class="fa-solid fa-trash-can"></i> 删除按钮</h2>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (_, row) in enumerate(mgmt_df.iterrows()):
            btn_id = int(row["id"])
            if cols[i % 3].button(f"删除：{row['name']}", key=f"del_qbtn_{btn_id}"):
                conn = sqlite3.connect("finance.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM quick_buttons WHERE id=?", (btn_id,))
                conn.commit()
                conn.close()
                st.toast(f"已删除 {row['name']}", icon="🗑️")
    else:
        st.info("暂无快捷按钮")

    # 添加新按钮
    st.markdown("---")
    st.markdown('<h2><i class="fa-solid fa-circle-plus"></i> 添加新按钮</h2>', unsafe_allow_html=True)
    with st.form("add_quick_button"):
        new_name = st.text_input("按钮名称", placeholder="例如：午餐+30")
        new_category = st.selectbox(
            "类别",
            ["餐饮", "购物", "交通", "娱乐", "住宿", "医疗", "教育", "通讯", "人情", "其他"]
        )
        new_amount = st.number_input("金额（元）", min_value=0, step=1)
        add_submitted = st.form_submit_button("添加")

    if add_submitted:
        if new_name.strip():
            conn = sqlite3.connect("finance.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO quick_buttons (name, category, amount, is_default, user_id) VALUES (?, ?, ?, 0, 1)",
                (new_name, new_category, new_amount)
            )
            conn.commit()
            conn.close()
            st.success(f"已添加按钮：{new_name}")
        else:
            st.warning("请输入按钮名称")

    # [新增] 返回主页按钮
    st.markdown("---")
    if st.button("返回记账主页"):
        st.session_state["nav_page"] = "🏠 记账主页"
        st.rerun()

# ========== 页面：负债管理 ==========
elif page == "📉 负债管理":
    st.markdown('<h1><i class="fa-solid fa-hand-holding-dollar"></i> 负债管理</h1>', unsafe_allow_html=True)
    st.caption("记录借款与还款，清晰掌握负债状况")

    st.markdown("---")

    # ===== 区域1：记录借款 =====
    st.markdown('<h2><i class="fa-solid fa-file-invoice-dollar"></i> 记录借款</h2>', unsafe_allow_html=True)
    with st.form("add_debt_form"):
        debt_type = st.selectbox("负债类型", ["花呗", "信用卡", "房贷", "车贷", "亲友借款", "其他"])
        total_amount = st.number_input("借款金额（元）", min_value=0.01, step=1.0, format="%.2f")
        annual_rate = st.number_input("年化利率（%，可选）", min_value=0.0, step=0.01, format="%.2f", help="如 3.6 表示年化 3.6%")
        borrowed_date = st.date_input("借入日期", value=today)
        due_date = st.date_input("预计还款日期（可选）", value=None)
        debt_desc = st.text_input("备注（可选）", placeholder="例如：分期12个月")
        debt_submitted = st.form_submit_button("记录借款")

    if debt_submitted:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO debts (debt_type, total_amount, annual_rate, borrowed_date, due_date, description, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (debt_type, total_amount, annual_rate if annual_rate > 0 else None,
             borrowed_date.strftime("%Y-%m-%d"),
             due_date.strftime("%Y-%m-%d") if due_date else None,
             debt_desc, 1)
        )
        conn.commit()
        conn.close()
        st.success(f"✓ 已记录 {debt_type} 借款 ¥{total_amount:.2f}")

    st.markdown("---")

    # ===== 区域2：记录还款 =====
    st.markdown('<h2><i class="fa-solid fa-money-bill-wave"></i> 记录还款</h2>', unsafe_allow_html=True)

    # 查询进行中的负债列表
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT d.id, d.debt_type, d.total_amount, "
        "COALESCE(SUM(r.repayment_amount), 0) AS total_repaid "
        "FROM debts d "
        "LEFT JOIN debt_repayments r ON d.id = r.debt_id "
        "WHERE d.status = '进行中' "
        "GROUP BY d.id"
    )
    active_debts = cursor.fetchall()
    conn.close()

    if active_debts:
        debt_options = []
        debt_map = {}
        for debt_id, d_type, total, repaid in active_debts:
            remaining = total - repaid
            label = f"[{d_type}] 剩余未还: ¥{remaining:.2f}"
            debt_options.append(label)
            debt_map[label] = debt_id
        selected_debt_label = st.selectbox("选择要还款的负债", debt_options)
        selected_debt_id = debt_map[selected_debt_label]

        with st.form("add_repayment_form"):
            repayment_amount = st.number_input("还款金额（元）", min_value=0.01, step=1.0, format="%.2f")
            repayment_date = st.date_input("还款日期", value=today)
            repayment_desc = st.text_input("备注（可选）", placeholder="例如：第3期还款")
            repayment_submitted = st.form_submit_button("记录还款")

        if repayment_submitted:
            conn = sqlite3.connect("finance.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO debt_repayments (debt_id, repayment_amount, repayment_date, description, user_id) VALUES (?, ?, ?, ?, ?)",
                (selected_debt_id, repayment_amount, repayment_date.strftime("%Y-%m-%d"), repayment_desc, 1)
            )
            # 检查是否已还清
            cursor.execute(
                "SELECT d.total_amount, COALESCE(SUM(r.repayment_amount), 0) "
                "FROM debts d LEFT JOIN debt_repayments r ON d.id = r.debt_id "
                "WHERE d.id = ? GROUP BY d.id",
                (selected_debt_id,)
            )
            total, repaid = cursor.fetchone()
            if repaid >= total:
                cursor.execute("UPDATE debts SET status='已结清' WHERE id=?", (selected_debt_id,))
            conn.commit()
            conn.close()
            st.success(f"✓ 已记录还款 ¥{repayment_amount:.2f}")
            st.rerun()
    else:
        st.info("暂无进行中的负债，请先记录借款")

    st.markdown("---")

    # ===== 区域3：负债总览 =====
    st.markdown('<h2><i class="fa-solid fa-chart-simple"></i> 负债总览</h2>', unsafe_allow_html=True)

    conn = sqlite3.connect("finance.db")
    all_debts = pd.read_sql_query(
        "SELECT d.id, d.debt_type, d.total_amount, d.annual_rate, d.borrowed_date, d.due_date, d.status, "
        "COALESCE(SUM(r.repayment_amount), 0) AS total_repaid "
        "FROM debts d "
        "LEFT JOIN debt_repayments r ON d.id = r.debt_id "
        "GROUP BY d.id "
        "ORDER BY d.status ASC, d.borrowed_date DESC",
        conn
    )
    conn.close()

    if not all_debts.empty:
        # 统计卡片
        all_debts["remaining"] = all_debts["total_amount"] - all_debts["total_repaid"]
        active_mask = all_debts["status"] == "进行中"
        total_remaining = all_debts.loc[active_mask, "remaining"].sum()
        active_count = active_mask.sum()
        closed_count = (all_debts["status"] == "已结清").sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("总负债余额", f"¥{total_remaining:.2f}")
        m2.metric("进行中负债笔数", str(active_count))
        m3.metric("已结清负债笔数", str(closed_count))

        st.markdown("---")

        # 详细表格
        display_debts = all_debts.copy()
        display_debts.columns = ["ID", "类型", "借款总额", "年化利率(%)", "借入日期", "预计还款日", "状态", "已还总额", "剩余未还"]
        display_debts["年化利率(%)"] = display_debts["年化利率(%)"].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
        )
        display_debts["借款总额"] = display_debts["借款总额"].apply(lambda x: f"¥{x:.2f}")
        display_debts["已还总额"] = display_debts["已还总额"].apply(lambda x: f"¥{x:.2f}")
        display_debts["剩余未还"] = display_debts["剩余未还"].apply(lambda x: f"¥{x:.2f}")
        display_debts["预计还款日"] = display_debts["预计还款日"].fillna("-")
        display_debts = display_debts.rename(columns={"剩余未还": "剩余未还"})
        table_cols = ["ID", "类型", "借款总额", "年化利率(%)", "已还总额", "剩余未还", "借入日期", "预计还款日", "状态"]
        st.dataframe(display_debts[table_cols], use_container_width=True, hide_index=True)
    else:
        st.info("暂无负债数据")
