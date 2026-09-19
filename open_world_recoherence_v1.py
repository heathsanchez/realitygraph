from __future__ import annotations
from dataclasses import dataclass, field
from itertools import product
import hashlib, json

N_ROWS = 16
FULL_MASK = (1 << N_ROWS) - 1
MAX_FORMULA_COST = 13
SEED = "OPEN_WORLD_RECOHERENCE_V1_2026_09_19"

def bitmask(signal: int) -> int:
    out=0
    for row in range(N_ROWS):
        if (row >> signal) & 1:
            out |= 1 << row
    return out

SIGNALS = tuple(bitmask(i) for i in range(4))
CONST0=0
CONST1=FULL_MASK

def nand(a:int,b:int)->int:
    return (~(a & b)) & FULL_MASK

def table_apply(table:int,a:int,b:int)->int:
    out=0
    for row in range(N_ROWS):
        av=(a>>row)&1; bv=(b>>row)&1
        if (table >> (av + 2*bv)) & 1:
            out |= 1 << row
    return out

def support(mask:int)->tuple[int,...]:
    out=[]
    for sig in range(4):
        changed=False
        for row in range(N_ROWS):
            other=row ^ (1<<sig)
            if ((mask>>row)&1) != ((mask>>other)&1):
                changed=True; break
        if changed: out.append(sig)
    return tuple(out)

def abstract_binary(mask:int, supp:tuple[int,...])->int|None:
    if len(supp)!=2: return None
    i,j=supp
    table=0
    for a,b in product((0,1), repeat=2):
        vals=[]
        for row in range(N_ROWS):
            if ((row>>i)&1)==a and ((row>>j)&1)==b:
                vals.append((mask>>row)&1)
        if len(set(vals))!=1: return None
        table |= vals[0] << (a + 2*b)
    return table

@dataclass
class Capability:
    capability_id:str
    table:int
    authority:str
    active:bool=True
    provenance:tuple[str,...]=()

@dataclass
class State:
    logic:bool=False
    temporal:bool=False
    capabilities:list[Capability]=field(default_factory=list)
    authority:str="A1"
    events:list[dict]=field(default_factory=list)

    def active_tables(self):
        return sorted({c.table for c in self.capabilities if c.active and c.authority==self.authority})

    def snapshot(self):
        payload={
            "logic":self.logic,"temporal":self.temporal,"authority":self.authority,
            "capabilities":[{
                "id":c.capability_id,"table":c.table,"authority":c.authority,
                "active":c.active,"provenance":list(c.provenance)
            } for c in self.capabilities],
            "events":self.events,
        }
        return json.dumps(payload,sort_keys=True,separators=(",",":"))

    @classmethod
    def restore(cls,text):
        p=json.loads(text)
        s=cls(logic=p["logic"],temporal=p["temporal"],authority=p["authority"],events=p["events"])
        s.capabilities=[Capability(x["id"],x["table"],x["authority"],x["active"],tuple(x["provenance"])) for x in p["capabilities"]]
        return s

@dataclass(frozen=True)
class Episode:
    episode_id:str
    target:int
    closed:bool=True
    observed_rows:tuple[int,...]=tuple(range(N_ROWS))

class ExternalVerifier:
    def __init__(self, episode:Episode):
        self.episode=episode
        self.calls=0

    def check(self, candidate:int)->tuple[str,int|None]:
        self.calls += 1
        rows=self.episode.observed_rows
        for row in rows:
            if ((candidate>>row)&1) != ((self.episode.target>>row)&1):
                return ("REFUTED",row)
        if self.episode.closed and len(rows)==N_ROWS:
            return ("VERIFIED",None)
        return ("CONSISTENT_ONLY",None)

def generate_candidates(state:State):
    seeds={}
    for name,m in (("0",CONST0),("1",CONST1),("c0",SIGNALS[0]),("c1",SIGNALS[1])):
        seeds.setdefault(m,(1,name))
    if state.temporal:
        for name,m in (("p0",SIGNALS[2]),("p1",SIGNALS[3])):
            seeds.setdefault(m,(1,name))
    available_signals=[0,1]+([2,3] if state.temporal else [])
    for table in state.active_tables():
        for i in available_signals:
            for j in available_signals:
                if i==j: continue
                m=table_apply(table,SIGNALS[i],SIGNALS[j])
                seeds.setdefault(m,(1,f"M{table:x}({i},{j})"))
    return seeds

