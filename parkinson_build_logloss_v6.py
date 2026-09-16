from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

WORK = Path('/workspace')
ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = WORK / 'submission_t75r75_build'
DEFAULT_V5_PATCH = WORK / 'parkinson_final_submission_v5'
DEFAULT_META = WORK / 'parkinson_logloss_v6' / 'logloss_model.json'
DEFAULT_OUT = WORK / 'submission_final_logloss_v6.zip'


def wrapper_source(*, already_parent=False):
    flag = 'True' if already_parent else 'False'
    return f'''from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from parkinson_runtime_logloss_patch import load_meta_model, patch_probability
from parkinson_runtime_patch import load_model

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path('/code_execution/data')
NIFTI_DIR = DATA_ROOT / 'niftis'
SUBMISSION_PATH = ROOT / 'submission.csv'
V5_MODEL = load_model(ROOT / 'model.json')
META_MODEL = load_meta_model(ROOT / 'logloss_model.json')
ALREADY_PARENT = {flag}


def _nifti(uid: str) -> Path:
    gz = NIFTI_DIR / f'{{uid}}.nii.gz'
    if gz.exists():
        return gz
    nii = NIFTI_DIR / f'{{uid}}.nii'
    if nii.exists():
        return nii
    raise FileNotFoundError(f'missing NIfTI for {{uid}}')


def main():
    subprocess.run([sys.executable, str(ROOT / 'base_main.py')], cwd=ROOT, check=True)
    if not SUBMISSION_PATH.exists():
        raise FileNotFoundError('base submission did not write submission.csv')

    df = pd.read_csv(SUBMISSION_PATH)
    if 'is_pathologic' not in df.columns:
        raise RuntimeError('submission.csv missing is_pathologic column')
    if 'uid' in df.columns:
        uid_col = 'uid'
    else:
        uid_col = df.columns[0]
        if str(uid_col).startswith('Unnamed:'):
            df = df.rename(columns={{uid_col: 'uid'}})
            uid_col = 'uid'

    for i in range(len(df)):
        uid = str(df.iloc[i][uid_col])
        base_p = float(df.iloc[i]['is_pathologic'])
        if not (0.0 <= base_p <= 1.0):
            raise RuntimeError('base probability outside [0,1]')
        df.at[df.index[i], 'is_pathologic'] = patch_probability(
            _nifti(uid), base_p, V5_MODEL, META_MODEL,
            already_parent=ALREADY_PARENT,
        )

    if not df['is_pathologic'].between(0.0, 1.0).all():
        raise RuntimeError('patched probability outside [0,1]')
    df.to_csv(SUBMISSION_PATH, index=False)


if __name__ == '__main__':
    main()
'''


def main():
    parser = argparse.ArgumentParser(description='Build the V6 log-loss-optimized competition submission.')
    parser.add_argument('--source-dir', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--v5-patch-dir', type=Path, default=DEFAULT_V5_PATCH)
    parser.add_argument('--meta-model', type=Path, default=DEFAULT_META)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--already-parent', action='store_true')
    args = parser.parse_args()

    source_main = args.source_dir / 'main.py'
    if not source_main.exists():
        raise FileNotFoundError(source_main)
    for required in ('model.json', 'parkinson_runtime_patch.py'):
        if not (args.v5_patch_dir / required).exists():
            raise FileNotFoundError(args.v5_patch_dir / required)
    if not (args.v5_patch_dir / 'realitygraph').is_dir():
        raise FileNotFoundError(args.v5_patch_dir / 'realitygraph')
    if not args.meta_model.exists():
        raise FileNotFoundError(args.meta_model)

    src = source_main.read_text(errors='ignore')
    markers = ('L_elong_q95', 'R_q90', '1.5314126014709473', '2.02439')
    marker_hits = [m for m in markers if m in src]
    if len(marker_hits) >= 2 and not args.already_parent:
        raise RuntimeError(
            'source main.py appears to contain G1/G2 markers; rerun with --already-parent only if exact frozen G1+G2 are already applied: '
            + ', '.join(marker_hits)
        )

    build_dir = args.output.with_suffix('')
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(args.source_dir, build_dir)

    (build_dir / 'main.py').rename(build_dir / 'base_main.py')
    (build_dir / 'main.py').write_text(wrapper_source(already_parent=args.already_parent))

    shutil.copy2(args.v5_patch_dir / 'model.json', build_dir / 'model.json')
    shutil.copy2(args.v5_patch_dir / 'parkinson_runtime_patch.py', build_dir / 'parkinson_runtime_patch.py')
    target_pkg = build_dir / 'realitygraph'
    if target_pkg.exists():
        shutil.rmtree(target_pkg)
    shutil.copytree(args.v5_patch_dir / 'realitygraph', target_pkg)

    shutil.copy2(args.meta_model, build_dir / 'logloss_model.json')
    shutil.copy2(ROOT / 'parkinson_runtime_logloss_patch.py', build_dir / 'parkinson_runtime_logloss_patch.py')
    shutil.copy2(ROOT / 'realitygraph' / 'logloss_meta.py', target_pkg / 'logloss_meta.py')

    if args.output.exists():
        args.output.unlink()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(build_dir.rglob('*')):
            if path.is_file():
                zf.write(path, path.relative_to(build_dir))

    with zipfile.ZipFile(args.output) as zf:
        names = set(zf.namelist())
        required = {
            'main.py', 'base_main.py', 'model.json', 'logloss_model.json',
            'parkinson_runtime_patch.py', 'parkinson_runtime_logloss_patch.py',
            'realitygraph/logloss_meta.py',
        }
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f'V6 ZIP missing required files: {missing}')

    print('FINAL_LOGLOSS_ZIP', args.output)
    print('SOURCE', args.source_dir)
    print('META_MODEL', args.meta_model)
    print('ALREADY_PARENT', int(args.already_parent))
    print('SIZE_BYTES', args.output.stat().st_size)
    print('READY_FOR_LOCAL_RUNTIME_CHECK')


if __name__ == '__main__':
    main()
