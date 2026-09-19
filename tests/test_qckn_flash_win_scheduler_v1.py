from __future__ import annotations

import unittest

from qckn_flash_win_scheduler_v1 import (
    BUDGET,
    DEADLINE_PRESSURE,
    ranking_controls,
    run_policy,
    run_probe,
)
from realitygraph.win_scheduler import (
    GlobalWinScheduler,
    VerifiedWinEvent,
    WinOpportunity,
)


class WinSchedulerContracts(unittest.TestCase):
    def test_unverified_event_cannot_cancel_shared_work(self):
        scheduler = GlobalWinScheduler(
            (
                WinOpportunity(
                    "a", "x", 1, 1, 1, 0, 0, 0, 0, 1, 1
                ),
                WinOpportunity(
                    "b", "x", 1, 1, 1, 0, 0, 0, 0, 1, 1
                ),
            )
        )
        with self.assertRaises(ValueError):
            scheduler.admit_event(
                VerifiedWinEvent(
                    "sham",
                    "a",
                    False,
                    cancel_opportunities=("b",),
                )
            )
        self.assertEqual(scheduler.metrics()["open"], ["a", "b"])

    def test_verified_event_reprices_and_cancels(self):
        scheduler = GlobalWinScheduler(
            (
                WinOpportunity(
                    "bridge", "x", 1, 1, 1, 1, 2, 10, 1, 1, 1
                ),
                WinOpportunity(
                    "target", "y", 10, 1, 1, 0, 0, 0, 0, 8, 8
                ),
                WinOpportunity(
                    "dup", "y", 2, 1, 1, 0, 0, 0, 0, 3, 2
                ),
            )
        )
        before = scheduler.opportunities["target"]
        delta = scheduler.admit_event(
            VerifiedWinEvent(
                "verified-bridge",
                "bridge",
                True,
                flash_radius_realized=2,
                cancel_opportunities=("dup",),
                cost_multipliers=(("target", 0.25),),
                latency_multipliers=(("target", 0.5),),
            )
        )
        after = scheduler.opportunities["target"]
        self.assertLess(after.cost, before.cost)
        self.assertLess(after.latency, before.latency)
        self.assertEqual(delta.cancelled, ("dup",))
        self.assertEqual(delta.repriced, ("target",))

    def test_authority_discount_applies_only_to_global_value(self):
        weak = WinOpportunity(
            "weak",
            "cross-domain",
            direct_win=1,
            verification_probability=1,
            authority_readiness=0.2,
            destination_bridge_probability=0.1,
            flash_radius=100,
            future_search_removed=1000,
            composition_unlocks=10,
            cost=1,
            latency=1,
        )
        strong = WinOpportunity(
            "strong",
            "local",
            direct_win=1,
            verification_probability=1,
            authority_readiness=1,
            destination_bridge_probability=0.8,
            flash_radius=5,
            future_search_removed=20,
            composition_unlocks=2,
            cost=1,
            latency=1,
        )
        scheduler = GlobalWinScheduler((weak, strong))
        ranked = scheduler.rank(mode="DISCOVERY")
        self.assertEqual(ranked[0].opportunity_id, "strong")


class QCKNWinSchedulerQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_probe()

    def test_win_scheduler_beats_direct_greedy(self):
        self.assertGreater(
            self.result["win_scheduler"]["direct_win"],
            self.result["direct_greedy"]["direct_win"],
        )

    def test_win_scheduler_beats_round_robin(self):
        self.assertGreater(
            self.result["win_scheduler"]["direct_win"],
            self.result["round_robin"]["direct_win"],
        )

    def test_compounding_bridge_precedes_final_boss(self):
        steps = self.result["win_scheduler"]["steps"]
        self.assertIn("bridge-lemma", steps)
        self.assertIn("final-boss", steps)
        self.assertLess(
            steps.index("bridge-lemma"),
            steps.index("final-boss"),
        )

    def test_budget_is_respected(self):
        self.assertLessEqual(
            self.result["win_scheduler"]["spent"],
            BUDGET,
        )

    def test_discovery_and_battle_differ(self):
        controls = ranking_controls()
        self.assertEqual(
            controls["discovery_order"][0],
            "flash-infrastructure",
        )
        self.assertNotEqual(
            controls["battle_order"][0],
            "flash-infrastructure",
        )

    def test_speculative_global_is_discounted(self):
        self.assertTrue(
            self.result["controls"][
                "speculative_global_below_verified_bridge"
            ]
        )

    def test_all_declared_gates_pass(self):
        self.assertTrue(self.result["passed"])
        self.assertTrue(all(self.result["gates"].values()))


class QCKNWinSchedulerDeterminism(unittest.TestCase):
    def test_policy_repeatability(self):
        left = run_policy("WIN_SCHEDULER")
        right = run_policy("WIN_SCHEDULER")
        self.assertEqual(left.direct_win, right.direct_win)
        self.assertEqual(left.spent, right.spent)
        self.assertEqual(left.steps, right.steps)
        self.assertEqual(left.events, right.events)


if __name__ == "__main__":
    unittest.main(verbosity=2)
