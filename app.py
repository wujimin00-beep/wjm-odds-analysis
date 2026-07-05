import copy
import re
from typing import Any

import pandas as pd
import streamlit as st

from bet_manager import (
    clear_confirmed_bets,
    clear_live_draft_bets,
    clear_pre_match_draft_bets,
    confirm_live_bets,
    confirm_pre_match_bets,
    get_all_active_bets,
    initialize_bet_state,
)
from calaulator import simulate_score_grid


# ============================================================
# Page setup
# ============================================================

st.set_page_config(
    page_title="赔率分析",
    page_icon="⚽",
    layout="wide",
)

st.title("赔率分析")
st.caption("足球投注盈亏模拟系统")

initialize_bet_state(st.session_state)

if "strategy_slots" not in st.session_state:
    st.session_state.strategy_slots = {
        "方案一": [],
        "方案二": [],
        "方案三": [],
        "方案四": [],
        "方案五": [],
    }

if "workspace_add_mode" not in st.session_state:
    st.session_state.workspace_add_mode = None

if "show_saved_pre_match_strategies" not in st.session_state:
    st.session_state.show_saved_pre_match_strategies = False


# ============================================================
# Basic helpers
# ============================================================

def get_workspace_phase() -> str:
    """Return current workspace phase."""

    return "live" if st.session_state.confirmed_bets else "pre_match"


def get_workspace_list_key() -> str:
    """Return current workspace session-state key."""

    return "live_draft_bets" if get_workspace_phase() == "live" else "pre_match_draft_bets"


def get_workspace_bets() -> list[dict[str, Any]]:
    """Return current workspace bets."""

    return st.session_state[get_workspace_list_key()]


def phase_to_display(phase: str) -> str:
    return {"pre_match": "赛前", "live": "滚球"}.get(phase, phase)


def display_to_phase(phase_display: str) -> str:
    return {"赛前": "pre_match", "滚球": "live"}.get(phase_display, phase_display)


def type_to_display(bet_type: str) -> str:
    return {"asian_handicap": "亚洲让球", "correct_score": "波胆"}.get(bet_type, bet_type)


def display_to_type(type_display: str) -> str:
    return {"亚洲让球": "asian_handicap", "波胆": "correct_score"}.get(type_display, type_display)


def team_to_display(team: str) -> str:
    return {"home": "主队", "away": "客队"}.get(team, team)


def display_to_team(team_display: str) -> str:
    return {"主队": "home", "客队": "away"}.get(team_display, team_display)


def format_score(home: Any, away: Any) -> str:
    if home is None or away is None or pd.isna(home) or pd.isna(away):
        return ""
    return f"{int(home)} : {int(away)}"


def safe_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        st.error(f"{field_name} 必须输入数字。")
        st.stop()


def safe_int(value: Any, field_name: str) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        st.error(f"{field_name} 必须输入整数。")
        st.stop()


def get_remaining_strategy_slots() -> int:
    """Return how many empty strategy slots remain."""

    return sum(1 for bets in st.session_state.strategy_slots.values() if not bets)


def reset_strategy_slots() -> None:
    """Clear all saved strategy slots."""

    st.session_state.strategy_slots = {
        "方案一": [],
        "方案二": [],
        "方案三": [],
        "方案四": [],
        "方案五": [],
    }


def save_current_strategy(active_bets: list[dict[str, Any]]) -> None:
    """Save current active bets into the next available strategy slot."""

    if not active_bets:
        st.warning("当前没有可保存的注单。")
        return

    for strategy_name, strategy_bets in st.session_state.strategy_slots.items():
        if not strategy_bets:
            st.session_state.strategy_slots[strategy_name] = copy.deepcopy(active_bets)
            st.rerun()

    st.warning("方案保存次数已用完。请先清空方案对比。")


# ============================================================
# Bet display and parsing
# ============================================================

def bet_to_content(bet: dict[str, Any]) -> str:
    """Convert a bet into the compact content column."""

    if bet.get("type") == "asian_handicap":
        return f"{team_to_display(bet.get('team'))} {bet.get('line')}"

    if bet.get("type") == "correct_score":
        return format_score(bet.get("pick_home"), bet.get("pick_away"))

    return ""


def parse_asian_content(content: Any) -> tuple[str, float]:
    """Parse content like '主队 -1.5' or '客队 +0.5'."""

    content_text = str(content).strip()

    team = "away" if "客" in content_text else "home"

    match = re.search(r"[+-]?\d+(?:\.\d+)?", content_text)
    if not match:
        st.error("亚洲让球内容格式错误，请输入类似：主队 -1.5 或 客队 +0.5")
        st.stop()

    return team, float(match.group())


