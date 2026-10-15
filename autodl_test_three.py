"""Run the three supplied PDFs sequentially, upstream only; preserve all runs."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED


CASES = [('steel01', '0814钢筋01.pdf'), ('steel02', '0814钢筋02.pdf'),
         ('steel1206', '2025.12.6日钢筋报审表.pdf')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--device', default='gpu:0')
    parser.add_argument('--model-cache', type=Path, default=Path('/root/.paddlex'))
    parser.add_argument('--out', type=Path, help='Must not exist; default is a new timestamped runs directory')
    parser.add_argument('--dry-run', action='store_true', help='Validate inputs and print commands without running OCR')
    args = parser.parse_args()
    project = Path(__file__).resolve().parent
    source = args.data_dir.resolve()
    missing = [str(source/name) for _, name in CASES if not (source/name).is_file()]
    if missing:
        parser.error('PDF files missing: ' + ', '.join(missing))
    output = (args.out or project/'runs'/('autodl_v2_'+datetime.now().strftime('%Y%m%d_%H%M%S')
                                        +'_'+uuid4().hex[:6])).resolve()
    commands = [(key, [sys.executable, '-u', '-m', 'material_ocr.worker', 'inspection',
                      '--pdf', str(source/name), '--out', str(output/key),
                      '--device', args.device, '--model-cache', str(args.model_cache.resolve()),
                      '--layout', 'adaptive']) for key, name in CASES]
    if args.dry_run:
        for key, command in commands:
            print(key, json.dumps(command, ensure_ascii=False))
        return 0
    import material_ocr
    if not Path(material_ocr.__file__).resolve().is_relative_to(project/'src'):
        parser.error('The active environment imports another checkout. Run: python -m pip install --no-deps -e .')
    output.mkdir(parents=True, exist_ok=False)
    (output/'logs').mkdir()
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1', OMP_NUM_THREADS='1',
               PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK='True')
    summaries = []
    for key, command in commands:
        print(f'\n===== {key}: upstream PDF test =====', flush=True)
        start = time.perf_counter()
        with (output/'logs'/f'{key}.log').open('w', encoding='utf-8') as log:
            log.write('COMMAND '+json.dumps(command, ensure_ascii=False)+'\n')
            log.flush()
            with subprocess.Popen(command, cwd=project, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace') as process:
                for line in process.stdout:
                    print(line, end='', flush=True)
                    log.write(line); log.flush()
                exit_code = process.wait()
        summary = {'case': key, 'exit_code': exit_code,
                   'elapsed_seconds': round(time.perf_counter()-start, 2)}
        try:
            records = json.loads((output/key/'records_all_pages.json').read_text(encoding='utf-8'))
            forms = json.loads((output/key/'submission_forms.json').read_text(encoding='utf-8'))
            summary.update(target_pages=records['target_pages'], submission_pages=forms['submission_pages'],
                record_count=len(records['records']),
                entry_needs_review_count=sum(r['status']=='needs_review' for r in records['records']),
                extraction_failure_count=len(records['extraction_failures']),
                submission_failure_count=len(forms['failures']))
        except (OSError, ValueError, KeyError) as exc:
            summary['result_read_error'] = str(exc)
        summaries.append(summary)
        (output/'test_summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    archive = output/'results_for_review.zip'
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as zip_file:
        files = [output/'test_summary.json', *(output/'logs').glob('*.log')]
        files += [output/key/name for key, _ in CASES
                  for name in ('page_index.json', 'records_all_pages.json', 'submission_forms.json')]
        for path in files:
            if path.is_file():
                zip_file.write(path, path.relative_to(output).as_posix())
    print(f'\n下载此文件发回复核：{archive}', flush=True)
    return int(any(s['exit_code'] or s.get('result_read_error') or s.get('extraction_failure_count')
                   or s.get('submission_failure_count') for s in summaries))


if __name__ == '__main__':
    raise SystemExit(main())
