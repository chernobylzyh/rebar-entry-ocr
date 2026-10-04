"""仅CPU真实PDF几何验收，不调用OCR。使用新的输出目录。"""
import argparse
from pathlib import Path
from types import SimpleNamespace
from lab import render,preview,read_json,write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--pages',type=int,nargs='+',default=[2,3,5,6])
    p.add_argument('--template',default='template_entry_full.json')
    a=p.parse_args()
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for page in a.pages:
        folder=out/f'page_{page:03d}'
        render(SimpleNamespace(pdf=a.pdf,page=page,dpi=300,out=str(folder)))
        try:
            preview(SimpleNamespace(run=str(folder),template=a.template))
            g=read_json(folder/'geometry.json')
            reports.append({'page_no':page,'rows':len(g['ys'])-1,'columns':len(g['xs'])-1,'errors':g['geometry_errors'],'quad_page':g['quad_page']})
        except Exception as exc:
            reports.append({'page_no':page,'errors':[str(exc)]})
    write_json(out/'alignment_report.json',reports)
    if any(r['errors'] for r in reports):
        raise SystemExit('FAIL: see alignment_report.json')
    print('PASS: all requested pages passed geometry checks; OCR not tested.')


if __name__=='__main__':
    main()
