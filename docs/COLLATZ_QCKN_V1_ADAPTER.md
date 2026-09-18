# Collatz QCKN V1 Adapter

## Status

This adapter is a compatible QCKN V1 domain extension built from the frozen
QCKN V1 runtime. It does **not** modify the frozen QCK or QCKN semantics.

Frozen runtime base:

- repository: `heathsanchez/realitygraph`
- branch: `qckn-v1-frozen`
- commit: `527cb7df1d931be53a61b1523abeaae20501af27`

Adapter branch:

- `collatz-qckn-v1-adapter`

The purpose of this adapter is to make the already-existing Collatz research
loop explicit as QCKN state:

[
oxed{
	ext{residual}
	o
	ext{verified capability / repair rule}
	o
	ext{causal promotion}
	o
	ext{CompiledPresent}
	o
	ext{exact restart}
	o
	ext{future reuse}
	o
	ext{ablation}.
}
]

This is an architectural closure, not a proof of the Collatz conjecture.

---

## 1. Domain contract

Shortcut map:

[
T(n)=
egin{cases}
n/2,&n	ext{ even},\\
(3n+1)/2,&n	ext{ odd}.
end{cases}
]

Protected consequence:

[
oxed{
	ext{lower merge / certified descent to an already-smaller source.}
}
]

For the retained endpoint capability used in this adapter, a concrete endpoint
(x) is certified by an exact finite tail

[
T^k(x)=1.
]

Any source whose trajectory reaches (x) therefore shares the tail at (1).

Authority boundary:

- authority: `collatz-shortcut-exact-v1`
- verifier: `collatz-exact-integer-replay-v1`

No empirical or probabilistic evidence can promote an endpoint capability.

---

## 2. Typed residual

The adapter distinguishes two endpoint obligations.

### COMPILED

The endpoint is already present in the active verified endpoint bank.

Routing:

[
	ext{COMPILED}	o	ext{TERMINAL}.
]

### UNKNOWN_IDENTITY

The endpoint is a live endpoint not represented in the active bank.

Routing:

[
	ext{UNKNOWN_IDENTITY}	o	ext{SPLIT}.
]

The promoted repair rule then identifies the licensed repair family:

> verify the concrete endpoint tail exactly; if successful, promote the
> endpoint capability.

This preserves proposal/promotion separation.

---

## 3. Frozen endpoint capability

Before the prospective 27-bit holdout, the endpoint bank was frozen with ten
verified endpoints:

[
egin{aligned}
&147269353, 153560809, 157755113, 260515561, 373761769,\
&1205282537, 1290217193, 1928799977, 2196186857, 4083623657.
end{aligned}
]

Every row is independently replayed by the adapter before the
`FiniteCapability` can be constructed.

The capability records:

- endpoint input;
- exact tail-to-one result;
- authority snapshot;
- verifier identity;
- certificate identity;
- evidence provenance;
- acquisition cost.

It is then promoted through the immutable QCKN causal ledger.

---

## 4. Promoted repair rule

The endpoint repair strategy is not promoted from a single successful use.

The adapter constructs separate:

- ACQUISITION evidence;
- CALIBRATION evidence.

Only after both are recorded does QCKN `MetaMemory` promote the exact repair
rule.

The rule is bound to:

- obstruction fingerprint;
- strategy identity/version;
- portfolio digest;
- authority;
- verifier;
- interface digest;
- evidence lineage;
- ablation handle.

The causal ledger promotes the endpoint capability first and the repair rule
as a causally dependent later event.

---

## 5. CompiledPresent and restart

The ledger is compiled through the frozen QCKN
`materialize_compiled_present()` implementation.

Qualification requires:

[
oxed{
operatorname{parse}(operatorname{text}(P))=P
}
]

and exact digest preservation after restart.

Raw acquisition/calibration episodes do not enter active cognition.

---

## 6. Prospective 27-bit causal compounding test

The future sequence is the exact live-endpoint multiplicity profile from the
untouched 27-bit C9 holdout.

It contains:

[
25	ext{ endpoint hits}
]

covering

[
12	ext{ unique endpoints}.
]

Six endpoint identities were already represented by the frozen bank. Six were
genuinely new.

The adapter measures two prospective costs:

- independent endpoint-verifier calls;
- repair-portfolio search calls.

### WARM

Starts only from causally promoted and restarted QCKN active state.

Expected:

