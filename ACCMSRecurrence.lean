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
identity exposed by the five Discovery-track moves.  The proof expands the
Discovery-track inverse-relator multiplication into the official Proof-track
primitive steps: invert the second relator, multiply, then invert it back. -/
theorem ms_centralizer_recurrence (n : ℕ) (w : Word)
    (hcentral : w⁻¹ * y * w = y) :
    AC.Reachable (P (n + 1) w) (P n w) := by
  let i : Fin 2 := 0
  let j : Fin 2 := 1
  have hij : i ≠ j := by decide

  let R0 : AC.Relators 2 := P (n + 1) w
  let R1 : AC.Relators 2 := Function.update R0 i (x * R0 i * x⁻¹)
  let R2 : AC.Relators 2 := Function.update R1 i (R1 i * R1 j)
  let R3 : AC.Relators 2 := Function.update R2 i (y⁻¹ * R2 i * (y⁻¹)⁻¹)
  let R4 : AC.Relators 2 := Function.update R3 j (R3 j)⁻¹
  let R5 : AC.Relators 2 := Function.update R4 i (R4 i * R4 j)
  let R6 : AC.Relators 2 := Function.update R5 j (R5 j)⁻¹
  let R7 : AC.Relators 2 := Function.update R6 i (x⁻¹ * R6 i * (x⁻¹)⁻¹)

  have h01 : AC.Step R0 R1 := by
    exact AC.Step.conj R0 i x
  have h12 : AC.Step R1 R2 := by
    exact AC.Step.mulRight R1 i j hij
  have h23 : AC.Step R2 R3 := by
    exact AC.Step.conj R2 i y⁻¹
  have h34 : AC.Step R3 R4 := by
    exact AC.Step.inv R3 j
  have h45 : AC.Step R4 R5 := by
    exact AC.Step.mulRight R4 i j hij
  have h56 : AC.Step R5 R6 := by
    exact AC.Step.inv R5 j
  have h67 : AC.Step R6 R7 := by
    exact AC.Step.conj R6 i x⁻¹

  have p1 : AC.Reachable R0 R1 :=
    Relation.ReflTransGen.tail Relation.ReflTransGen.refl h01
  have p2 : AC.Reachable R0 R2 := Relation.ReflTransGen.tail p1 h12
  have p3 : AC.Reachable R0 R3 := Relation.ReflTransGen.tail p2 h23
  have p4 : AC.Reachable R0 R4 := Relation.ReflTransGen.tail p3 h34
  have p5 : AC.Reachable R0 R5 := Relation.ReflTransGen.tail p4 h45
  have p6 : AC.Reachable R0 R6 := Relation.ReflTransGen.tail p5 h56
  have p7 : AC.Reachable R0 R7 := Relation.ReflTransGen.tail p6 h67

  have hfinal : R7 = P n w := by
    funext k
    fin_cases k
    · simp [R7, R6, R5, R4, R3, R2, R1, R0, P, A, B, i, j, hcentral]
      group
    · simp [R7, R6, R5, R4, R3, R2, R1, R0, P, A, B, i, j]

  rw [hfinal] at p7
  simpa [R0] using p7

end ACCMSRecurrence
