import AC

namespace ACCMSRecurrence

abbrev Word := AC.Word 2

def x : Word := FreeGroup.of (0 : Fin 2)
def y : Word := FreeGroup.of (1 : Fin 2)

def A (n : ℕ) : Word := x⁻¹ * y ^ n * x * (y ^ (n + 1))⁻¹

def B (w : Word) : Word := x * w⁻¹

def P (n : ℕ) (w : Word) : AC.Relators 2 := ![A n, B w]

/-- The exact Miller--Schupp recurrence discovered by the replay system.

The centralizer hypothesis is deliberately stated as the precise residual
identity exposed by the five Discovery-track moves.  The proof must use the
official Proof-track `AC.Step`/`AC.Reachable` definitions imported above. -/
theorem ms_centralizer_recurrence (n : ℕ) (w : Word)
    (hcentral : w⁻¹ * y * w = y) :
    AC.Reachable (P (n + 1) w) (P n w) := by
  exact Relation.ReflTransGen.refl

end ACCMSRecurrence