[
oxed{
6	ext{ verifier calls},qquad0	ext{ portfolio searches}.
}
]

The six calls are the six genuinely new endpoint identities.

### COLD

No retained capability or repair rule.

Expected:

[
oxed{
12	ext{ verifier calls},qquad12	ext{ portfolio searches}.
}
]

### RAW_HISTORY

The historical evidence identifiers exist, but nothing is compiled into active
QCKN memory.

Expected: identical to COLD.

### SHAM

A similarly shaped endpoint capability and repair rule are present, but their
endpoint carrier / obstruction fingerprint do not match.

Expected: identical to COLD.

### CAPABILITY_ABLATION

The endpoint bank is causally revoked while the repair rule remains.

Expected:

[
12	ext{ verifier calls},qquad0	ext{ portfolio searches}.
]

This isolates the causal contribution of endpoint reuse.

### REPAIR_RULE_ABLATION

The endpoint bank remains but the repair rule is revoked.

Expected:

[
6	ext{ verifier calls},qquad6	ext{ portfolio searches}.
]

This isolates the causal contribution of retained repair-family selection.

### FULL ABLATION

Both endpoint capability and repair rule are revoked through causal events,
then the present is recompiled and restarted.

Expected: exact restoration of the COLD result.

This is the principal causal-compounding qualification.

---

## 7. Cross-repository evidence pins

The cross-repository gate independently checks the Collatz artifacts against
pinned source commits.

### Endpoint / family evidence

Repository:

- `heathsanchez/test`

Pinned commit:

- `34b1979f048993a914cc75dcd2af3f7b6daa04e2`

The gate independently replays:

- endpoint (157755113	o1) in 105 shortcut steps;
- endpoint (373761769	o1) in 146 shortcut steps;
- the reverse-family compiler for the exact t153 family.

### Prospective forward-macro transfer

Repository:

- `heathsanchez/test`

Pinned commit:

- `91742a2d544e9a4e46d2b936560000b8ae6f5643`

Reference source run:

- `35327397877`
- job: `105543545053`

The cross-repository qualification reruns:

[
	exttt{--train-hi 8191 --held-hi 16383 --K 96 --maxlen 12}
]

and requires:

[
oxed{
481	ext{ learned macros},quad
88	ext{ held-out closures},quad
74	ext{ remaining hard sources}.
}
]

The remaining hard sources stay residuals. They are not converted into an
expressivity claim.

---

## 8. What is now closed

The architectural gap identified before this adapter is closed:

1. Collatz evidence is independently verified before promotion.
2. Endpoint capabilities are represented as typed QCKN capabilities.
3. The endpoint-repair strategy requires acquisition plus calibration before
   promotion.
4. Promotions are immutable causal events.
5. Causal history compiles to `CompiledPresent`.
6. The compiled state restarts exactly.
7. Future held-out work receives measurable verified reuse.
8. RAW_HISTORY and SHAM do not reproduce the advantage.
9. Targeted causal revocation restores the corresponding cold cost.
10. Missing evidence remains unresolved rather than being silently claimed.

Therefore it is now justified to describe this bounded experiment as:

[
oxed{
	extbf{QCKN V1 causal capability compounding on the Collatz domain.}
}
]

---

## 9. Claim boundary

This adapter does **not** establish:

- the Collatz conjecture;
- universal endpoint-bank finiteness;
- universal transfer of forward macros;
- universal lower-merge generation;
- universal repair optimality;
- unbounded QCKN self-development.

The mathematical residual remains whatever lower-merge-free obligations survive
the current verified capability set.

The adapter changes how verified lessons are retained and reused; it does not
change the truth conditions of the mathematics.

---

## 10. Operating rule going forward

New Collatz development should now follow:

[
oxed{
egin{array}{c}
	ext{exact residual}\
downarrow\
	ext{smallest warranted candidate}\
downarrow\
	ext{independent exact verifier}\
downarrow\
	ext{promotion evidence}\
downarrow\
	ext{causal ledger}\
downarrow\
	ext{CompiledPresent}\
downarrow\
	ext{restart}\
downarrow\
	ext{held-out reuse / ablation}.
end{array}
}
]

A discovered endpoint, macro, reverse-family law, obstruction filter, or repair
rule is not active QCKN knowledge merely because it exists in a notebook or
commit. It becomes active only after the corresponding promotion protocol is
satisfied.

That is the operational meaning of:

> **Never pay twice for a verified Collatz lesson.**
