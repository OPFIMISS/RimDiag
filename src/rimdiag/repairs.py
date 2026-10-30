"""Declarative repair proposals. No code execution, source access or safety approval."""
from __future__ import annotations

import hashlib
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .core import Diagnostics, DiagnosticError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LogAnchor(StrictModel):
    group_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    occurrence: int = Field(default=0, ge=0, lt=100000)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=400)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_line < self.start_line:
            raise ValueError("end_line precedes start_line")
        return self


class ExternalReference(StrictModel):
    kind: Literal["vanilla_source", "offline_check", "real_reference_compile", "in_game", "user_report"]
    description: str = Field(min_length=1, max_length=600)
    locator: str = Field(min_length=1, max_length=400)
    game_version: str = Field(min_length=1, max_length=80)
    assembly_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class ChainStep(StrictModel):
    role: Literal["trigger", "fault_origin", "consumer", "blocker"]
    statement: str = Field(min_length=1, max_length=600)
    status: Literal["log_observation", "external_claim", "hypothesis"]
    logs: list[LogAnchor] = Field(default_factory=list, max_length=4)
    external: list[ExternalReference] = Field(default_factory=list, max_length=3)


class Intervention(StrictModel):
    target_symbol: str = Field(min_length=1, max_length=240)
    scope: Literal["single_vanilla_call_site", "single_vanilla_method", "other"]
    rationale: str = Field(min_length=1, max_length=1000)
    normal_behavior_preserved: str = Field(min_length=1, max_length=1000)
    structure_mismatch_behavior: str = Field(min_length=1, max_length=600)
    invalid_data_diagnostics: str = Field(min_length=1, max_length=600)
    unresolved_problems: list[str] = Field(min_length=1, max_length=8)


class ValidationClaim(StrictModel):
    check: Literal["normal_input_equivalence", "invalid_input_behavior", "single_target_match",
                   "structure_mismatch_refusal", "runtime_outcome"]
    level: Literal["offline", "real_reference_compile", "in_game"]
    result: Literal["not_run", "passed", "failed", "inconclusive"]
    provenance: Literal["agent_report", "user_report", "author_report"]
    evidence: str | None = Field(default=None, min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_reference(self):
        if self.result != "not_run" and not self.evidence:
            raise ValueError("reported check results need an evidence reference")
        if self.check == "runtime_outcome" and self.level != "in_game":
            raise ValueError("runtime_outcome must use the in_game level")
        return self


class RepairPlan(StrictModel):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=160)
    applicable_game_version: str = Field(min_length=1, max_length=80)
    failure_chain: list[ChainStep] = Field(min_length=2, max_length=12)
    intervention: Intervention
    new_patch_source: str | None = Field(default=None, min_length=1, max_length=8000,
        description="Newly authored patch text only; inert data, never executed. No unauthorized Mod implementation.")
    validation: list[ValidationClaim] = Field(default_factory=list, max_length=12)
    backup: str = Field(min_length=1, max_length=1000)
    rollback: str = Field(min_length=1, max_length=1000)
    stop_conditions: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def budget(self):
        if len(self.model_dump_json().encode("utf-8")) > 24576:
            raise ValueError("repair plan exceeds 24 KiB")
        if sum(len(s.logs) for s in self.failure_chain) > 24:
            raise ValueError("at most 24 log anchors")
        for value in self.intervention.unresolved_problems + self.stop_conditions:
            if not value.strip() or len(value) > 600:
                raise ValueError("list entries must have 1..600 characters")
        return self


