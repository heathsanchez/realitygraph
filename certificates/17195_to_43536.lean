-- RealityGraph zero-search countermodel reuse certificate
-- Donor: YanbiaoLab/equational-challenges proof 17195_to_17861
-- New target: 17195_to_43536
-- External corpus pinned at bed33e36c33fca139d902addd8cb77cd4172fe64

set_option maxRecDepth 1000000
set_option maxHeartbeats 0

class Magma (α : Type _) where
  op : α → α → α

@[inherit_doc] infix:65 " ◇ " => Magma.op

@[implicit_reducible]
def magmaFin (n : Nat) (table : List Nat) : Magma (Fin n) where
  op a b :=
    let idx := a.val * n + b.val
    ⟨table[idx]! % n, Nat.mod_lt _ (Fin.pos a)⟩

@[reducible] def EquationLHS (G : Type _) [Magma G] : Prop :=
  ∀ (x y z w : G), x = (y ◇ x) ◇ (x ◇ (y ◇ (z ◇ w)))

@[reducible] def EquationRHS (G : Type _) [Magma G] : Prop :=
  ∀ (x y : G), x ◇ y = x ◇ ((y ◇ y) ◇ (y ◇ x))

abbrev Goal : Prop :=
  ∃ (G : Type) (_ : Magma G), EquationLHS G ∧ ¬ EquationRHS G

def submission : Goal := by
  let m : Magma (Fin 8) := magmaFin 8 [
    0,2,6,2,7,7,0,6,
    2,2,2,2,2,2,2,2,
    3,2,1,5,7,4,0,6,
    0,2,0,2,2,2,0,0,
    5,2,5,5,2,5,2,2,
    3,2,3,5,2,5,0,0,
    2,2,7,2,7,7,2,7,
    5,2,4,5,7,4,2,7
  ]
  refine ⟨Fin 8, m, ?_⟩
  decide

theorem certificate_17195_to_43536 :
    ∃ (G : Type) (_ : Magma G), EquationLHS G ∧ ¬ EquationRHS G :=
  submission

#print axioms certificate_17195_to_43536
