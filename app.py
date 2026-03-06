"""Travel Expense Tracker - Streamlit Application."""

import io

import pandas as pd
import streamlit as st

import ai_client
import db
from config import AI_PROVIDERS, DEFAULT_CATEGORIES

# --- Initialize ---
db.init_db()

st.set_page_config(page_title="旅行経費トラッカー", page_icon="", layout="wide")

st.markdown("""
<style>
    /* Prevent horizontal scroll on dataframes */
    [data-testid="stDataFrame"] > div { overflow-x: hidden !important; }
    /* Wider metric value */
    [data-testid="stMetricValue"] { font-size: 2rem; }
</style>
""", unsafe_allow_html=True)


# --- Session state defaults ---
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None
if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = "claude"


# --- Sidebar ---
with st.sidebar:
    st.title("旅行経費トラッカー")

    # AI provider selection
    provider_names = {k: v["name"] for k, v in AI_PROVIDERS.items()}
    selected_provider = st.selectbox(
        "AI プロバイダー",
        options=list(provider_names.keys()),
        format_func=lambda x: provider_names[x],
        index=list(provider_names.keys()).index(st.session_state.ai_provider),
    )
    st.session_state.ai_provider = selected_provider

    st.divider()

    # New thread button
    if st.button("+ 新しい旅行", use_container_width=True):
        new_id = db.create_thread()
        st.session_state.current_thread_id = new_id
        st.rerun()

    # Thread list
    threads = db.list_threads()
    if threads:
        st.subheader("旅行一覧")
        for t in threads:
            total = f"¥{t['total_amount']:,}" if t["total_amount"] else "¥0"
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    f"{t['name']}  ({total})",
                    key=f"thread_{t['id']}",
                    use_container_width=True,
                ):
                    st.session_state.current_thread_id = t["id"]
                    st.rerun()
            with col2:
                if st.button("×", key=f"del_{t['id']}"):
                    db.delete_thread(t["id"])
                    if st.session_state.current_thread_id == t["id"]:
                        st.session_state.current_thread_id = None
                    st.rerun()


# --- Main area ---
if st.session_state.current_thread_id is None:
    st.header("旅行経費トラッカーへようこそ")
    st.write("左のサイドバーから「新しい旅行」を作成するか、既存の旅行を選択してください。")
    st.write("")
    st.write("**使い方:**")
    st.write("- チャットで経費を入力すると、AIが自動的に費目を分類して記録します")
    st.write('- 例: 「新幹線 14000円」「ホテル2泊で30000円」「ランチ 1200円」')
    st.write('- 「集計して」と入力すると、現在の経費をまとめて表示します')
    st.write('- 「#edit 新幹線 12000円」のように #edit を付けると既存データを編集できます')
    st.stop()

# Get current thread
thread = db.get_thread(st.session_state.current_thread_id)
if thread is None:
    st.session_state.current_thread_id = None
    st.rerun()

# Thread header with rename
col_title, col_rename = st.columns([3, 1])
with col_title:
    st.header(thread["name"])
    st.caption(f"作成日: {thread['created_at']}")
with col_rename:
    with st.popover("名前変更"):
        new_name = st.text_input("新しい名前", value=thread["name"], key="rename_input")
        if st.button("変更", key="rename_btn"):
            db.rename_thread(thread["id"], new_name)
            st.rerun()

# --- Two-column layout: Chat (left) + Summary (right) ---
expenses = db.get_expenses(thread["id"])
messages = db.get_messages(thread["id"])

col_chat, col_summary = st.columns([1, 1])

