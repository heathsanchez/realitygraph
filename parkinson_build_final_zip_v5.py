from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from realitygraph.submission_wrapper import build_submission

WORK = Path('/workspace')
DEFAULT_SOURCE = WORK / 'submission_t75r75_build'
DEFAULT_PATCH = WORK / 'parkinson_final_submission_v5'
DEFAULT_OUT = WORK / 'submission_final_v5.zip'


def main():
    parser = argparse.ArgumentParser(description='Wrap the retained T75_R75 submission with frozen G1+G2+V3 trajectory patch.')
    parser.add_argument('--source-dir', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--patch-dir', type=Path, default=DEFAULT_PATCH)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--already-parent', action='store_true', help='Use only if source main.py already applies exact frozen G1+G2.')
    args = parser.parse_args()

    source_main = args.source_dir / 'main.py'
    if not source_main.exists():
        raise FileNotFoundError(source_main)
    src = source_main.read_text(errors='ignore')
    markers = ('L_elong_q95', 'R_q90', '1.5314126014709473', '2.02439')
    marker_hits = [m for m in markers if m in src]
    if len(marker_hits) >= 2 and not args.already_parent:
        raise RuntimeError(
            'source main.py appears to contain G1/G2 markers; rerun with --already-parent only if it already applies the exact frozen G1+G2 corrections: '
            + ', '.join(marker_hits)
        )

    out = build_submission(
        args.source_dir,
        args.patch_dir,
        args.output,
        already_parent=args.already_parent,
    )
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        required = {'main.py', 'base_main.py', 'model.json', 'parkinson_runtime_patch.py'}
        missing = sorted(required - set(names))
        if missing:
            raise RuntimeError(f'final ZIP missing required files: {missing}')
        if not any(name.startswith('realitygraph/') for name in names):
            raise RuntimeError('final ZIP missing realitygraph package')

    print('FINAL_ZIP', out)
    print('SOURCE', args.source_dir)
    print('ALREADY_PARENT', int(args.already_parent))
    print('FILES', len(names))
    print('SIZE_BYTES', out.stat().st_size)
    print('READY_FOR_LOCAL_RUNTIME_CHECK')


if __name__ == '__main__':
    main()
