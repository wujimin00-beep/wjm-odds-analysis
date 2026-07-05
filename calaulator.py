def settle_single_handicap(goal_diff, line, stake, odds):
    """
    goal_diff: 你买的球队净胜球
    line: 盘口，例如 -2, -1.75, -0.5, 0.25
    stake: 本金
    odds: 亚洲盘净盈利赔率，例如 1.0 表示赢得 1 倍本金

    返回：盈利，不包含本金
    """

    result = goal_diff + line

    if result > 0:
        return stake * odds
    elif result == 0:
        return 0
    else:
        return -stake


def settle_asian_handicap(goal_diff, line, stake, odds):
    """
    支持 -2, -1.75, -1.5, -1.25, -1, -0.75, -0.5, -0.25, 0 等盘口
    """

    # 整数盘 / 半球盘
    if line * 4 % 2 == 0:
        return settle_single_handicap(goal_diff, line, stake, odds)

    # 四分之一盘，例如 -1.75 = 一半 -1.5，一半 -2
    lower = line - 0.25
    upper = line + 0.25

    return (
        settle_single_handicap(goal_diff, lower, stake / 2, odds)
        + settle_single_handicap(goal_diff, upper, stake / 2, odds)
    )

def settle_correct_score(actual_home, actual_away, pick_home, pick_away, stake, odds):
    """
    actual_home, actual_away: 实际比分
    pick_home, pick_away: 你买的波胆比分
    stake: 本金
    odds: 十进制赔率

    返回：盈利，不包含本金
    """

    if actual_home == pick_home and actual_away == pick_away:
        return stake * (odds - 1)
    else:
        return -stake


# 新增：合计盈利函数
def calculate_total_profit(actual_home, actual_away, bets):
    """
    actual_home, actual_away: 假设的实际比分
    bets: 注单列表，每一条注单是一个 dict

    支持两种注单：
    1. 亚洲让球：
       {
           "type": "asian_handicap",
           "team": "home" 或 "away",
           "line": -1.75,
           "stake": 100,
           "odds": 1.0
       }

    2. 波胆：
       {
           "type": "correct_score",
           "pick_home": 2,
           "pick_away": 1,
           "stake": 100,
           "odds": 8.5
       }

    返回：该比分下所有注单的合计盈利，不包含本金
    """

    total_profit = 0

    for bet in bets:
        if bet["type"] == "asian_handicap":
            if bet["team"] == "home":
                goal_diff = actual_home - actual_away
            elif bet["team"] == "away":
                goal_diff = actual_away - actual_home
            else:
                raise ValueError("team 必须是 'home' 或 'away'")

            profit = settle_asian_handicap(
                goal_diff=goal_diff,
                line=bet["line"],
                stake=bet["stake"],
                odds=bet["odds"]
            )

        elif bet["type"] == "correct_score":
            profit = settle_correct_score(
                actual_home=actual_home,
                actual_away=actual_away,
                pick_home=bet["pick_home"],
                pick_away=bet["pick_away"],
                stake=bet["stake"],
                odds=bet["odds"]
            )

        else:
            raise ValueError(f"不支持的注单类型: {bet['type']}")

        total_profit += profit

    return total_profit


# 新增：比分网格推演
def simulate_score_grid(bets, max_home_score=5, max_away_score=5):
    """
    自动推演 0-0 到 max_home_score-max_away_score 的所有比分。

    返回：列表，每一项包含主队进球、客队进球、比分、合计盈亏
    """

    results = []

    for home_score in range(max_home_score + 1):
        for away_score in range(max_away_score + 1):
            total_profit = calculate_total_profit(
                actual_home=home_score,
                actual_away=away_score,
                bets=bets
            )

            results.append({
                "home_score": home_score,
                "away_score": away_score,
                "score": f"{home_score}-{away_score}",
                "total_profit": total_profit
            })

    return results


if __name__ == "__main__":
    sample_bets = [
        {
            "type": "asian_handicap",
            "team": "home",
            "line": -1.75,
            "stake": 100,
            "odds": 1.0
        },
        {
            "type": "correct_score",
            "pick_home": 2,
            "pick_away": 0,
            "stake": 50,
            "odds": 7.5
        }
    ]

    score_grid = simulate_score_grid(sample_bets, max_home_score=4, max_away_score=4)

    for row in score_grid:
        print(row)
