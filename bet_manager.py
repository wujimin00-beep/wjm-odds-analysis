

"""
Bet manager for the odds analysis app.

This file only manages bet states:
- pre_match_draft_bets: 赛前试算注单
- confirmed_bets: 已确认买入注单
- live_draft_bets: 滚球试算注单

It does not calculate profit and does not display UI.
"""


def initialize_bet_state(session_state):
    """Initialize all bet lists in Streamlit session state."""

    if "pre_match_draft_bets" not in session_state:
        session_state.pre_match_draft_bets = []

    if "confirmed_bets" not in session_state:
        session_state.confirmed_bets = []

    if "live_draft_bets" not in session_state:
        session_state.live_draft_bets = []


# ---------- Draft bet creation ----------

def create_asian_handicap_bet(
    team="home",
    line=0.0,
    stake=0.0,
    odds=1.90,
    phase="pre_match",
    buy_home_score=None,
    buy_away_score=None,
):
    """Create an Asian handicap bet dictionary."""

    bet = {
        "type": "asian_handicap",
        "team": team,
        "line": line,
        "stake": stake,
        "odds": odds,
        "phase": phase,
    }

    if phase == "live":
        bet["buy_home_score"] = buy_home_score
        bet["buy_away_score"] = buy_away_score

    return bet


def create_correct_score_bet(
    pick_home=0,
    pick_away=0,
    stake=0.0,
    odds=1.90,
    phase="pre_match",
    buy_home_score=None,
    buy_away_score=None,
):
    """Create a correct score bet dictionary."""

    bet = {
        "type": "correct_score",
        "pick_home": pick_home,
        "pick_away": pick_away,
        "stake": stake,
        "odds": odds,
        "phase": phase,
    }

    if phase == "live":
        bet["buy_home_score"] = buy_home_score
        bet["buy_away_score"] = buy_away_score

    return bet


# ---------- Add draft bets ----------

def add_pre_match_asian_handicap(session_state):
    """Add one default pre-match Asian handicap bet to the draft list."""

    session_state.pre_match_draft_bets.append(
        create_asian_handicap_bet(phase="pre_match")
    )


def add_pre_match_correct_score(session_state):
    """Add one default pre-match correct score bet to the draft list."""

    session_state.pre_match_draft_bets.append(
        create_correct_score_bet(phase="pre_match")
    )


def add_live_asian_handicap(session_state, buy_home_score, buy_away_score):
    """Add one default live Asian handicap bet to the live draft list."""

    session_state.live_draft_bets.append(
        create_asian_handicap_bet(
            phase="live",
            buy_home_score=buy_home_score,
            buy_away_score=buy_away_score,
        )
    )


def add_live_correct_score(session_state, buy_home_score, buy_away_score):
    """Add one default live correct score bet to the live draft list."""

    session_state.live_draft_bets.append(
        create_correct_score_bet(
            phase="live",
            buy_home_score=buy_home_score,
            buy_away_score=buy_away_score,
        )
    )


# ---------- Confirm / clear bets ----------

def confirm_pre_match_bets(session_state):
    """Move all pre-match draft bets into confirmed bets."""

    session_state.confirmed_bets.extend(session_state.pre_match_draft_bets)
    session_state.pre_match_draft_bets = []


def confirm_live_bets(session_state):
    """Move all live draft bets into confirmed bets."""

    session_state.confirmed_bets.extend(session_state.live_draft_bets)
    session_state.live_draft_bets = []


def clear_pre_match_draft_bets(session_state):
    """Clear only pre-match draft bets."""

    session_state.pre_match_draft_bets = []


def clear_live_draft_bets(session_state):
    """Clear only live draft bets."""

    session_state.live_draft_bets = []


def clear_confirmed_bets(session_state):
    """Clear confirmed bets."""

    session_state.confirmed_bets = []


# ---------- Combined views ----------

def get_all_active_bets(session_state):
    """
    Return all bets that should participate in the current simulation.

    This includes:
    - confirmed bets
    - pre-match draft bets
    - live draft bets
    """

    return (
        session_state.confirmed_bets
        + session_state.pre_match_draft_bets
        + session_state.live_draft_bets
    )


def get_confirmed_bets(session_state):
    """Return confirmed bets only."""

    return session_state.confirmed_bets


def has_any_active_bets(session_state):
    """Return True if there is at least one bet to simulate."""

    return len(get_all_active_bets(session_state)) > 0