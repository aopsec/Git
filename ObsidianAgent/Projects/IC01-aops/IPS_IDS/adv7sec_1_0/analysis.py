"""Real-time event analysis and safe auto-response decisions."""

from __future__ import annotations

from adv7sec_1_0.models import AnalysisReport, AutoResponseDecision, ThreatEvent

_PATH_KEYWORDS = ("found", "infected", "trojan", "ransom", "malware")
_PID_KEYWORDS = ("reverse shell", "crypto", "miner", "wget", "curl", "chmod +s")


def _decision_for_event(event: ThreatEvent, execute: bool) -> AutoResponseDecision | None:
    summary = event.summary.lower()
    if event.path and any(keyword in summary for keyword in _PATH_KEYWORDS):
        return AutoResponseDecision(
            event_source=event.source,
            event_summary=event.summary,
            action="quarantine-path",
            target=event.path,
            confidence=95,
            reason="Arquivo associado a sinal forte de malware ou infeccao.",
            execute=execute,
        )
    if event.pid is not None and any(keyword in summary for keyword in _PID_KEYWORDS):
        return AutoResponseDecision(
            event_source=event.source,
            event_summary=event.summary,
            action="kill-pid",
            target=str(event.pid),
            confidence=82,
            reason="Processo associado a padrao de execucao hostil conhecido.",
            execute=execute,
        )
    return None


def analyze_events(events: list[ThreatEvent], execute: bool = False) -> AnalysisReport:
    """[FIX-LIVE-PIPELINE] Rank events and derive safe automatic responses."""
    responses: list[AutoResponseDecision] = []
    elevated_events = 0
    signals: list[str] = []
    for event in events:
        if event.severity in {"high", "critical"}:
            elevated_events += 1
        decision = _decision_for_event(event, execute)
        if decision is not None:
            responses.append(decision)
    if not events:
        signals.append("Nenhum evento recente encontrado nas fontes monitoradas.")
    elif elevated_events == 0:
        signals.append("Telemetria recente sem eventos high/critical.")
    else:
        signals.append(f"{elevated_events} eventos elevados detectados na amostra atual.")
    if not responses:
        signals.append("Nenhuma resposta automatica segura foi selecionada.")
    else:
        signals.append(f"{len(responses)} respostas seguras prontas para preview/execucao.")
    return AnalysisReport(
        total_events=len(events),
        elevated_events=elevated_events,
        signals=signals,
        events=events,
        responses=responses,
    )
