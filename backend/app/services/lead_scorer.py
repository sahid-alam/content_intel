_BUDGET_PTS: dict[str, float] = {"explicit": 4.0, "mentioned": 1.5, "none": 0.0}
_URGENCY_PTS: dict[str, float] = {"explicit": 4.0, "mentioned": 1.5, "none": 0.0}


def score_lead(budget_signal: str, urgency_signal: str, pain_signals: list, source: str) -> float:
    pts = _BUDGET_PTS.get(budget_signal, 0.0)
    pts += _URGENCY_PTS.get(urgency_signal, 0.0)
    if pain_signals:
        pts += 1.0
    return min(round(pts, 1), 10.0)