def review_repair_plan(diagnostics: Diagnostics, run_id: str, plan: RepairPlan) -> dict:
    gaps, anchors = [], []
    snapshot = diagnostics.summary(run_id)
    roles = {s.role for s in plan.failure_chain}
    for role in ("fault_origin", "consumer", "blocker"):
        if role not in roles:
            gaps.append("missing_chain_role:" + role)
    cache = {}
    for index, step in enumerate(plan.failure_chain):
        if step.status == "log_observation" and not step.logs:
            gaps.append(f"step_{index}:log_observation_has_no_anchor")
        if step.status == "external_claim" and not step.external:
            gaps.append(f"step_{index}:external_claim_has_no_reference")
        if step.status == "hypothesis":
            gaps.append(f"step_{index}:causal_hypothesis_needs_verification")
        for anchor in step.logs:
            key = (anchor.group_id, anchor.occurrence)
            try:
                if key not in cache:
                    cache[key] = diagnostics.evidence(run_id, *key)
                event = cache[key]
                first, last = event["lines"]
                lines = event["text"].splitlines()
                retained_last = first + len(lines) - 1
                bounds = first <= anchor.start_line <= anchor.end_line <= min(last, retained_last)
                excerpt = "\n".join(lines[anchor.start_line - first:anchor.end_line - first + 1]) if bounds else ""
                matched = bounds and anchor.quote in excerpt
                anchors.append({"step": index, "group_id": anchor.group_id, "occurrence": anchor.occurrence,
                                "quote_matches_retained_lines": matched, "event_truncated": event["truncated"]})
                if not matched:
                    gaps.append(f"step_{index}:quote_or_line_range_not_retained")
            except DiagnosticError:
                anchors.append({"step": index, "group_id": anchor.group_id, "quote_matches_retained_lines": False})
                gaps.append(f"step_{index}:unknown_log_evidence")
    vanilla = [r for s in plan.failure_chain for r in s.external if r.kind == "vanilla_source"]
    if not vanilla:
        gaps.append("missing_versioned_vanilla_source_reference")
    if any(r.game_version != plan.applicable_game_version for s in plan.failure_chain for r in s.external):
        gaps.append("declared_reference_version_mismatch")
    if any(not r.assembly_sha256 for r in vanilla):
        gaps.append("vanilla_reference_missing_assembly_fingerprint")
    if not plan.new_patch_source:
        gaps.append("new_patch_source_not_supplied")
    required = {"normal_input_equivalence", "invalid_input_behavior", "single_target_match", "structure_mismatch_refusal"}
    for check in sorted(required):
        checks = [c for c in plan.validation if c.check == check and c.level == "offline"]
        if not checks or any(c.result != "passed" for c in checks):
            gaps.append("offline_check_not_reported_passed:" + check)
    if not any(c.level == "real_reference_compile" and c.result == "passed" for c in plan.validation):
        gaps.append("real_reference_compile_not_reported_passed")
    if not any(c.check == "runtime_outcome" and c.level == "in_game" and c.result == "passed" for c in plan.validation):
        gaps.append("in_game_outcome_not_reported_passed")
    if any(c.result in ("failed", "inconclusive") for c in plan.validation):
        gaps.append("failed_or_inconclusive_validation_claims_remain")
    if snapshot["incomplete"] or snapshot["input_changed_during_scan"] or snapshot["multiple_sections"]:
        gaps.append("snapshot_completeness_or_session_scope_needs_review")
    return {"review_status": "needs_evidence" if gaps else "outline_complete_needs_human_review",
            "run_id": run_id, "title": plan.title, "gaps": sorted(set(gaps)), "log_anchors": anchors,
            "validation_claim_counts": {level: sum(c.level == level for c in plan.validation)
                                         for level in ("offline", "real_reference_compile", "in_game")},
            "external_references_verified": False, "validation_claims_independently_verified": False,
            "causal_claims_verified": False, "patch_safety_verified": False, "patch_executed": False,
            "patch_source_sha256": hashlib.sha256(plan.new_patch_source.encode()).hexdigest() if plan.new_patch_source else None,
            "remaining_problems": len(plan.intervention.unresolved_problems),
            "meaning": "Only local quote anchors and outline requirements checked. Caller-reported source/tests/user outcomes are not independently verified. This is not patch approval or functional acceptance."}
