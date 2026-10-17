import Init.Data.Nat.Lemmas

/-!
CLC finite transport proof kernel (Lean 4.24.0)
Scope: finite instances and general abstract laws relative to admitted evaluator functions.
No external truth or source/authentication is inferred from the formal judgments.
-/
namespace FiniteCLC

inductive Verdict where
  | unknown
  | eq
  | dist
  deriving DecidableEq, Repr, BEq

/-- The flat information order: UNKNOWN is below both decisive outcomes. -/
def Refines (a b : Verdict) : Prop := a = .unknown ∨ a = b

theorem refines_refl (a : Verdict) : Refines a a := Or.inr rfl

theorem refines_trans {a b c : Verdict}
    (hab : Refines a b) (hbc : Refines b c) : Refines a c := by
  cases hab with
  | inl ha => exact Or.inl ha
  | inr heq =>
    rw [heq]
    exact hbc

theorem refines_decisive {a b : Verdict}
    (hab : Refines a b) (ha : a ≠ .unknown) : a = b := by
  cases hab with
  | inl hunknown => exact False.elim (ha hunknown)
  | inr heq => exact heq

/-- One typed state-test interface, with a designated protected test family. -/
structure Form (State Test : Type) where
  eval : State → Test → Verdict
  isProtected : Test → Bool

/-- A candidate CLC transport. The verification laws are not assumed here. -/
structure Transport {SA TA SB TB : Type}
    (A : Form SA TA) (B : Form SB TB) where
  forward : SA → SB
  pull : TB → TA
  lift : TA → TB

/-- Refinement + backward protection + protected lift/split. -/
def Valid {SA TA SB TB : Type}
    (A : Form SA TA) (B : Form SB TB)
    (r : Transport A B) : Prop :=
  (∀ x d, Refines (A.eval x (r.pull d)) (B.eval (r.forward x) d)) ∧
  (∀ d, B.isProtected d = true → A.isProtected (r.pull d) = true) ∧
  (∀ p, A.isProtected p = true →
    B.isProtected (r.lift p) = true ∧ r.pull (r.lift p) = p)

/-- A decisive old verdict cannot turn into its opposite under a valid refinement. -/
theorem preserve_decisive {SA TA SB TB : Type}
    {A : Form SA TA} {B : Form SB TB} {r : Transport A B}
    (h : Valid A B r) (x : SA) (d : TB)
    (decisive : A.eval x (r.pull d) ≠ .unknown) :
    A.eval x (r.pull d) = B.eval (r.forward x) d :=
  refines_decisive (h.1 x d) decisive

/-- Strict transport is exact evaluator equality (rather than information refinement). -/
def Strict {SA TA SB TB : Type}
    (A : Form SA TA) (B : Form SB TB)
    (r : Transport A B) : Prop :=
  Valid A B r ∧
  (∀ x d, A.eval x (r.pull d) = B.eval (r.forward x) d)

/-- Compose forward states, contravariant target tests, and protected lifts. -/
def compose {SA TA SB TB SC TC : Type}
    {A : Form SA TA} {B : Form SB TB} {C : Form SC TC}
    (r : Transport A B) (s : Transport B C) : Transport A C :=
  { forward := fun x => s.forward (r.forward x)
    pull := fun d => r.pull (s.pull d)
    lift := fun p => s.lift (r.lift p) }

/-- The CLC transport laws are closed under composition. -/
theorem valid_compose {SA TA SB TB SC TC : Type}
    {A : Form SA TA} {B : Form SB TB} {C : Form SC TC}
    (r : Transport A B) (s : Transport B C)
    (hr : Valid A B r) (hs : Valid B C s) :
    Valid A C (compose r s) := by
  constructor
  · intro x d
    exact refines_trans (hr.1 x (s.pull d)) (hs.1 (r.forward x) d)
  constructor
  · intro d hp
    exact hr.2.1 (s.pull d) (hs.2.1 d hp)
  · intro p hp
    have ha := hr.2.2 p hp
    have hb := hs.2.2 (r.lift p) ha.1
    constructor
    · exact hb.1
    · show r.pull (s.pull (s.lift (r.lift p))) = p
      rw [hb.2, ha.2]

/-- A strict transport is also a developmental refinement. -/
theorem strict_is_valid {SA TA SB TB : Type}
    {A : Form SA TA} {B : Form SB TB} {r : Transport A B}
    (h : Strict A B r) : Valid A B r := h.1

/-- The identity witness is valid without needing any extra axioms. -/
def identity {SA TA : Type} (A : Form SA TA) : Transport A A :=
  { forward := id, pull := id, lift := id }

theorem valid_identity {SA TA : Type} (A : Form SA TA) :
    Valid A A (identity A) := by
  constructor
  · intro x d
    exact refines_refl _
  constructor
  · intro d hd
    exact hd
  · intro p hp
    exact ⟨hp, rfl⟩

end FiniteCLC