def parse_correct_score_content(content: Any) -> tuple[int, int]:
    """Parse content like '2 : 1' or '2:1'."""

    content_text = str(content).replace("：", ":").strip()
    parts = [part.strip() for part in content_text.split(":")]

    if len(parts) != 2:
        st.error("波胆内容格式错误，请输入类似：2 : 1")
        st.stop()

    return safe_int(parts[0], "预测主队进球"), safe_int(parts[1], "预测客队进球")


def bets_to_summary_df(bets: list[dict[str, Any]]) -> pd.DataFrame:
    """Create a compact display table from bet dictionaries."""

    rows = []

    for bet in bets:
        rows.append({
            "阶段": phase_to_display(bet.get("phase")),
            "玩法": type_to_display(bet.get("type")),
            "内容": bet_to_content(bet),
            "赔率": bet.get("odds"),
            "下注金额": bet.get("stake"),
        })

    return pd.DataFrame(rows)


def summary_df_to_bets(edited_df: pd.DataFrame, original_bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert an edited summary table back into backend bet dictionaries."""

    updated_bets = []

    for row_index, row in edited_df.iterrows():
        original_bet = original_bets[row_index] if row_index < len(original_bets) else {}

        bet_type = display_to_type(row.get("玩法"))
        phase = display_to_phase(row.get("阶段"))

        bet = {
            "type": bet_type,
            "phase": phase,
            "odds": safe_float(row.get("赔率"), "赔率"),
            "stake": safe_float(row.get("下注金额"), "下注金额"),
        }

        if bet_type == "asian_handicap":
            team, line = parse_asian_content(row.get("内容"))
            bet["team"] = team
            bet["line"] = line

        elif bet_type == "correct_score":
            pick_home, pick_away = parse_correct_score_content(row.get("内容"))
            bet["pick_home"] = pick_home
            bet["pick_away"] = pick_away

        if phase == "live":
            bet["buy_home_score"] = original_bet.get("buy_home_score")
            bet["buy_away_score"] = original_bet.get("buy_away_score")

        updated_bets.append(bet)

    return updated_bets


# ============================================================
# Shared UI components
# ============================================================

def render_bet_table(
    title: str,
    bets: list[dict[str, Any]],
    *,
    editable: bool = False,
    key: str | None = None,
) -> list[dict[str, Any]]:
    """Render a bet table. Editable mode is used for current draft bets only."""

    st.subheader(title)

    if not bets:
        st.info("暂无注单。")
        return bets

    df = bets_to_summary_df(bets)

    if not editable:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return bets

    table_key = key or "editable_bet_table"
    revision_key = f"{table_key}_revision"
    revision = st.session_state.get(revision_key, 0)
    widget_prefix = f"{table_key}_{revision}"
    column_widths = [1.0, 1.2, 2.2, 1.2, 1.4, 0.7]
    header_columns = st.columns(column_widths)
    for column, label in zip(header_columns, ["阶段", "玩法", "内容", "赔率", "下注金额", "操作"]):
        column.markdown(f"**{label}**")

    updated_rows = []
    for row_index, row in df.iterrows():
        row_columns = st.columns(column_widths, vertical_alignment="center")
        row_columns[0].write(row["阶段"])
        row_columns[1].write(row["玩法"])

        content = row_columns[2].text_input(
            "内容",
            value=str(row["内容"]),
            key=f"{widget_prefix}_content_{row_index}",
            label_visibility="collapsed",
            help="亚洲让球示例：主队 -1.5；波胆示例：2 : 1",
        )
        odds = row_columns[3].number_input(
            "赔率",
            min_value=1.0,
            value=float(row["赔率"]),
            step=0.01,
            format="%.2f",
            key=f"{widget_prefix}_odds_{row_index}",
            label_visibility="collapsed",
        )
        stake = row_columns[4].number_input(
            "下注金额",
            min_value=0.0,
            value=float(row["下注金额"]),
            step=10.0,
            format="%.2f",
            key=f"{widget_prefix}_stake_{row_index}",
            label_visibility="collapsed",
        )

        if row_columns[5].button(
            "删除",
            key=f"{widget_prefix}_delete_{row_index}",
            type="secondary",
            use_container_width=True,
        ):
            current_df = df.copy()
            for index in range(len(current_df)):
                current_df.at[index, "内容"] = st.session_state.get(
                    f"{widget_prefix}_content_{index}", current_df.at[index, "内容"]
                )
                current_df.at[index, "赔率"] = st.session_state.get(
                    f"{widget_prefix}_odds_{index}", current_df.at[index, "赔率"]
                )
                current_df.at[index, "下注金额"] = st.session_state.get(
                    f"{widget_prefix}_stake_{index}", current_df.at[index, "下注金额"]
                )
            bets[:] = summary_df_to_bets(current_df, bets)
            bets.pop(row_index)
            st.session_state[revision_key] = revision + 1
            st.rerun()

        updated_row = row.copy()
        updated_row["内容"] = content
        updated_row["赔率"] = odds
        updated_row["下注金额"] = stake
        updated_rows.append(updated_row)

    edited_df = pd.DataFrame(updated_rows, columns=df.columns)
    return summary_df_to_bets(edited_df, bets)


# ============================================================
# Quick add forms
# ============================================================

def render_asian_handicap_form(
    phase: str,
    target_list_key: str,
    buy_home_score: int | None = None,
    buy_away_score: int | None = None,
) -> None:
    st.subheader("添加亚洲让球")

    with st.form(f"asian_handicap_form_{phase}"):
        col1, col2, col3, col4, col5 = st.columns([1.2, 1, 1, 1, 1])

        with col1:
            team_display = st.segmented_control(
                "球队",
                options=["主队", "客队"],
                default="主队",
                selection_mode="single",
            )

        with col2:
            line_input = st.text_input("盘口", placeholder="-0.75")

        with col3:
            odds_input = st.text_input("赔率", placeholder="1.90")

        with col4:
            stake_input = st.text_input("下注金额", placeholder="100")

        with col5:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("添加")

        st.caption("输入后可以按 Tab 跳到下一个字段，最后按 Enter 或点击添加。")

    if not submitted:
        return

    bet = {
        "type": "asian_handicap",
        "team": display_to_team(team_display),
        "line": safe_float(line_input, "盘口"),
        "odds": safe_float(odds_input, "赔率"),
        "stake": safe_float(stake_input, "下注金额"),
        "phase": phase,
    }

    if phase == "live":
        bet["buy_home_score"] = buy_home_score
        bet["buy_away_score"] = buy_away_score

    st.session_state[target_list_key].append(bet)
    st.session_state.workspace_add_mode = None
    st.rerun()


def render_correct_score_form(
    phase: str,
    target_list_key: str,
    buy_home_score: int | None = None,
    buy_away_score: int | None = None,
) -> None:
    st.subheader("批量添加波胆")
    st.caption("可以连续输入多条波胆。按 Tab 进入下一格，继续填写下一行；最后按 Enter 或点击按钮完成添加。")

    with st.form(f"correct_score_form_{phase}"):
        correct_score_rows = []

        for row_index in range(5):
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

            with col1:
                pick_home_input = st.text_input(
                    "预测主队进球" if row_index == 0 else " ",
                    placeholder="2" if row_index == 0 else "",
                    key=f"cs_home_{phase}_{row_index}",
                )

            with col2:
                pick_away_input = st.text_input(
                    "预测客队进球" if row_index == 0 else " ",
                    placeholder="1" if row_index == 0 else "",
                    key=f"cs_away_{phase}_{row_index}",
                )

            with col3:
                odds_input = st.text_input(
                    "赔率" if row_index == 0 else " ",
                    placeholder="8.50" if row_index == 0 else "",
                    key=f"cs_odds_{phase}_{row_index}",
                )

            with col4:
                stake_input = st.text_input(
                    "下注金额" if row_index == 0 else " ",
                    placeholder="100" if row_index == 0 else "",
                    key=f"cs_stake_{phase}_{row_index}",
                )

            correct_score_rows.append({
                "pick_home": pick_home_input,
                "pick_away": pick_away_input,
                "odds": odds_input,
                "stake": stake_input,
            })

        submitted = st.form_submit_button("完成添加波胆")

    if not submitted:
        return

    added_count = 0

    for row in correct_score_rows:
        values = [row["pick_home"], row["pick_away"], row["odds"], row["stake"]]

        if all(value.strip() == "" for value in values):
            continue

        if any(value.strip() == "" for value in values):
            st.error("每一条波胆都必须完整填写：预测主队进球、预测客队进球、赔率、下注金额。")
            st.stop()

        bet = {
            "type": "correct_score",
            "pick_home": safe_int(row["pick_home"], "预测主队进球"),
            "pick_away": safe_int(row["pick_away"], "预测客队进球"),
            "odds": safe_float(row["odds"], "赔率"),
            "stake": safe_float(row["stake"], "下注金额"),
            "phase": phase,
        }

        if phase == "live":
            bet["buy_home_score"] = buy_home_score
            bet["buy_away_score"] = buy_away_score

        st.session_state[target_list_key].append(bet)
        added_count += 1

    if added_count == 0:
        st.error("请至少填写一条波胆。")
        st.stop()

    st.session_state.workspace_add_mode = None
    st.rerun()


# ============================================================
# Workspace and confirmed bets
# ============================================================

def render_saved_pre_match_strategies() -> None:
    """Show saved pre-match strategies and allow loading one for editing."""

    saved_strategies = {
        name: [copy.deepcopy(bet) for bet in bets if bet.get("phase") == "pre_match"]
        for name, bets in st.session_state.strategy_slots.items()
        if bets
    }
    saved_strategies = {name: bets for name, bets in saved_strategies.items() if bets}

    if not saved_strategies:
        st.info("暂无可载入的赛前购买方案。")
        return

    st.caption("载入方案会替换当前赛前工作区中的试算注单，载入后可继续修改并确认买入。")

    for strategy_index, (strategy_name, strategy_bets) in enumerate(saved_strategies.items()):
        total_stake = sum(bet.get("stake", 0) for bet in strategy_bets)
        with st.expander(
            f"{strategy_name} · {len(strategy_bets)} 笔 · ¥{total_stake:.2f}",
            expanded=strategy_index == 0,
        ):
            st.dataframe(
                bets_to_summary_df(strategy_bets),
                use_container_width=True,
                hide_index=True,
            )
            if st.button(
                "载入并编辑",
                key=f"load_pre_match_strategy_{strategy_name}",
                type="primary",
            ):
                st.session_state.pre_match_draft_bets = copy.deepcopy(strategy_bets)
                revision_key = "workspace_table_pre_match_revision"
                st.session_state[revision_key] = st.session_state.get(revision_key, 0) + 1
                st.session_state.workspace_add_mode = None
                st.session_state.show_saved_pre_match_strategies = False
                st.rerun()


def render_workspace() -> None:
    st.header("① 当前工作区")

    phase = get_workspace_phase()
    target_list_key = get_workspace_list_key()
    workspace_bets = get_workspace_bets()

    live_home_score = None
    live_away_score = None

    if phase == "pre_match":
        st.caption("赛前阶段：先完成赛前试算并确认买入。确认后，系统会进入滚球工作区。")
        st.subheader("赛前工作区")
        saved_button_label = (
            "收起已保存方案"
            if st.session_state.show_saved_pre_match_strategies
            else "查看已保存方案"
        )
        if st.button(saved_button_label, key="toggle_saved_pre_match_strategies"):
            st.session_state.show_saved_pre_match_strategies = (
                not st.session_state.show_saved_pre_match_strategies
            )
            st.rerun()

        if st.session_state.show_saved_pre_match_strategies:
            render_saved_pre_match_strategies()
    else:
        st.caption("滚球阶段：赛前下注已经确认，现在可以在已买入基础上试算滚球加注。")
        st.subheader("滚球工作区")

        score_col1, score_col2 = st.columns(2)
        with score_col1:
            live_home_score = st.number_input("滚球买入时主队比分", min_value=0, value=0, step=1)
        with score_col2:
            live_away_score = st.number_input("滚球买入时客队比分", min_value=0, value=0, step=1)

    action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)

    with action_col1:
        if st.button("添加亚洲让球", key=f"add_ah_{phase}"):
            st.session_state.workspace_add_mode = "asian_handicap"
            st.rerun()

    with action_col2:
        if st.button("添加波胆", key=f"add_cs_{phase}"):
            st.session_state.workspace_add_mode = "correct_score"
            st.rerun()

    with action_col3:
        confirm_label = "确认赛前买入" if phase == "pre_match" else "确认滚球买入"
        if st.button(confirm_label, key=f"confirm_{phase}"):
            if phase == "pre_match":
                confirm_pre_match_bets(st.session_state)
            else:
                confirm_live_bets(st.session_state)
            st.session_state.workspace_add_mode = None
            st.rerun()

    with action_col4:
        clear_label = "清空赛前工作区" if phase == "pre_match" else "清空滚球工作区"
        if st.button(clear_label, key=f"clear_{phase}"):
            if phase == "pre_match":
                clear_pre_match_draft_bets(st.session_state)
            else:
                clear_live_draft_bets(st.session_state)
            st.session_state.workspace_add_mode = None
            st.rerun()

    with action_col5:
        remaining_slots = get_remaining_strategy_slots()
        if st.button(f"保存方案（{remaining_slots}）", key=f"save_strategy_workspace_{phase}"):
            save_current_strategy(get_all_active_bets(st.session_state))

    if st.session_state.workspace_add_mode == "asian_handicap":
        render_asian_handicap_form(
            phase=phase,
            target_list_key=target_list_key,
            buy_home_score=live_home_score,
            buy_away_score=live_away_score,
        )
    elif st.session_state.workspace_add_mode == "correct_score":
        render_correct_score_form(
            phase=phase,
            target_list_key=target_list_key,
            buy_home_score=live_home_score,
            buy_away_score=live_away_score,
        )

    if st.session_state.workspace_add_mode is not None:
        if st.button("取消添加", key=f"cancel_add_{phase}"):
            st.session_state.workspace_add_mode = None
            st.rerun()

    st.session_state[target_list_key] = render_bet_table(
        "当前试算注单",
        workspace_bets,
        editable=True,
        key=f"workspace_table_{phase}",
    )


def render_confirmed_bets() -> None:
    st.header("③ 已确认下注")

    confirmed_total_stake = sum(bet.get("stake", 0) for bet in st.session_state.confirmed_bets)
    confirmed_count = len(st.session_state.confirmed_bets)

    col1, col2 = st.columns(2)
    col1.metric("已确认注单数量", f"{confirmed_count} 笔")
    col2.metric("已确认下注金额", f"¥{confirmed_total_stake:.2f}")

    render_bet_table("已确认买入注单", st.session_state.confirmed_bets, editable=False)

    if st.session_state.confirmed_bets:
        if st.button("清除已确认注单", key="clear_confirmed"):
            clear_confirmed_bets(st.session_state)
            clear_live_draft_bets(st.session_state)
            st.session_state.workspace_add_mode = None
            st.rerun()


# ============================================================
# Strategy comparison
# ============================================================

def render_strategy_compare() -> None:
    st.header("② 方案对比")
    st.caption("将当前模拟中的注单保存为不同方案，最多对比五种买法。")

    remaining_slots = get_remaining_strategy_slots()
    st.caption(f"剩余可保存方案次数：{remaining_slots}")

    clear_col1, clear_col2 = st.columns([1, 4])

    with clear_col1:
        if st.button("清空方案对比", key="clear_strategy_slots"):
            reset_strategy_slots()
            st.rerun()

    saved_strategies = {
        name: bets
        for name, bets in st.session_state.strategy_slots.items()
        if bets
    }

    if not saved_strategies:
        st.info("暂无已保存方案。请先在上方完成一组试算，然后保存方案。")
        return

    saved_bets = [bet for bets in saved_strategies.values() for bet in bets]
    max_home_score = max(
        [4] + [bet.get("pick_home", 0) for bet in saved_bets if bet.get("type") == "correct_score"]
    )
    max_away_score = max(
        [4] + [bet.get("pick_away", 0) for bet in saved_bets if bet.get("type") == "correct_score"]
    )

    strategy_summary_rows = []
    comparison_df = None

    for strategy_name, strategy_bets in saved_strategies.items():
        strategy_grid = simulate_score_grid(
            bets=strategy_bets,
            max_home_score=max_home_score,
            max_away_score=max_away_score,
        )
        strategy_df = pd.DataFrame(strategy_grid)

        strategy_profit_df = strategy_df[["score", "total_profit"]].rename(
            columns={"total_profit": strategy_name}
        )

        if comparison_df is None:
            comparison_df = strategy_profit_df
        else:
            comparison_df = comparison_df.merge(strategy_profit_df, on="score", how="outer")

        strategy_summary_rows.append({
            "方案": strategy_name,
            "注单数量": len(strategy_bets),
            "总下注金额": sum(bet.get("stake", 0) for bet in strategy_bets),
            "最大盈利": strategy_df["total_profit"].max(),
            "最大亏损": strategy_df["total_profit"].min(),
            "盈利比分数量": int((strategy_df["total_profit"] > 0).sum()),
            "亏损比分数量": int((strategy_df["total_profit"] < 0).sum()),
        })

    st.subheader("方案统计")
    summary_df = pd.DataFrame(strategy_summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    strategy_count = len(saved_strategies)
    chart_height = min(520, 320 + strategy_count * 40)

    chart_data = comparison_df.set_index("score")
    st.line_chart(chart_data, height=chart_height)


# ============================================================
# Main page
# ============================================================

render_workspace()
render_strategy_compare()
render_confirmed_bets()
