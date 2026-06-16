import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
from openai import OpenAI

st.set_page_config(page_title="个人理财储蓄助手 · 极简记账本", layout="wide")

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

conn.commit()
conn.close()

today = date.today()
year_month = today.strftime("%Y-%m")

# ---------- 侧边栏：页面导航 ----------
st.sidebar.markdown("---")
page = st.sidebar.radio("导航", ["🏠 记账主页", "📊 数据分析"])

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

st.sidebar.subheader("📊 月度预算")
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
st.sidebar.markdown("### 💡 预算执行")
if budget_row:
    budget_amount = budget_row[0]
    remaining = budget_amount - monthly_expense
    st.sidebar.metric("本月预算", f"¥{budget_amount:.2f}")
    st.sidebar.metric("实际支出", f"¥{monthly_expense:.2f}")
    st.sidebar.metric("剩余", f"¥{remaining:.2f}")
    if monthly_expense > budget_amount:
        st.sidebar.error(f"⚠️ 已超支 ¥{monthly_expense - budget_amount:.2f} 元")
else:
    st.sidebar.info("未设置本月预算")

# [新增] 侧边栏：类别预算管理
st.sidebar.markdown("---")
st.sidebar.subheader("📊 类别预算管理")

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
if st.sidebar.button("💾 保存类别预算"):
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
    st.title("📒 我的记账本")
    st.caption("第一步：数据库已准备就绪，下一步将添加记账表单。")

    # 记账表单
    st.markdown("---")
    st.subheader("📝 记账表单")
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
        st.success("记账成功！")

    st.markdown("---")

    # 当前总余额
    st.subheader("💰 当前总余额")
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

    # 本月支出按类别汇总
    st.subheader("📂 本月支出分类汇总")
    cursor.execute(
        "SELECT category, SUM(amount) FROM transactions "
        "WHERE type='支出' AND substr(date, 1, 7)=? "
        "GROUP BY category",
        (year_month,)
    )
    rows = cursor.fetchall()
    conn.close()

    if rows:
        df = pd.DataFrame(rows, columns=["类别", "金额（元）"])
        df["金额（元）"] = df["金额（元）"].map(lambda x: f"¥{x:.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.text("本月暂无支出")

    st.markdown("---")

    # [修改] 查询和展示增加备注列
    st.subheader("🕒 最近10条交易记录")
    conn = sqlite3.connect("finance.db")
    recent_df = pd.read_sql_query(
        "SELECT date, type, category, amount, description FROM transactions ORDER BY date DESC LIMIT 10",
        conn
    )
    conn.close()

    if not recent_df.empty:
        recent_df.columns = ["日期", "类型", "类别", "金额（元）", "备注"]
        recent_df["备注"] = recent_df["备注"].fillna("-")
        recent_df["金额（元）"] = recent_df["金额（元）"].map(lambda x: f"¥{x:.2f}")
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.text("暂无交易记录")


# ========== 页面：数据分析 ==========
elif page == "📊 数据分析":
    st.title("📈 月度支出趋势")
    st.caption("过去6个月的支出变化趋势")

    st.markdown("---")

    # 月度支出趋势图
    months = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")

    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT substr(date, 1, 7) AS ym, SUM(amount) FROM transactions "
        "WHERE type='支出' AND substr(date, 1, 7) IN ({}) "
        "GROUP BY ym".format(",".join("?" * len(months))),
        months
    )
    db_rows = dict(cursor.fetchall())
    conn.close()

    trend_data = []
    has_any_expense = False
    for ym in months:
        val = db_rows.get(ym, 0)
        trend_data.append({"月份": ym, "支出总金额（元）": val})
        if val > 0:
            has_any_expense = True

    if has_any_expense:
        trend_df = pd.DataFrame(trend_data)
        fig = px.line(trend_df, x="月份", y="支出总金额（元）", markers=True)
        fig.update_traces(line=dict(width=2), marker=dict(size=8))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无支出数据，无法绘制趋势图")

    # 本月支出结构饼图
    st.markdown("---")
    st.subheader("🍩 本月支出结构")
    conn = sqlite3.connect("finance.db")
    pie_df = pd.read_sql_query(
        "SELECT category, SUM(amount) AS total FROM transactions "
        "WHERE type='支出' AND substr(date, 1, 7)=? "
        "GROUP BY category",
        conn,
        params=(year_month,)
    )
    conn.close()

    if not pie_df.empty:
        pie_fig = px.pie(pie_df, names="category", values="total", title="本月支出结构", hole=0.3)
        pie_fig.update_traces(textinfo="label+percent")
        st.plotly_chart(pie_fig, use_container_width=True)
    else:
        st.info("本月暂无支出，无法生成饼图")

    # AI 省钱建议
    st.markdown("---")
    st.subheader("🤖 AI 省钱建议")

    if st.button("🤖 获取 AI 省钱建议"):
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