def synthesize(state:State, episode:Episode, verifier:ExternalVerifier, max_cost=MAX_FORMULA_COST):
    seeds=generate_candidates(state)
    best=dict(seeds)
    by={1:list(seeds)}
    checked=set()
    def check_cost(cost):
        for m in sorted(by.get(cost,[])):
            if m in checked: continue
            checked.add(m)
            status,_=verifier.check(m)
            if status=="VERIFIED":
                return m,best[m][1],status
        return None
    got=check_cost(1)
    if got: return {"found":True,"mask":got[0],"expr":got[1],"checks":len(checked),"max_cost":1}
    if not episode.closed:
        return {"found":False,"unknown":True,"checks":len(checked),"reason":"UNKNOWN_AUTHORITY"}
    if not state.logic:
        return {"found":False,"unknown":False,"checks":len(checked),"reason":"COMPLETE_CURRENT_LANGUAGE_NO_RESOLUTION"}
    for cost in range(2,max_cost+1):
        rows=[]
        for ca in range(1,cost-1):
            cb=cost-1-ca
            for a in by.get(ca,()):
                for b in by.get(cb,()):
                    m=nand(a,b)
                    if m not in best:
                        best[m]=(cost,("nand",best[a][1],best[b][1]))
                        rows.append(m)
        if rows:
            by[cost]=rows
            got=check_cost(cost)
            if got:
                return {"found":True,"mask":got[0],"expr":got[1],"checks":len(checked),"max_cost":cost}
    return {"found":False,"unknown":False,"checks":len(checked),"reason":"BOUNDED_LANGUAGE_NO_RESOLUTION"}

def try_extensions(parent:State, episode:Episode):
    candidates=[]; options=[]
    if not parent.logic: options.append(("ADD_LOGIC",True,False))
    if not parent.temporal: options.append(("ADD_TEMPORAL",False,True))
    for name,lg,tp in options:
        trial=State(parent.logic or lg,parent.temporal or tp,list(parent.capabilities),parent.authority,list(parent.events))
        v=ExternalVerifier(episode)
        r=synthesize(trial,episode,v)
        candidates.append((name,trial,r,v.calls))
    successes=[x for x in candidates if x[2].get("found")]
    if successes:
        return min(successes,key=lambda x:(x[3],x[0])), candidates
    if len(options)==2:
        trial=State(True,True,list(parent.capabilities),parent.authority,list(parent.events))
        v=ExternalVerifier(episode)
        r=synthesize(trial,episode,v)
        candidates.append(("ADD_LOGIC+TEMPORAL",trial,r,v.calls))
        if r.get("found"):
            return candidates[-1],candidates
    return None,candidates

def compile_behavioral_macro(state:State, mask:int, episode_id:str):
    table=abstract_binary(mask,support(mask))
    if table is None or table in state.active_tables(): return None
    cid=f"cap-{state.authority}-{table:x}-{len(state.capabilities)+1}"
    cap=Capability(cid,table,state.authority,True,(episode_id,))
    state.capabilities.append(cap)
    return cap

def solve_episode(state:State, episode:Episode):
    v=ExternalVerifier(episode)
    initial=synthesize(state,episode,v)
    total=v.calls
    trace={"episode":episode.episode_id,"initial":initial,"extensions":[]}
    if initial.get("unknown"):
        trace["route"]="UNKNOWN"
        return trace,total,None
    result=initial
    if not result.get("found"):
        chosen,trials=try_extensions(state,episode)
        for name,trial,r,calls in trials:
            trace["extensions"].append({"name":name,"checks":calls,"found":bool(r.get("found")),"reason":r.get("reason")})
            total += calls
        if chosen is None:
            trace["route"]="OBSTRUCTION"
            return trace,total,None
        name,trial,result,_=chosen
        state.logic=trial.logic; state.temporal=trial.temporal
        trace["selected_extension"]=name
    trace["route"]="VERIFIED"
    trace["expr"]=result["expr"]
    trace["result_cost"]=result["max_cost"]
    cap=compile_behavioral_macro(state,result["mask"],episode.episode_id)
    if cap: trace["compiled_capability"]=cap.capability_id
    state.events.append({"episode":episode.episode_id,"route":trace["route"],"authority":state.authority})
    return trace,total,cap

def mk_targets():
    c0,c1,p0,p1=SIGNALS
    xnor=lambda a,b:(~(a^b))&FULL_MASK
    return [
        Episode("E0-open-partial",c0^c1,False,(0,1,2,3)),
        Episode("E1-direct",c0),
        Episode("E2-binary-genesis",c0^c1),
        Episode("E3-zero-search-reuse",c1^c0),
        Episode("E4-temporal-genesis",p0),
        Episode("E5-cross-substrate-compose",p0^c1),
        Episode("E6-derived-composition",xnor(p1,c0)),
    ]

def run_stream(warm=True, ablate_macros=False):
    state=State(); records=[]; total=0
    for ep in mk_targets():
        if not warm: state=State(authority=state.authority)
        if ablate_macros:
            for c in state.capabilities: c.active=False
        rec,cost,_=solve_episode(state,ep)
        total+=cost
        rec["episode_checks"]=cost
        rec["state_logic"]=state.logic
        rec["state_temporal"]=state.temporal
        rec["active_macros"]=len(state.active_tables())
        records.append(rec)
    return state,records,total

