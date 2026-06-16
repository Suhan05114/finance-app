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

conn.commit()
conn.close()

today = date.today()
year_month = today.strftime("%Y-%m")

# ---------- 侧边栏：页面导航 ----------
st.sidebar.markdown("---")
# 用 session_state 管理页面切换，支持从快捷录入区域跳转到管理页
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "🏠 记账主页"
page = st.sidebar.radio(
    "导航",
    ["🏠 记账主页", "📊 数据分析", "📋 月度报告", "⚙️ 管理快捷按钮"],
    index=["🏠 记账主页", "📊 数据分析", "📋 月度报告", "⚙️ 管理快捷按钮"].index(st.session_state["nav_page"])
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

    # [新增] 快捷录入（从数据库读取按钮）
    st.markdown("---")
    st.subheader("⚡ 快捷录入")

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
        st.info("暂无快捷按钮，请去管理页面添加")

    # [新增] 跳转到管理页的按钮
    if st.button("📝 管理", key="goto_mgmt"):
        st.session_state["nav_page"] = "⚙️ 管理快捷按钮"
        st.rerun()

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

    # [修改] 本月支出按类别汇总（增加预算和进度列）
    st.subheader("📂 本月支出分类汇总")
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


# ========== 页面：月度报告 ==========
elif page == "📋 月度报告":
    st.title("📋 月度财务报告")
    st.caption("基于 AI 自动生成本月财务分析报告")

    st.markdown("---")

    if st.button("📊 生成月度报告"):
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


# ========== 页面：管理快捷按钮 ==========
elif page == "⚙️ 管理快捷按钮":
    st.title("⚙️ 管理快捷按钮")
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
        st.subheader("🗑️ 删除按钮")
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
    st.subheader("➕ 添加新按钮")
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
    if st.button("🏠 返回记账主页"):
        st.session_state["nav_page"] = "🏠 记账主页"
        st.rerun()
