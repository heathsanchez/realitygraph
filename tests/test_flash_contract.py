import tempfile
from pathlib import Path
import unittest

from realitygraph.flash_contract import (
    CapabilityState,
    DependencyRule,
    FlashEvent,
    FlashEventKind,
    FrontierState,
    IncrementalFlashRuntime,
)


class FlashContractTests(unittest.TestCase):
    def runtime(self):
        cap=CapabilityState(
            "cap:verified",
            "VERIFIED",
            "ACTIVE",
            "fixture",
            "fixture",
        )
        return IncrementalFlashRuntime(
            (
                FrontierState(
                    "a","a",10,10,
                    route_ids={"r"},
                    base_route_ids={"r"},
                    reserve_capabilities={"cap:verified"},
                ),
                FrontierState(
                    "b","b",10,10,
                    route_ids={"s"},
                    base_route_ids={"s"},
                ),
            ),
            (
                DependencyRule("p","k","a","remove_route","r"),
                DependencyRule("q","revive","a","activate_capability","cap:verified"),
            ),
            (cap,),
        )

    def event(self,eid,key,kind=FlashEventKind.OBSTRUCTION):
        return FlashEvent(
            eid,kind,"a",key,"fixture-authority",("fixture",)
        )

    def test_incremental_and_revocation(self):
        rt=self.runtime()
        d=rt.admit(self.event("e1","k"))
        self.assertEqual(d.touched_frontiers,("a",))
        self.assertNotIn("r",rt.frontiers["a"].route_ids)
        self.assertIn("s",rt.frontiers["b"].route_ids)
        rev=rt.revoke("e1",reason="test")
        self.assertEqual(rev.touched_frontiers,("a",))
        self.assertIn("r",rt.frontiers["a"].route_ids)

    def test_restart_without_replay(self):
        rt=self.runtime()
        rt.admit(self.event("e1","k"))
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"state.json"
            rt.save_compiled_present(p)
            re=IncrementalFlashRuntime.load_compiled_present(p,rt.rules)
            self.assertEqual(re.replayed_events_on_restart,0)
            self.assertEqual(
                re.snapshot()["frontiers"],
                rt.snapshot()["frontiers"],
            )

    def test_repeated_event_is_idempotent(self):
        rt=self.runtime()
        event=self.event("e1","k")
        rt.admit(event)
        d=rt.admit(event)
        self.assertEqual(d.iterations,0)
        self.assertEqual(d.touched_frontiers,())
        self.assertEqual(d.changed_frontiers,())

    def test_reserve_semantics_do_not_activate_without_economic_win(self):
        reserve=CapabilityState(
            "cap:reserve",
            "VERIFIED",
            "RESERVE",
            "fixture",
            "semantically valid but no preference win",
        )
        rt=IncrementalFlashRuntime(
            (FrontierState("a","a",5,5),),
            (DependencyRule("r","verified","a","activate_capability","cap:reserve"),),
            (reserve,),
        )
        rt.admit(self.event("e","verified",FlashEventKind.PREFERENCE_CHANGE))
        self.assertIn("cap:reserve",rt.frontiers["a"].reserve_capabilities)
        self.assertNotIn("cap:reserve",rt.frontiers["a"].active_capabilities)


if __name__=="__main__":
    unittest.main()