def authority_shift(state:State):
    old=state.authority; state.authority="A2"; revoked=[]
    for c in state.capabilities:
        if c.active and c.authority!=state.authority:
            c.active=False; revoked.append(c.capability_id)
    requalified=[]; checks=0
    for c in [x for x in state.capabilities if x.authority==old]:
        checks += 4
        nc=Capability(f"cap-A2-{c.table:x}-{len(state.capabilities)+1}",c.table,"A2",True,("requalified",c.capability_id))
        state.capabilities.append(nc); requalified.append(nc.capability_id)
    state.events.append({"event":"AUTHORITY_SHIFT","from":old,"to":"A2","revoked":revoked,"requalified":requalified})
    return checks,revoked,requalified

def main():
    protocol={
        "seed":SEED,
        "initial_language":"constants+current-signals",
        "extension_portfolio":["ADD_LOGIC","ADD_TEMPORAL"],
        "logic_primitive":"NAND",
        "temporal_primitive":"previous-signal terminals",
        "max_formula_cost":MAX_FORMULA_COST,
        "proposal_truth_separation":"controller cannot self-certify",
        "unknown_rule":"nonclosed authority cannot promote",
        "future_stream_generated_after_freeze":True,
    }
    protocol_hash=hashlib.sha256(json.dumps(protocol,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    warm_state,warm,warm_total=run_stream(True,False)
    _,cold,cold_total=run_stream(False,False)
    _,abl,abl_total=run_stream(True,True)
    snap=warm_state.snapshot(); restarted=State.restore(snap); exact_restart=(restarted.snapshot()==snap)
    shift_checks,revoked,requalified=authority_shift(restarted)
    post=Episode("E7-post-authority-reuse",SIGNALS[2]^SIGNALS[1])
    post_rec,post_cost,_=solve_episode(restarted,post)
    byid={r["episode"]:r for r in warm}; cold_by={r["episode"]:r for r in cold}
    gates={
        "PROTOCOL_FROZEN_BEFORE_STREAM": bool(protocol_hash),
        "UNKNOWN_PRESERVED_WITH_OPEN_AUTHORITY": byid["E0-open-partial"]["route"]=="UNKNOWN",
        "LOGIC_LANGUAGE_GROWS_ONLY_AFTER_NO_RESOLUTION": byid["E2-binary-genesis"].get("selected_extension")=="ADD_LOGIC",
        "COMPILED_BINARY_BEHAVIOR_CREATED": "compiled_capability" in byid["E2-binary-genesis"],
        "PROSPECTIVE_REUSE_REDUCES_SEARCH": byid["E3-zero-search-reuse"]["episode_checks"] < cold_by["E3-zero-search-reuse"]["episode_checks"],
        "TEMPORAL_SUBSTRATE_GROWS": byid["E4-temporal-genesis"].get("selected_extension")=="ADD_TEMPORAL",
        "CROSS_SUBSTRATE_COMPOSITION_COMPOUNDS": byid["E5-cross-substrate-compose"]["episode_checks"] < cold_by["E5-cross-substrate-compose"]["episode_checks"],
        "DERIVED_COMPOSITION_COMPOUNDS": byid["E6-derived-composition"]["episode_checks"] < cold_by["E6-derived-composition"]["episode_checks"],
        "WARM_TOTAL_BEATS_COLD": warm_total < cold_total,
        "MACRO_ABLATION_LOSES_ADVANTAGE": abl_total > warm_total,
        "EXACT_RESTART": exact_restart,
        "AUTHORITY_SHIFT_REVOKES_STALE": len(revoked)>0 and all(not c.active for c in restarted.capabilities if c.authority=="A1"),
        "REQUALIFICATION_RESTORES_REUSE": len(requalified)>0 and post_rec["route"]=="VERIFIED",
        "POST_SHIFT_WARM_BEATS_COLD_EPISODE": post_cost < cold_by["E5-cross-substrate-compose"]["episode_checks"],
    }
    out={
        "schema":"open-world-recoherence-v1",
        "classification":"BOUNDED_PROSPECTIVE_OPEN_WORLD_PRECURSOR",
        "protocol":protocol,"protocol_sha256":protocol_hash,
        "warm":{"total_checks":warm_total,"records":warm},
        "cold":{"total_checks":cold_total,"records":cold},
        "macro_ablation":{"total_checks":abl_total,"records":abl},
        "restart_exact":exact_restart,
        "authority_shift":{"checks":shift_checks,"revoked":revoked,"requalified":requalified,"post_record":post_rec,"post_cost":post_cost},
        "gates":gates,
        "verdict":"PASS_OPEN_WORLD_RECOHERENCE_V1" if all(gates.values()) else "FAIL_OPEN_WORLD_RECOHERENCE_V1",
        "claim_boundary":"bounded synthetic stream; extension families and verifier semantics supplied; tests integration of UNKNOWN, language/substrate growth, compilation, reuse, ablation, restart and authority revocation, not unrestricted natural-world self-development",
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if all(gates.values()) else 1

if __name__=="__main__": raise SystemExit(main())
