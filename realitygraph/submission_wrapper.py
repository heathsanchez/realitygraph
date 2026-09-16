from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


def wrapper_source(*, already_parent: bool) -> str:
    flag = 'True' if already_parent else 'False'
    return f'''from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from parkinson_runtime_patch import load_model, patch_probability

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path('/code_execution/data')
NIFTI_DIR = DATA_ROOT / 'niftis'
SUBMISSION_PATH = ROOT / 'submission.csv'
MODEL = load_model(ROOT / 'model.json')
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
            _nifti(uid), base_p, MODEL, already_parent=ALREADY_PARENT
        )

    if not df['is_pathologic'].between(0.0, 1.0).all():
        raise RuntimeError('patched probability outside [0,1]')
    df.to_csv(SUBMISSION_PATH, index=False)


if __name__ == '__main__':
    main()
'''


def build_submission(source_dir, patch_dir, output_zip, *, already_parent=False):
    source_dir = Path(source_dir)
    patch_dir = Path(patch_dir)
    output_zip = Path(output_zip)
    source_main = source_dir / 'main.py'
    if not source_main.exists():
        raise FileNotFoundError(source_main)
    for required in ('model.json', 'parkinson_runtime_patch.py'):
        if not (patch_dir / required).exists():
            raise FileNotFoundError(patch_dir / required)
    if not (patch_dir / 'realitygraph').is_dir():
        raise FileNotFoundError(patch_dir / 'realitygraph')

    build_dir = output_zip.with_suffix('')
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(source_dir, build_dir)

    original = build_dir / 'main.py'
    original.rename(build_dir / 'base_main.py')
    (build_dir / 'main.py').write_text(wrapper_source(already_parent=already_parent))

    shutil.copy2(patch_dir / 'model.json', build_dir / 'model.json')
    shutil.copy2(patch_dir / 'parkinson_runtime_patch.py', build_dir / 'parkinson_runtime_patch.py')
    target_pkg = build_dir / 'realitygraph'
    if target_pkg.exists():
        shutil.rmtree(target_pkg)
    shutil.copytree(patch_dir / 'realitygraph', target_pkg)

    if output_zip.exists():
        output_zip.unlink()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(build_dir.rglob('*')):
            if path.is_file():
                zf.write(path, path.relative_to(build_dir))
    return output_zip
