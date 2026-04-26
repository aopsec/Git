"""Token-pressure alert helpers for control-mesh sessions."""
from __future__ import annotations

from adv7ia_control.models import SessionRecord


def evaluate_session_alerts(
    session: SessionRecord,
    warning_ratio: float,
    freeze_ratio: float,
    compact_ratio: float,
) -> list[str]:
    """Report token pressure for one session using the configured policy."""
    warning_floor = int(session.context_window * warning_ratio)
    freeze_floor = int(session.context_window * freeze_ratio)
    compact_floor = int(session.context_window * compact_ratio)
    if session.prompt_tokens >= compact_floor:
        return [
            f"session `{session.session_id}` reached {render_ratio(compact_ratio)} token usage "
            "and should compact now."
        ]
    if session.prompt_tokens >= freeze_floor:
        return [
            f"session `{session.session_id}` reached {render_ratio(freeze_ratio)} token usage "
            "and should stop opening new branches."
        ]
    if session.prompt_tokens >= warning_floor:
        return [
            f"session `{session.session_id}` crossed the "
            f"{render_ratio(warning_ratio)} token warning threshold."
        ]
    return []


def render_ratio(ratio: float) -> str:
    """Render one ratio as a rounded percentage string."""
    return f"{ratio:.0%}"
