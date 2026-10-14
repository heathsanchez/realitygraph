"""Historical receipt admission tests; runs with real upstream artifacts in CI."""
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
import zipfile

import consumer as rv

BASE = Path(__file__).resolve().parent
FIXTURES = BASE / "fixtures"
POLICY = (BASE / "policy.json").read_bytes()
PIN = "ba9313b4cf4225592dbae5bcd6bbca837d03be34d837e43267544923f3774426"


def repack(archive, edits):
    source = zipfile.ZipFile(io.BytesIO(archive))
    old = {name: source.read(name) for name in source.namelist()}
    for name, content in edits.items():
        old[name] = content
    destination = io.BytesIO()
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
        for name, content in old.items():
            writer.writestr(name, content)
    return destination.getvalue()


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        policy = rv.policy_from_bytes(POLICY, PIN)
        cls.archives = {}
        cls.sources = {}
        for item in policy['receipts']:
            a = FIXTURES / 'artifacts' / (item['id'] + '.zip')
            s = FIXTURES / 'sources' / item['file']
            if not a.exists() or not s.exists():
                raise AssertionError(f'MISSING_GENUINE_FIXTURE: {a}, {s}')
            cls.archives[item['id']] = a.read_bytes()
            cls.sources[item['id']] = s.read_bytes()
        cls.ids = sorted(cls.archives)

    def check(self, *args, **kwargs):
        return rv.replay(POLICY, PIN, self.archives, self.sources, *args, **kwargs)

    def assertRefused(self, reason, fun):
        with self.assertRaises(rv.Refused) as err:
            fun()
        self.assertEqual(err.exception.reason, reason)

    def test_two_independent_original_sources_admitted_without_status_trust(self):
        data = self.check()
        self.assertTrue(data['accepted_history'])
        self.assertEqual(list(data['claims']), self.ids)
        for key in self.ids:
            claim = data['claims'][key]
            self.assertEqual(claim['historical'], 'WARRANTED_BOUNDED_SOURCE_RECEIPT')
            self.assertEqual(claim['current_applicability'], 'NOT_CHECKED')
            self.assertEqual(claim['verified_by_receiver'], 'INTEGRITY_AND_PINNED_LOG_REPLAY_ONLY')
        self.assertEqual(data['claims']['mathlib.function.flip_def']['original_declaration'],
                         'Function.flip_def')
        self.assertEqual(data['claims']['mathlib.nat.choose_zero_right']['original_declaration'],
                         'Nat.choose_zero_right')

    def test_independent_policy_integrity(self):
        mutated = bytearray(POLICY)
        mutated[-3] ^= 1
        self.assertRefused('POLICY_NOT_AUTHORIZED',
            lambda: rv.replay(bytes(mutated), PIN, self.archives, self.sources))

    def test_archive_byte_tampering(self):
        changed = dict(self.archives)
        key = self.ids[0]
        changed[key] = changed[key][:-1] + bytes([changed[key][-1] ^ 1])
        self.assertRefused('UNAUTHORIZED_ARTIFACT_BYTES',
            lambda: rv.replay(POLICY, PIN, changed, self.sources))

    def test_publisher_status_is_not_the_admission_authority(self):
        key = self.ids[0]
        source = zipfile.ZipFile(io.BytesIO(self.archives[key]))
        report = json.loads(source.read('report.json'))
        report['status'] = 'ANY_UNTRUSTED_CLAIM_OF_SUCCESS'
        changed = dict(self.archives)
        changed[key] = repack(self.archives[key], {'report.json': json.dumps(report).encode()})
        self.assertRefused('UNAUTHORIZED_ARTIFACT_BYTES',
            lambda: rv.replay(POLICY, PIN, changed, self.sources))

    def test_source_bytes_changed_even_when_historical_zip_unchanged(self):
        changed = dict(self.sources)
        key = self.ids[0]
        changed[key] = changed[key] + b'\n'
        self.assertRefused('UNAUTHORIZED_SOURCE_BYTES',
            lambda: rv.replay(POLICY, PIN, self.archives, changed))

    def test_source_attribution_swapped(self):
        changed = dict(self.sources)
        changed[self.ids[0]], changed[self.ids[1]] = changed[self.ids[1]], changed[self.ids[0]]
        self.assertRefused('UNAUTHORIZED_SOURCE_BYTES',
            lambda: rv.replay(POLICY, PIN, self.archives, changed))

    def test_rehashed_misattribution_even_with_new_policy_pin(self):
        # An independent recipient must still recompute source selection, even if
        # a hypothetical newly approved archive has its own intact hash.
        key = self.ids[0]
        source = zipfile.ZipFile(io.BytesIO(self.archives[key]))
        report = json.loads(source.read('report.json'))
        report['selection']['discovered_name'] = 'Function.this_is_not_the_source_theorem'
        changed = dict(self.archives)
        changed[key] = repack(self.archives[key],
                              {'report.json': json.dumps(report).encode()})
        policy = json.loads(POLICY)
        for item in policy['receipts']:
            if item['id'] == key:
                item['archive_sha256'] = hashlib.sha256(changed[key]).hexdigest()
        policy_bytes = json.dumps(policy).encode()
        independently_supplied_pin = hashlib.sha256(policy_bytes).hexdigest()
        self.assertRefused('CLAIM_STATEMENT_MISMATCH',
            lambda: rv.replay(policy_bytes, independently_supplied_pin, changed, self.sources))

    def test_rehashed_log_forgery_even_under_reauthorized_archive(self):
        key = self.ids[0]
        source = zipfile.ZipFile(io.BytesIO(self.archives[key]))
        report = json.loads(source.read('report.json'))
        log = b'$ lake env lean SourceForged.lean\n'  # Remove the actual failure diagnostic.
        for step in report['steps']:
            if step['label'] == 'forged_source_binding':
                step['sha256'] = hashlib.sha256(log).hexdigest()
        changed = dict(self.archives)
        changed[key] = repack(self.archives[key], {
            'report.json': json.dumps(report).encode(),
            'forged_source_binding.log': log,
        })
        policy = json.loads(POLICY)
        for item in policy['receipts']:
            if item['id'] == key:
                item['archive_sha256'] = hashlib.sha256(changed[key]).hexdigest()
        policy_bytes = json.dumps(policy).encode()
        self.assertRefused('MISSING_VERIFIER_DIAGNOSTIC',
            lambda: rv.replay(policy_bytes, hashlib.sha256(policy_bytes).hexdigest(),
                              changed, self.sources))

    def test_simulated_withdrawal_is_local_and_reversible(self):
        original = self.check()
        key = self.ids[0]
        revoked = self.check(simulate_withdrawn=frozenset([key]))
        self.assertEqual(revoked['claims'][key]['recipient_support'], 'STALE_SIMULATED_WITHDRAWAL')
        self.assertEqual(revoked['claims'][self.ids[1]]['recipient_support'],
                         'WARRANTED_BOUNDED_HISTORICAL')
        self.assertEqual(revoked['claims'][key]['historical'],
                         original['claims'][key]['historical'])
        self.assertEqual(self.check(), original)
        self.assertEqual(self.check(simulate_withdrawn=frozenset([key])), revoked)

    def test_changed_revision_means_unknown_applicability_not_refuted(self):
        result = self.check(supplied_current_source_commit='0' * 40)
        for item in result['claims'].values():
            self.assertEqual(item['historical'], 'WARRANTED_BOUNDED_SOURCE_RECEIPT')
            self.assertEqual(item['current_applicability'], 'UNKNOWN_SOURCE_REVISION_CHANGED')
            self.assertEqual(item['recipient_support'], 'WARRANTED_BOUNDED_HISTORICAL')

    def test_unrecognized_withdrawal_refused(self):
        self.assertRefused('UNAUTHORIZED_WITHDRAWAL_TARGET',
                           lambda: self.check(simulate_withdrawn=frozenset(['forged-id'])))


if __name__ == '__main__':
    unittest.main()
