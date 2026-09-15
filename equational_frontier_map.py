from __future__ import annotations
import hashlib,json,re,urllib.request
from collections import Counter,defaultdict
from pathlib import Path
from equational_residual_demo import _read_corpus
from equational_transition_demo import _archive_files

COMMIT="bed33e36c33fca139d902addd8cb77cd4172fe64"
URL=f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
SHA="284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"

def dl():
 q=urllib.request.Request(URL,headers={"User-Agent":"RealityGraph/1.0 frontier-map"})
 with urllib.request.urlopen(q,timeout=90) as r: raw=r.read()
 if hashlib.sha256(raw).hexdigest()!=SHA: raise ValueError("archive hash mismatch")
 return raw

def verdict(t):
 m=re.search(r"-- Recorded verdict:\s*(true|false)",t)
 return m.group(1) if m else None

def family(t):
 if verdict(t)=="true": return "true_proof"
 body=t[max(t.rfind("-- Original submission body"),t.rfind("-- Aurora-accepted corrected submission body"),0):]
 if re.search(r"finOpTable\s+\"",body) or re.search(r"magmaFin\s+\d+\s*\[[0-9,\s]+\]",body,re.S):
  return "concrete_table"
 if re.search(r"affineOp_\d+_\d+_\d+_\d+",body): return "affine"
 if "noncomputable def eval" in body and ("inductive " in body or "structure " in body): return "free_completion"
 if "Magma Nat" in body or "Magma Int" in body: return "nat_int"
 if "ZMod" in body: return "zmod_or_algebraic"
 if "noncomputable" in body: return "noncomputable_other"
 if "decideFin!" in body: return "finite_computed"
 return "other"

def main():
 raw=dl(); rows,proofs,_,_,source_hashes,archive_hash=_read_corpus(raw)
 files=_archive_files(raw); by={str(r["id"]):r for r in rows}
 local={p.stem for p in Path("certificates").glob("*.lean")}
 current=sorted(set(by)-proofs-local)
 donors=defaultdict(Counter); donor_ids=defaultdict(lambda:defaultdict(list))
 for pid in sorted(proofs):
  row=by.get(pid); blob=files.get(f"proofs/{pid}.lean")
  if not row or not blob: continue
  fam=family(blob.decode("utf-8",errors="replace"))
  s=int(row["eq1_id"]); donors[s][fam]+=1
  if len(donor_ids[s][fam])<8: donor_ids[s][fam].append(pid)
 clusters=defaultdict(list)
 for pid in current: clusters[int(by[pid]["eq1_id"])].append(pid)
 ranking=[]
 for s,ids in clusters.items():
  ranking.append({
   "source_eq":s,"residual_count":len(ids),"residual_ids":ids[:30],
   "historical_mechanisms":dict(donors[s]),
   "donor_examples":dict(donor_ids[s]),
   "equation1":str(by[ids[0]]["equation1"])
  })
 ranking.sort(key=lambda x:(-x["residual_count"],x["source_eq"]))
 out={
  "experiment":"realitygraph-post-retention-frontier-map-v1",
  "upstream":{"commit":COMMIT,"archive_sha256":archive_hash,"dataset_sha256":source_hashes},
  "state":{"external_unsolved":len(set(by)-proofs),"local_retained":len(local & set(by)),
           "current_frontier":len(current),"current_source_clusters":len(clusters)},
  "top_clusters":ranking[:40],
  "cluster_size_histogram":dict(Counter(x["residual_count"] for x in ranking)),
 }
 print(json.dumps(out,indent=2,sort_keys=True))
 p=Path("results/equational-frontier-map-v1.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
