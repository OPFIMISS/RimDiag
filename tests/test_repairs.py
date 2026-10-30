import tempfile
import unittest
from pathlib import Path
from pydantic import ValidationError
from rimdiag.core import Diagnostics
from rimdiag.repairs import RepairPlan, review_repair_plan


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        log = root / 'Player.log'
        log.write_text('ERROR Config error in ExampleFurniture: has null thingClass.\n')
        self.d = Diagnostics(root / 'store', [log])
        self.run = self.d.analyze()['run_id']
        group = self.d.list_errors(self.run)['groups'][0]['fingerprint']
        self.plan = {
            'title': 'Illustrative local guard', 'applicable_game_version': '1.7.fixture',
            'failure_chain': [
                {'role': 'fault_origin', 'statement': 'A null thingClass is logged.', 'status': 'log_observation',
                 'logs': [{'group_id': group, 'start_line': 1, 'end_line': 1, 'quote': 'has null thingClass.'}]},
                {'role': 'consumer', 'statement': 'Caller reports a vanilla consumer dereferences it.', 'status': 'external_claim',
                 'external': [{'kind': 'vanilla_source', 'description': 'Caller-reported fixture inspection', 'locator': 'fixture only',
                               'game_version': '1.7.fixture', 'assembly_sha256': 'a' * 64}]},
                {'role': 'blocker', 'statement': 'Caller reports startup blocked.', 'status': 'external_claim',
                 'external': [{'kind': 'user_report', 'description': 'Fixture, not actual gameplay', 'locator': 'test fixture', 'game_version': '1.7.fixture'}]}],
            'intervention': {'target_symbol': 'Illustrative.VanillaConsumer', 'scope': 'single_vanilla_call_site',
                'rationale': 'Only isolate the null input at the consumer.', 'normal_behavior_preserved': 'Non-null input retains the original predicate.',
                'structure_mismatch_behavior': 'Refuse when the unique anchor is absent.',
                'invalid_data_diagnostics': 'Report the bad Def and observed identity without guessing.',
                'unresolved_problems': ['Original data remains broken.']},
            'new_patch_source': '// newly authored fixture text only, never executable here',
            'validation': [{'check': c, 'level': 'offline', 'result': 'passed', 'provenance': 'author_report', 'evidence': 'fixture claim'}
                           for c in ('normal_input_equivalence', 'invalid_input_behavior', 'single_target_match', 'structure_mismatch_refusal')] + [
                {'check': 'single_target_match', 'level': 'real_reference_compile', 'result': 'passed', 'provenance': 'author_report', 'evidence': 'fixture claim'},
                {'check': 'runtime_outcome', 'level': 'in_game', 'result': 'passed', 'provenance': 'user_report', 'evidence': 'fixture claim'}],
            'backup': 'Separate new patch; retain original files and profile snapshot.',
            'rollback': 'Remove only the owned patch from a disposable profile.',
            'stop_conditions': ['New blocker: stop and inspect a new log.']}

    def review(self):
        return review_repair_plan(self.d, self.run, RepairPlan.model_validate(self.plan))

    def test_complete_outline_is_never_safety_approval(self):
        r = self.review()
        self.assertEqual(r['review_status'], 'outline_complete_needs_human_review')
        for field in ('patch_executed', 'causal_claims_verified', 'patch_safety_verified', 'validation_claims_independently_verified', 'external_references_verified'):
            self.assertFalse(r[field])
        self.assertTrue(r['log_anchors'][0]['quote_matches_retained_lines'])

    def test_fabricated_quote_does_not_validate(self):
        self.plan['failure_chain'][0]['logs'][0]['quote'] = 'invented fault'
        self.assertIn('step_0:quote_or_line_range_not_retained', self.review()['gaps'])

    def test_wrong_line_does_not_validate(self):
        self.plan['failure_chain'][0]['logs'][0].update(start_line=2, end_line=2)
        self.assertFalse(self.review()['log_anchors'][0]['quote_matches_retained_lines'])

    def test_unknown_group_reports_gap(self):
        self.plan['failure_chain'][0]['logs'][0]['group_id'] = '0' * 24
        self.assertIn('step_0:unknown_log_evidence', self.review()['gaps'])

    def test_hypothesis_stays_unverified(self):
        self.plan['failure_chain'][1]['status'] = 'hypothesis'
        self.assertIn('step_1:causal_hypothesis_needs_verification', self.review()['gaps'])

    def test_missing_checks_source_version_and_fingerprint(self):
        self.plan['validation'] = []
        self.plan['new_patch_source'] = None
        ref = self.plan['failure_chain'][1]['external'][0]
        ref['game_version'] = '1.6.fixture'
        ref['assembly_sha256'] = None
        gaps = self.review()['gaps']
        self.assertIn('declared_reference_version_mismatch', gaps)
        self.assertIn('vanilla_reference_missing_assembly_fingerprint', gaps)
        self.assertIn('in_game_outcome_not_reported_passed', gaps)

    def test_failures_cannot_be_overridden_by_other_pass_claims(self):
        self.plan['validation'].append({'check': 'invalid_input_behavior', 'level': 'offline', 'result': 'failed', 'provenance': 'agent_report', 'evidence': 'fixture failure'})
        self.assertIn('failed_or_inconclusive_validation_claims_remain', self.review()['gaps'])

    def test_schema_forbids_arbitrary_operations(self):
        self.plan['execute'] = 'anything'
        with self.assertRaises(ValidationError):
            RepairPlan.model_validate(self.plan)

    def test_claim_requires_evidence_and_runtime_level(self):
        self.plan['validation'][-1]['evidence'] = None
        with self.assertRaises(ValidationError):
            RepairPlan.model_validate(self.plan)

    def test_source_is_inert_and_output_bounded(self):
        self.plan['new_patch_source'] = "raise Exception('must not execute')"
        r = self.review()
        self.assertFalse(r['patch_executed'])
        self.assertNotIn('new_patch_source', r)


if __name__ == '__main__':
    unittest.main()
