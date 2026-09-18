import unittest

from qckn_flash_kernel_v1 import run_flash, run_independent, run_sham


class FlashKernelV1Tests(unittest.TestCase):
    def test_global_flash_beats_siloed_pipelines_on_frozen_market(self):
        independent = run_independent()
        _kernel, flash = run_flash()
        self.assertEqual(independent["pending_candidate_search_after_local_evidence"], 93)
        self.assertEqual(independent["discharged_obligations"], 0)
        self.assertEqual(flash["flash_acquisition_cost"], 9)
        self.assertEqual(flash["total_search_eliminated"], 96)
        self.assertEqual(flash["open_workers_after_flash"], 0)
        self.assertEqual(flash["g_event_generated"], ["h"])
        self.assertEqual(flash["flash_radius"], 12)

    def test_good_failure_prunes_globally(self):
        _kernel, flash = run_flash()
        self.assertEqual(flash["pruned_by_informative_failure"], 12)
        self.assertEqual(flash["after_global_obstruction_pending"], 84)

    def test_future_continuations_define_present_and_revoke_cleanly(self):
        _kernel, flash = run_flash()
        self.assertEqual(
            flash["future_classes_after_first"],
            [["a", "b"], ["c"]],
        )
        self.assertEqual(
            flash["future_classes_after_separator"],
            [["a"], ["b"], ["c"]],
        )
        self.assertEqual(
            flash["future_classes_after_revocation"],
            [["a", "b"], ["c"]],
        )

    def test_targeted_ablation_restores_unresolved_search(self):
        _kernel, flash = run_flash()
        self.assertEqual(flash["ablation_reopened"], 12)
        self.assertEqual(flash["ablation_restored_pending_search"], 84)

    def test_irrelevant_verified_capability_does_not_mutate_protected_work(self):
        sham = run_sham()
        self.assertEqual(sham["before"], 96)
        self.assertEqual(sham["after"], 96)
        self.assertEqual(sham["discharged"], [])
        self.assertEqual(sham["generated_capabilities"], [])


if __name__ == "__main__":
    unittest.main()
