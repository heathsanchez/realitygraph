import unittest

from realitygraph.meta_memory import (
    MetaMemory,
    RepairEpisode,
    RepairPhase,
    RepairRuleStatus,
)


def episode(
    ident: str,
    phase: RepairPhase,
    *,
    fingerprint: str = "fp-a",
    strategy_id: str = "add-observable",
    strategy_version: str = "v1",
    portfolio_digest: str = "portfolio-a",
    authority: str = "authority-a",
    verifier: str = "verifier-a",
    interface: str = "interface-a",
    selection_cost: int = 1,
) -> RepairEpisode:
    return RepairEpisode(
        episode_id=ident,
        phase=phase,
        obstruction_fingerprint=fingerprint,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        portfolio_digest=portfolio_digest,
        authority_snapshot=authority,
        verifier_id=verifier,
        interface_digest=interface,
        selection_cost=selection_cost,
        object_evidence_digest=f"evidence-{ident}",
    )


class MetaMemoryTests(unittest.TestCase):
    def test_rule_requires_independent_calibration_before_promotion(self):
        memory = MetaMemory.empty().record_success(
            episode("source", RepairPhase.ACQUISITION)
        )
        self.assertEqual(len(memory.rules), 1)
        self.assertEqual(memory.rules[0].status, RepairRuleStatus.CANDIDATE)

        promoted = memory.record_success(
            episode("calibration", RepairPhase.CALIBRATION)
        )
        self.assertEqual(promoted.rules[0].status, RepairRuleStatus.PROMOTED)
        self.assertEqual(
            promoted.rules[0].source_episode_digests,
            tuple(sorted((
                episode("source", RepairPhase.ACQUISITION).digest,
                episode("calibration", RepairPhase.CALIBRATION).digest,
            ))),
        )

    def test_disagreeing_calibration_does_not_promote_source_rule(self):
        memory = MetaMemory.empty().record_success(
            episode("source", RepairPhase.ACQUISITION, strategy_id="s1")
        )
        memory = memory.record_success(
            episode("calibration", RepairPhase.CALIBRATION, strategy_id="s2")
        )
        self.assertFalse(any(rule.status is RepairRuleStatus.PROMOTED for rule in memory.rules))
        self.assertEqual({rule.strategy_id for rule in memory.rules}, {"s1", "s2"})

    def test_promoted_match_requires_exact_boundary_identity(self):
        memory = MetaMemory.empty()
        memory = memory.record_success(episode("a", RepairPhase.ACQUISITION))
        memory = memory.record_success(episode("b", RepairPhase.CALIBRATION))
        match = memory.promoted_match(
            obstruction_fingerprint="fp-a",
            portfolio_digest="portfolio-a",
            authority_snapshot="authority-a",
            verifier_id="verifier-a",
            interface_digest="interface-a",
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.strategy_id, "add-observable")
        self.assertIsNone(memory.promoted_match(
            obstruction_fingerprint="fp-a",
            portfolio_digest="portfolio-a",
            authority_snapshot="authority-stale",
            verifier_id="verifier-a",
            interface_digest="interface-a",
        ))

    def test_revocation_removes_rule_from_active_match_without_deleting_lineage(self):
        memory = MetaMemory.empty()
        memory = memory.record_success(episode("a", RepairPhase.ACQUISITION))
        memory = memory.record_success(episode("b", RepairPhase.CALIBRATION))
        rule_id = memory.rules[0].rule_id
        revoked = memory.revoke(rule_id)
        self.assertEqual(revoked.rules[0].status, RepairRuleStatus.REVOKED)
        self.assertIsNone(revoked.promoted_match(
            obstruction_fingerprint="fp-a",
            portfolio_digest="portfolio-a",
            authority_snapshot="authority-a",
            verifier_id="verifier-a",
            interface_digest="interface-a",
        ))
        self.assertEqual(revoked.rules[0].source_episode_digests, memory.rules[0].source_episode_digests)

    def test_meta_memory_round_trip_is_byte_exact(self):
        memory = MetaMemory.empty()
        memory = memory.record_success(episode("a", RepairPhase.ACQUISITION))
        memory = memory.record_success(episode("b", RepairPhase.CALIBRATION))
        text = memory.text()
        restarted = MetaMemory.from_text(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest, memory.digest)

    def test_duplicate_episode_is_idempotent(self):
        source = episode("source", RepairPhase.ACQUISITION)
        memory = MetaMemory.empty().record_success(source)
        repeated = memory.record_success(source)
        self.assertEqual(repeated.text(), memory.text())


if __name__ == "__main__":
    unittest.main()
