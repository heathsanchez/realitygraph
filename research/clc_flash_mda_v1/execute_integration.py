#!/usr/bin/env python3
"""Source-native RealityGraph CLC/MDA/FLASH finite integration versus independent batch.

Imports the frozen-existing RealityGraph modules (not vendored or rewritten).
The reference.py oracle deliberately imports nothing from RealityGraph.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

from reference import CAPS, OBSERVATIONS, STATES, TARGET, batch_state, test_reference_contracts

from realitygraph.capability import FiniteCapability
from realitygraph.developmental_core import route_residual, DevelopmentalRoute
from realitygraph.developmental_types import DevelopmentalResult, ResultKind
from realitygraph.flash import (
    CapabilityAdmissionEvent, CapabilityRevocationEvent, FlashClosure,
    FlashCompositionRule, FlashContract, FlashEventRuntime,
    FlashObstruction, ObstructionAdmissionEvent, ObstructionRevocationEvent,
    LiveObligation, ProtectedContinuation, FutureQuotient, PresentState,
)

AUTH = 'audit-omega-1'
CHECKER = 'audit-v1'
CONTRACT = FlashContract(AUTH, CHECKER)
WORK = ('oA', 'oB')


def cap(name: str, *, wrong=False, authority=AUTH) -> FiniteCapability:
    typin, typout, table, cost = CAPS[name]
    table = dict(table)
    if wrong:
        table[next(iter(table))] = 'wrong'
    return FiniteCapability(
        capability_id=name,
        input_type=typin,
        output_type=typout,
        semantics=tuple(sorted(table.items())),
        guard_inputs=tuple(sorted(table)),
        certificate_id=f'cert-{name}',
        dependencies=(),
        authority_snapshot=authority,
        verifier_id=CHECKER,
        provenance_ids=(f'source:{name}',),
        cost=cost,
    )


def cap_oracle(name: str) -> tuple[tuple[str,str], ...]:
    return tuple(sorted(CAPS[name][2].items()))


def obligation(ident: str) -> LiveObligation:
    return LiveObligation(
        obligation_id=ident, input_type=f'Target-{ident}',
        source_input_type='X', output_type='Z',
        oracle=(('t0','z0'),('t1','z1')),
        transport_to_source=(('t0','x0'),('t1','x1')),
        contract=CONTRACT,
        candidate_fingerprints=('bad','unused','correct'),
        domain=ident,
    )


def make_flash() -> tuple[FlashClosure,FlashEventRuntime]:
    composition = FlashCompositionRule('compose-f-g','f','g','h',
                                       (('x0','z0'),('x1','z1')),'cert-h')
    closure = FlashClosure(tuple(obligation(ident) for ident in WORK),
                           composition_rules=(composition,),
                           kernel='audit-v1-existing-flash')
    return closure, FlashEventRuntime(closure)


def apply_flash(runtime: FlashEventRuntime, event: str, eid: str) -> None:
    what, _, name = event.partition(':')
    if what == 'admit':
        runtime.apply(CapabilityAdmissionEvent(eid,cap(name),cap_oracle(name)))
    elif what == 'revoke':
        runtime.apply(CapabilityRevocationEvent(eid,name,'finite certified ablation'))
    elif what == 'obstruct':
        o = FlashObstruction(name,'X','Z',CONTRACT,'bad','x0','z0','wrong','counterexample')
        runtime.apply(ObstructionAdmissionEvent(eid,o))
    elif what == 'unobstruct':
        runtime.apply(ObstructionRevocationEvent(eid,name,'new evidence invalidates obstruction'))
    else:
        raise ValueError(event)


def compare_flash(closure:FlashClosure, source_events: tuple[str,...]) -> dict[str, object]:
    expected=batch_state(source_events)
    actual_ids=closure.active_capability_ids()
    discrepancies=[]
    if tuple(actual_ids)!=expected['active']:
        discrepancies.append({'dimension':'active_warrants','expected':expected['active'],'got':actual_ids})
    compiled=closure.compiled_present()
    restarted=compiled.restart()
    native_compiled=tuple(restarted.capability_graph.active_ids())
    if native_compiled!=actual_ids:
        discrepancies.append({'dimension':'compiled_restart','expected':actual_ids,'got':native_compiled})
    expected_pruned=expected['pruned']
    actual_best={}
    for oid in WORK:
        o=closure.obligations[oid]
        if o.status!=expected['status']:
            discrepancies.append({'dimension':'protected_outcome','obligation':oid,
                                  'expected':expected['status'],'got':o.status})
        if tuple(sorted(o.pruned_fingerprints))!=expected_pruned:
            discrepancies.append({'dimension':'negative_propagation','obligation':oid,
                                  'expected':expected_pruned,'got':tuple(sorted(o.pruned_fingerprints))})
        if o.status=='DISCHARGED':
            if o.solved_by not in expected['all_eligible']:
                discrepancies.append({'dimension':'invalid_active_solver','obligation':oid,
                                      'expected':expected['all_eligible'],'got':o.solved_by})
            if not o.worker_cancelled:
                discrepancies.append({'dimension':'cancellation','obligation':oid})
        else:
            if o.solved_by is not None or o.worker_cancelled:
                discrepancies.append({'dimension':'incomplete_reopening','obligation':oid,
                                      'solver':o.solved_by,'cancelled':o.worker_cancelled})
        if o.solved_by!=expected['best']:
            actual_best[oid]={'expected':expected['best'],'got':o.solved_by}
    return {'protected':discrepancies,'preference':actual_best,
            'expected_status':expected['status'],'active':list(actual_ids),
            'expected_best':expected['best']}


def ordered_traces(operations: tuple[str,...], precedence:dict[str,str]) -> tuple[tuple[str,...],...]:
    return tuple(row for row in itertools.permutations(operations)
                 if all(row.index(before)<row.index(after) for after,before in precedence.items()))


def capability_census() -> dict[str, object]:
    operations=('admit:f','admit:g','admit:alt','revoke:f','revoke:alt')
    traces=ordered_traces(operations,{'revoke:f':'admit:f','revoke:alt':'admit:alt'})
    assert len(traces)==30,len(traces)
    counters=Counter(); pref=[]; defects=[]; digester=hashlib.sha256()
    for tid,trace in enumerate(traces):
        closure,runtime=make_flash(); events=[]
        for seq,event in enumerate(trace):
            apply_flash(runtime,event,f'E{tid}-{seq}')
            events.append(event)
            verdict=compare_flash(closure,tuple(events))
            digester.update(json.dumps([tid,seq,event,verdict['expected_status'],verdict['active']],sort_keys=True).encode())
            counters['native_prefixes']+=1
            counters['protected_violations']+=len(verdict['protected'])
            counters['preference_disagreements']+=len(verdict['preference'])
            if verdict['protected']:
                defects.append({'trace':trace,'prefix':seq+1,'faults':verdict['protected']})
            if verdict['preference'] and len(pref)<8:
                pref.append({'trace':trace,'prefix':seq+1,'source_events':events[:],
                             'differences':verdict['preference']})
    return {'traces':len(traces),'counts':dict(counters),'first_protected_failures':defects[:5],
            'first_preference_disagreements':pref,'trace_sha256':digester.hexdigest()}


def future_census() -> dict[str, object]:
    operations=tuple(f'protect:{x}' for x in OBSERVATIONS)+tuple(f'unprotect:{x}' for x in OBSERVATIONS)
    precedence={f'unprotect:{x}':f'protect:{x}' for x in OBSERVATIONS}
    traces=ordered_traces(operations,precedence)
    assert len(traces)==90,len(traces)
    count=0;failures=[]; digester=hashlib.sha256()
    for tid,trace in enumerate(traces):
        q=FutureQuotient(tuple(PresentState(s,provenance_ids=(f'prior:{s}',)) for s in STATES),
                         authority_snapshot=AUTH,verifier_id=CHECKER)
        events=[]
        for seq,event in enumerate(trace):
            kind,_,name=event.partition(':')
            if kind=='protect':
                c=ProtectedContinuation(name,tuple(sorted(OBSERVATIONS[name].items())),AUTH,CHECKER)
                q.admit_continuation(c)
            else:q.revoke_continuation(name,reason='frozen protected test revoked')
            events.append(event)
            desired=batch_state(tuple(events))['classes']
            actual=q.classes()
            count+=1
            digester.update(json.dumps([tid,seq,event,actual],sort_keys=True).encode())
            if desired!=actual:
                failures.append({'trace':trace,'step':seq,'expected':desired,'got':actual})
    return {'traces':len(traces),'native_prefixes':count,'failures':failures[:8],
            'trace_sha256':digester.hexdigest()}


def native_controls()->dict[str, object]:
    closed,runtime=make_flash()
    assert closed.open_obligation_ids()==WORK
    try:
        apply_flash(runtime,'admit:missing','invalid')
        raise AssertionError('missing source unexpectedly admitted')
    except KeyError:pass
    bad=cap('alt',wrong=True)
    try:
        runtime.apply(CapabilityAdmissionEvent('bad-source',bad,cap_oracle('alt')))
        raise AssertionError('unverified mutation was admitted')
    except ValueError: pass
    assert not closed.capabilities
    # A third-party certificate may be active in its own scope, not in protected obligations.
    foreign=cap('f',authority='foreign')
    runtime.apply(CapabilityAdmissionEvent('foreign-source',foreign,cap_oracle('f')))
    assert closed.open_obligation_ids()==WORK
    # Revoke foreign before starting controlled causal branch; identity cannot be forged.
    runtime.apply(CapabilityRevocationEvent('foreign-revoke','f','foreign witness excluded'))
    cold,rr=make_flash()
    assert cold.open_obligation_ids()==WORK
    rr.apply(CapabilityAdmissionEvent('f-add',cap('f'),cap_oracle('f')))
    assert cold.open_obligation_ids()==WORK
    rr.apply(CapabilityAdmissionEvent('g-add',cap('g'),cap_oracle('g')))
    assert cold.discharged_obligation_ids()==WORK
    assert 'h' in cold.active_capability_ids()
    compiled=cold.compiled_present().restart()
    assert 'h' in compiled.capability_graph.active_ids()
    h = next(c for c in compiled.capability_graph.capabilities if c.capability_id=='h')
    assert h.execute('x0')=='z0' and h.execute('x1')=='z1'
    old_events=cold.event_count
    rr.apply(CapabilityAdmissionEvent('g-add',cap('g'),cap_oracle('g')))
    assert old_events==cold.event_count  # idempotent exact same event
    try:
        rr.apply(CapabilityAdmissionEvent('g-add',cap('alt'),cap_oracle('alt')))
        raise AssertionError('event replay mutated accepted event')
    except ValueError:pass
    assert old_events==cold.event_count
    rr.apply(CapabilityRevocationEvent('f-revoke','f','targeted cause ablated'))
    assert cold.open_obligation_ids()==WORK
    assert 'h' not in cold.active_capability_ids()
    rr.apply(CapabilityAdmissionEvent('new-role',cap('alt'),cap_oracle('alt')))
    assert cold.discharged_obligation_ids()==WORK
    # Requalifies with a different capability identity. Revoked f remains revoked.
    assert 'f' not in cold.active_capability_ids()
    unrelated=FlashObstruction('irrelevant','X','Z',CONTRACT,'out-of-grammar','x0','z0','wrong')
    rr.apply(ObstructionAdmissionEvent('irrelevant-add',unrelated))
    assert cold.discharged_obligation_ids()==WORK
    rr.apply(ObstructionRevocationEvent('irrelevant-rm','irrelevant','sham-retraction'))
    assert cold.discharged_obligation_ids()==WORK
    # Two distinct, valid supports: removing one cannot erase protected truth.
    supported, sr=make_flash()
    for ident in ('f','g','alt'):
        sr.apply(CapabilityAdmissionEvent('add-'+ident,cap(ident),cap_oracle(ident)))
    assert supported.discharged_obligation_ids()==WORK
    sr.apply(CapabilityRevocationEvent('revoke-f','f','ancestor removed'))
    assert supported.discharged_obligation_ids()==WORK
    assert all(supported.obligations[oid].solved_by=='alt' for oid in WORK)
    sr.apply(CapabilityRevocationEvent('revoke-alt','alt','second path removed'))
    assert supported.open_obligation_ids()==WORK
    # Foreign future (unbound authority) cannot split classes.
    q=FutureQuotient((PresentState('a'),PresentState('b'),PresentState('c')),
                     authority_snapshot=AUTH,verifier_id=CHECKER)
    try:
        q.admit_continuation(ProtectedContinuation('forge',tuple(sorted(OBSERVATIONS['p1'].items())),'wrong',CHECKER))
        raise AssertionError('forged protected continuation admitted')
    except ValueError:pass
    assert q.classes()==(('a','b','c'),)
    # Native MDA route gate: search and choice DO NOT license language growth.
    assert route_residual(DevelopmentalResult(ResultKind.UNKNOWN_SEARCH,'r')) is DevelopmentalRoute.SEARCH
    assert route_residual(DevelopmentalResult(ResultKind.UNKNOWN_CHOICE,'r')) is DevelopmentalRoute.EVIDENCE
    assert route_residual(DevelopmentalResult(ResultKind.UNKNOWN_IDENTITY,'r')) is DevelopmentalRoute.SPLIT
    try:
        route_residual(DevelopmentalResult(ResultKind.UNKNOWN_EXPRESSIVITY,'r',certificate_digest='any'))
        raise AssertionError('unsupported expressivity expansion admitted')
    except ValueError:pass
    return {'cold_open':2, 'retained_h_discharge':2,'after_ancestor_ablation_open':2,
            'fresh_role_restores':2,'two_support_fallback':2,
            'event_idempotence':True, 'event_identity_mutation_rejected':True,
            'unverified_candidate_rejected':True,'foreign_future_rejected':True,
            'MDA_unsupported_expand_rejected':True, 'sham_control_passed':True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='V1_RESULTS.json')
    parser.add_argument('--strict',action='store_true',help='Fail if any protected OR preference discrepancy')
    args=parser.parse_args()
    clc=test_reference_contracts()
    native=native_controls()
    c=capability_census();q=future_census()
    protected_ok=c['counts']['protected_violations']==0 and not q['failures']
    preferred_ok=c['counts']['preference_disagreements']==0
    result={
        'experiment':'CLC/MDA/FLASH finite source-level batch compatibility v1',
        'schema':'clc-mda-flash-reference-v1',
        'base_commit':'81deb459120de01a4fd6b686cf2ed260158dd766',
        'frozen_protocol_commit':'43d119e4a3c0134db9c536ac82b17b67b3315e3d',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'reference_sha256':hashlib.sha256((Path(__file__).with_name('reference.py')).read_bytes()).hexdigest(),
        'clc_finite_adapter':clc,'native_controls':native,
        'capability_census':c,'future_census':q,
        'protected_batch_equivalence':'PASS' if protected_ok else 'FAIL',
        'preference_batch_equivalence':'PASS' if preferred_ok else 'FAIL',
        'CLC_full_theorem':'NOT_PROVED','CLC_native_implementation':'ADAPTER_ONLY',
        'MDA_full_frontier_integration':'NOT_RUN',
        'external_domain_transfer':'NOT_RUN','agent_comparator':'NOT_RUN',
    }
    path=Path(args.output)
    path.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('protected_batch_equivalence','preference_batch_equivalence')}
                     |{'capability_prefixes':c['counts']['native_prefixes'],'future_prefixes':q['native_prefixes'],
                       'preference_disagreements':c['counts']['preference_disagreements'],
                       'result':str(path)},indent=2))
    if not protected_ok or (args.strict and not preferred_ok):
        sys.exit(1)

if __name__=='__main__': main()
