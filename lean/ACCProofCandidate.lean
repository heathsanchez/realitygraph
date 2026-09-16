import AC

namespace ACCProofCandidate

open AC

abbrev W := AC.Word 2
abbrev Rels := AC.Relators 2

def x : W := FreeGroup.of (0 : Fin 2)
def y : W := FreeGroup.of (1 : Fin 2)

def ms0 (n : Nat) : W := x⁻¹ * y ^ n * x * (y ^ (n + 1))⁻¹

def ms (n : Nat) (w : W) : Rels :=
  Fin.cases (ms0 n) (fun _ : Fin 1 => x * w⁻¹)

def s1 (n : Nat) (w : W) : Rels :=
  Function.update (ms (n + 1) w) 0 (x * (ms (n + 1) w 0) * x⁻¹)

def s2 (n : Nat) (w : W) : Rels :=
  Function.update (s1 n w) 0 (s1 n w 0 * s1 n w 1)

def s3 (n : Nat) (w : W) : Rels :=
  Function.update (s2 n w) 0 (y⁻¹ * s2 n w 0 * y)

def s4 (n : Nat) (w : W) : Rels :=
  Function.update (s3 n w) 1 (s3 n w 1)⁻¹

def s5 (n : Nat) (w : W) : Rels :=
  Function.update (s4 n w) 0 (s4 n w 0 * s4 n w 1)

def s6 (n : Nat) (w : W) : Rels :=
  Function.update (s5 n w) 1 (s5 n w 1)⁻¹

def s7 (n : Nat) (w : W) : Rels :=
  Function.update (s6 n w) 0 (x⁻¹ * s6 n w 0 * x)

lemma step1 (n : Nat) (w : W) : AC.Step (ms (n + 1) w) (s1 n w) := by
  simpa [s1] using AC.Step.conj (ms (n + 1) w) (0 : Fin 2) x

lemma step2 (n : Nat) (w : W) : AC.Step (s1 n w) (s2 n w) := by
  simpa [s2] using AC.Step.mulRight (s1 n w) (0 : Fin 2) (1 : Fin 2) (by decide)

lemma step3 (n : Nat) (w : W) : AC.Step (s2 n w) (s3 n w) := by
  simpa [s3] using AC.Step.conj (s2 n w) (0 : Fin 2) y⁻¹

lemma step4 (n : Nat) (w : W) : AC.Step (s3 n w) (s4 n w) := by
  simpa [s4] using AC.Step.inv (s3 n w) (1 : Fin 2)

lemma step5 (n : Nat) (w : W) : AC.Step (s4 n w) (s5 n w) := by
  simpa [s5] using AC.Step.mulRight (s4 n w) (0 : Fin 2) (1 : Fin 2) (by decide)

lemma step6 (n : Nat) (w : W) : AC.Step (s5 n w) (s6 n w) := by
  simpa [s6] using AC.Step.inv (s5 n w) (1 : Fin 2)

lemma step7 (n : Nat) (w : W) : AC.Step (s6 n w) (s7 n w) := by
  simpa [s7] using AC.Step.conj (s6 n w) (0 : Fin 2) x⁻¹

lemma endpoint (n : Nat) (w : W) (h : w⁻¹ * y * w = y) : s7 n w = ms n w := by
  funext i
  refine Fin.cases ?_ (fun j => ?_) i
  · simp [s7, s6, s5, s4, s3, s2, s1, ms, ms0, x, y, h, pow_succ, mul_assoc]
  · have hj : j = 0 := Fin.eq_zero j
    subst j
    simp [s7, s6, s5, s4, s3, s2, s1, ms, ms0, x, y, h, pow_succ, mul_assoc]

/-- The exact recurrence discovered by replay: under the centralizer condition
`w⁻¹ y w = y`, one Miller-Schupp parameter step is AC-reachable.  The official
finite verifier realizes multiplication by an inverse in one move; the shared
proof-track `AC.Step` basis realizes that derived move by invert/multiply/invert,
so this proof uses seven abstract AC steps. -/
theorem millerSchupp_recurrence (n : Nat) (w : W) (h : w⁻¹ * y * w = y) :
    AC.Reachable (ms (n + 1) w) (ms n w) := by
  have p1 : AC.Reachable (ms (n + 1) w) (s1 n w) :=
    Relation.ReflTransGen.single (step1 n w)
  have p2 : AC.Reachable (ms (n + 1) w) (s2 n w) := p1.tail (step2 n w)
  have p3 : AC.Reachable (ms (n + 1) w) (s3 n w) := p2.tail (step3 n w)
  have p4 : AC.Reachable (ms (n + 1) w) (s4 n w) := p3.tail (step4 n w)
  have p5 : AC.Reachable (ms (n + 1) w) (s5 n w) := p4.tail (step5 n w)
  have p6 : AC.Reachable (ms (n + 1) w) (s6 n w) := p5.tail (step6 n w)
  have p7 : AC.Reachable (ms (n + 1) w) (s7 n w) := p6.tail (step7 n w)
  rw [endpoint n w h] at p7
  exact p7

end ACCProofCandidate