# --- Left: Chat ---
with col_chat:
    st.subheader("チャット")
    chat_container = st.container(height=520)
    with chat_container:
        if not messages:
            st.caption("経費を入力してください（例: 新幹線 14000円）")
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# --- Right: Summary ---
with col_summary:
    if expenses:
        total = sum(e["amount"] for e in expenses)
        st.metric("合計金額", f"¥{total:,}")

        # Sort control
        sort_options = {"日付 昇順": ("expense_date", True), "日付 降順": ("expense_date", False), "金額 昇順": ("amount", True), "金額 降順": ("amount", False)}
        sort_label = st.selectbox("並び替え", list(sort_options.keys()), index=0, key="sort_select")
        sort_col, sort_asc = sort_options[sort_label]

        # Expense table
        summary_container = st.container(height=200)
        with summary_container:
            df = pd.DataFrame(expenses)
            df["expense_date"] = df["expense_date"].fillna("")
            df = df.sort_values(sort_col, ascending=sort_asc, na_position="last")
            df_display = df[["expense_date", "description", "amount", "category"]].copy()
            df_display.columns = ["日付", "項目", "金額", "カテゴリ"]
            df_display["金額"] = df_display["金額"].apply(lambda x: f"¥{x:,}")
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Category summary
        summary = db.get_expenses_summary(thread["id"])
        df_summary = pd.DataFrame(summary)
        df_summary.columns = ["カテゴリ", "件数", "合計"]
        df_summary["合計"] = df_summary["合計"].apply(lambda x: f"¥{x:,}")
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        # CSV download + delete in expander
        with st.expander("データ出力・経費削除"):
            df_export = pd.DataFrame(expenses)
            df_export = df_export[["expense_date", "description", "amount", "category", "created_at"]]
            df_export.columns = ["日付", "項目", "金額", "カテゴリ", "記録日時"]

            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()

            st.download_button(
                label="CSV ダウンロード",
                data=csv_data,
                file_name=f"{thread['name']}_expenses.csv",
                mime="text/csv",
            )

            st.divider()
            for exp in expenses:
                col1, col2 = st.columns([4, 1])
                with col1:
                    date_label = f" [{exp['expense_date']}]" if exp.get("expense_date") else ""
                    st.caption(f"{exp['description']}: ¥{exp['amount']:,}{date_label}")
                with col2:
                    if st.button("×", key=f"del_exp_{exp['id']}"):
                        db.delete_expense(exp["id"])
                        st.rerun()
    else:
        st.info("まだ経費がありません")

# --- Chat input (full width, below columns) ---
if prompt := st.chat_input("経費を入力してください（例: 新幹線 14000円）"):
    db.add_message(thread["id"], "user", prompt)

    # Build conversation for AI
    context_parts = []
    if expenses:
        context_parts.append("【現在の経費一覧】")
        exp_total = 0
        for exp in expenses:
            date_str = f" [{exp['expense_date']}]" if exp.get('expense_date') else ""
            context_parts.append(f"- {exp['description']}: ¥{exp['amount']:,} ({exp['category']}){date_str}")
            exp_total += exp["amount"]
        context_parts.append(f"合計: ¥{exp_total:,}")
        context_parts.append("")

    MAX_HISTORY = 10  # 直近N往復(20メッセージ)のみAIに送信
    recent_messages = messages[-(MAX_HISTORY * 2):]

    ai_messages = []
    for msg in recent_messages:
        ai_messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = prompt
    if context_parts:
        user_content = "\n".join(context_parts) + "\n\n" + prompt

    ai_messages.append({"role": "user", "content": user_content})

    try:
        response = ai_client.chat(ai_messages, st.session_state.ai_provider)

        # Extract and process edits or new expenses
        edits = ai_client.extract_edits(response)
        new_expenses = ai_client.extract_expenses(response)

        edited_items = []
        for edit in edits:
            existing = db.find_expense_by_description(thread["id"], edit["original_description"])
            if existing:
                db.update_expense(existing["id"], edit["description"], edit["amount"], edit["category"], edit.get("date"))
                edited_items.append(edit)

        for exp in new_expenses:
            db.add_expense(
                thread["id"],
                exp["description"],
                exp["amount"],
                exp["category"],
                exp.get("date"),
            )

        # Build display text
        display_text = ai_client.remove_json_blocks(response)
        if edited_items:
            display_text += "\n\n**編集しました:**\n"
            for edit in edited_items:
                display_text += f"- {edit['description']}: ¥{edit['amount']:,} ({edit['category']})\n"
        if new_expenses:
            display_text += "\n\n**記録しました:**\n"
            for exp in new_expenses:
                display_text += f"- {exp['description']}: ¥{exp['amount']:,} ({exp['category']})\n"

        db.add_message(thread["id"], "assistant", display_text)

    except Exception as e:
        db.add_message(thread["id"], "assistant", f"エラーが発生しました: {str(e)}")

    st.rerun()
