import tempfile
import unittest
from pathlib import Path
from rimdiag.core import Diagnostics, DiagnosticError
from rimdiag.impact import ImpactReport, prioritize, signals


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'Player.log'
        self.diag = Diagnostics(self.root / 'runs', [self.log])

    def scan(self, text):
        self.log.write_text(text, encoding='utf-8')
        return self.diag.analyze()['run_id']

    def test_one_blocker_outranks_frequent_cosmetic_errors(self):
        run = self.scan('ERROR: Missing texture cosmetic\n' * 200 +
                        'NullReferenceException: reading failed\n at RimWorld.ReadingPolicyDatabase.GenerateStartingPolicies()\n')
        result = prioritize(self.diag, run)
        self.assertEqual(result['investigation_priorities'][0]['impact_signal'], 'required_initialization_failure')
        self.assertEqual(result['occurrences_inspected'], 201)
        self.assertEqual(self.diag.triage(run)['investigation_priorities'], result['investigation_priorities'])

    def test_same_headline_later_occurrence_keeps_stronger_stack(self):
        run = self.scan('NullReferenceException: failed\n at Other.Run()\n'
                        'NullReferenceException: failed\n at RimWorld.ReadingPolicyDatabase.GenerateStartingPolicies()\n')
        row = prioritize(self.diag, run)['investigation_priorities'][0]
        self.assertEqual(row['occurrence'], 1)
        self.assertEqual(row['score'], 100)
        self.assertIn('ReadingPolicyDatabase', self.diag.evidence(run, row['group_id'], row['occurrence'])['text'])

    def test_null_definition_is_structural_not_cosmetic(self):
        run = self.scan('Config error in GlowObject: has null thingClass\nERROR: Missing texture furniture\n')
        row = prioritize(self.diag, run)['investigation_priorities'][0]
        self.assertEqual(row['impact_signal'], 'structurally_invalid_definition')
        self.assertEqual(row['causality'], 'unconfirmed')

    def test_report_remains_user_claim_and_does_not_repair_data(self):
        run = self.scan('Config error in GlowObject: has null thingClass\n')
        group = self.diag.list_errors(run)['groups'][0]['fingerprint']
        report = ImpactReport(symptom='Cannot enter map', blocked_stage='map_creation', related_group_ids=[group],
                              outcome_after_workaround='User can enter map after guard')
        result = prioritize(self.diag, run, report)
        self.assertEqual(result['investigation_priorities'][0]['score'], 110)
        self.assertFalse(result['report_independently_verified'])
        self.assertFalse(result['workaround_means_data_repaired'])
        self.assertEqual(result['structural_data_leads'][0]['log_impact_signal'], 'structurally_invalid_definition')
        self.assertEqual(result['functional_status'], 'not_tested')
        with self.assertRaises(DiagnosticError):
            prioritize(self.diag, run, report.model_copy(update={'related_group_ids': ['f'*24]}))

    def test_likely_cause_hint_cannot_manufacture_blocker(self):
        run = self.scan('ERROR: missing texture\nLikely cause: ReadingPolicyDatabase.GenerateStartingPolicies NullReferenceException\n')
        self.assertNotEqual(prioritize(self.diag, run)['investigation_priorities'][0]['score'], 100)

    def test_unknown_empty_and_budget(self):
        run = self.scan('Normal game startup\n')
        self.assertEqual(prioritize(self.diag, run)['investigation_priorities'], [])
        with self.assertRaises(DiagnosticError):
            prioritize(self.diag, run, count=11)
        self.assertEqual(signals('ERROR unknown', '')[0], 20)
