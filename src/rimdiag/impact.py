"""Investigation priority from retained evidence, never automatic causal attribution."""
import re
from pydantic import BaseModel, ConfigDict, Field


class ImpactReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    symptom: str = Field(min_length=1, max_length=400)
    blocked_stage: str = Field(pattern=r"^(startup|game_creation|world_creation|map_creation|save_load|runtime)$")
    related_group_ids: list[str] = Field(min_length=1, max_length=8)
    outcome_after_workaround: str | None = Field(default=None, min_length=1, max_length=400)


def signals(headline: str, evidence: str) -> tuple[int, str, str]:
    if re.search(r"ReadingPolicyDatabase\.(?:GenerateStartingPolicies|\.ctor)", evidence) and re.search(r"(?:NullReferenceException|ArgumentNullException)", evidence):
        return 100, "required_initialization_failure", "Retained stack reaches reading-policy construction; investigate the invalid data and mandatory game-creation path even if it occurred only once."
    if re.search(r"\bGame\.\.ctor|\bGame\.InitNewGame|WorldGenerator\.GenerateWorld|WorldComponentUtility\.FinalizeInit", evidence) and re.search(r"Exception|returning null|Could not generate", headline):
        return 95, "creation_path_failure", "Retained exception reaches game/world/map initialization. Entry in the stack is a consumer/trigger clue, not culprit proof."
    if re.search(r"has null thingClass|has components but it's thingClass is not a ThingWithComps", headline):
        return 90, "structurally_invalid_definition", "A null/invalid runtime class can break any unguarded consumer, including unrelated mandatory initialization. Do not downgrade furniture/data errors to cosmetic issues."
    if re.search(r"Too many tries|Could not generate a pawn after|returning null", headline):
        return 90, "generation_retry_failure", "Explicit retries or null output affect generation and do extra work; measured TPS cost is unknown."
    if re.search(r"TypeInitializationException|HarmonyException|InvalidProgramException|Error while instantiating", evidence):
        return 80, "initialization_or_patch_failure", "A single initialization/patch failure can leave features unavailable for the whole session."
    if re.search(r"Could not find (?:a )?(?:type|class)|Exception loading def", headline):
        return 80, "missing_runtime_implementation", "Missing implementation is a structural compatibility risk; locate affected Defs without guessing Mod ownership."
    if re.search(r"Exception ticking|Error.*Tick|Exception.*OnGUI", headline, re.I):
        return 80, "runtime_exception", "Potential recurring runtime path; verify repetition and profile cost."
    if re.search(r"NullReferenceException|Patch operation.*failed|Config error", headline):
        return 60, "functional_candidate", "Inspect the actual effect and call path; frequency alone is not severity."
    return 20, "unclassified_impact", "No stronger impact rule matched; absence of a signal is not evidence that this is harmless."


def prioritize(diagnostics, run_id: str, report: ImpactReport | None = None, count: int = 5) -> dict:
    from .core import DiagnosticError, limit
    from .parsing import identity_text
    limit(count, 10)
    snapshot = diagnostics.summary(run_id)
    with diagnostics.db(run_id) as db:
        # Bounded by existing scan limits; inspect every retained occurrence, not just each headline's first sample.
        ranked = {}
        scanned = 0
        occurrences = {}
        for row in db.execute("SELECT fingerprint,id,line,end_line,headline,evidence,truncated FROM events ORDER BY id"):
            scanned += 1
            occurrence = occurrences.get(row['fingerprint'], 0)
            occurrences[row['fingerprint']] = occurrence + 1
            evidence = '\n'.join(line for line in identity_text(row['evidence']).splitlines() if not re.search(r'\bLikely cause:', line, re.I))
            score, label, reason = signals(identity_text(row['headline']), evidence)
            old = ranked.get(row['fingerprint'])
            if old is None or score > old['score']:
                ranked[row['fingerprint']] = {'group_id': row['fingerprint'], 'occurrence': occurrence,
                    'lines': [row['line'], row['end_line']], 'headline': row['headline'][:240], 'score': score,
                    'impact_signal': label, 'log_impact_signal': label, 'log_score': score, 'reason': reason, 'source': 'retained_log_heuristic', 'causality': 'unconfirmed',
                    'truncated': bool(row['truncated'])}
        if report:
            for group in report.related_group_ids:
                if not re.fullmatch(r'[a-f0-9]{24}', group) or group not in ranked:
                    raise DiagnosticError('impact_report_references_unknown_group')
                ranked[group] = ranked[group] | {'score': 110, 'impact_signal': 'user_reported_blocker',
                    'reason': report.symptom, 'source': 'caller_supplied_user_report_not_independently_verified',
                    'blocked_stage': report.blocked_stage}
        selected = sorted(ranked.values(), key=lambda x: (-x['score'], x['lines'][0], x['group_id']))[:count]
        # Related structural data is shown as a lead, never inferred as the cause of a particular exception.
        invalid = [r for r in ranked.values() if r['log_impact_signal'] == 'structurally_invalid_definition'][:5]
    return {'run_id': run_id, 'impact_rules_version': 1, 'investigation_priorities': selected, 'structural_data_leads': invalid,
            'occurrences_inspected': scanned, 'selection': 'impact rules then first occurrence; never frequency alone',
            'observed_report': report.model_dump() if report else None,
            'report_independently_verified': False, 'causal_chain_established': False,
            'functional_status': 'not_tested', 'workaround_means_data_repaired': False,
            'snapshot_incomplete': snapshot['incomplete'],
            'decoding_replacement_lines': snapshot['decoding_replacement_lines'],
            'truncated_event_count': snapshot['truncated_event_count'],
            'limits': 'Retained log evidence and caller-reported impact only; no source inspection or execution. A guard may change the current blocker without repairing upstream data.'}
