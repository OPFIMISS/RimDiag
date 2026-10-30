import unittest
from rimdiag.core import fingerprint
from rimdiag.parsing import normalize, split_prefix, symptom, annotations, identity_text


class ParsingTests(unittest.TestCase):
    def test_full_dates_do_not_break_grouping(self):
        a = '2026-10-30 18:20:31.001 ERROR [Verse] XML error: Def42'
        b = '2026-10-31 19:21:32.002 ERROR [Verse] XML error: Def42'
        self.assertEqual(fingerprint(a), fingerprint(b))
        self.assertEqual(normalize(a), 'XML error: Def42')
        self.assertNotEqual(fingerprint(a), fingerprint(b.replace('Def42', 'Def43')))

    def test_exported_thread_marker_and_nested_hint(self):
        line = '18:05:42.001 [메인] [Likely: [Example] Display Name] Could not find type named Example.Missing from node <X/>'
        parsed = split_prefix(line)
        self.assertEqual(parsed['reported_attribution'], '[Example] Display Name')
        self.assertTrue(parsed['message'].startswith('Could not find'))
        self.assertEqual(annotations(line)[0]['verified'], False)

    def test_unknown_mod_tag_is_preserved(self):
        self.assertEqual(normalize('12:00:01 ERROR [OtherLogger] Error A'), '[OtherLogger] Error A')
        self.assertNotEqual(fingerprint('[A] ERROR X'), fingerprint('[B] ERROR X'))

    def test_symptom_family_does_not_delete_exact_differences(self):
        a = 'Could not find type named Example.Missing from node <A/>'
        b = 'Could not find type named Example.Missing from node <B/>'
        self.assertEqual(symptom(a), symptom(b))
        self.assertNotEqual(fingerprint(a), fingerprint(b))
        self.assertNotEqual(symptom(a), symptom(a.replace('Missing', 'Different')))

    def test_unknown_field_family_preserves_target_type(self):
        a = "XML error: <option>A</option> doesn't correspond to any field in type Example.Type. Context: <A/>"
        b = a.replace('>A<', '>B<')
        self.assertEqual(symptom(a), symptom(b))
        self.assertNotEqual(symptom(a), symptom(a.replace('Example.Type', 'Example.Other')))

    def test_reporter_guess_is_removed_from_identity_input(self):
        text = '12:00:00 ERROR [Verse] [Likely: sample.a] Exception: actual\n[Error Helper] Likely cause: sample.b.'
        self.assertNotIn('sample.a', identity_text(text))
        self.assertNotIn('sample.b', identity_text(text))
        hints = annotations(text)
        self.assertEqual(len(hints), 2)
        self.assertTrue(all(not h['verified'] for h in hints))

    def test_sentence_error_is_not_a_transport_severity(self):
        text = 'Error while instantiating a mod of type Example.Mod: System.Reflection.TargetInvocationException: failed'
        self.assertEqual(normalize(text), text)
        self.assertEqual(normalize(normalize(text)), text)
        from rimdiag.parsing import category
        self.assertEqual(category(text)['category'], 'initialization')

    def test_def_configuration_family_retains_exact_def_groups(self):
        a = 'Config error in ExampleA: has null thingClass.'
        b = 'Config error in ExampleB: has null thingClass.'
        self.assertEqual(symptom(a), symptom(b))
        self.assertNotEqual(fingerprint(a), fingerprint(b))


if __name__ == '__main__':
    unittest.main()
