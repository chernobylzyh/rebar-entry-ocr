"""V6小范围测试：只读已有序号图片，不重扫PDF，不改旧结果。"""
import argparse
from pathlib import Path
from lab import create_ocr,load_image,ocr_cell,write_json
from cell_ocr import FixedCellOCR
from row_retry import needs_retry,retry_row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--images',nargs='+',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--device',default='gpu:0')
    args=p.parse_args()
    paths=[Path(s) for s in args.images]
    if any(not path.is_file() for path in paths):
        raise ValueError('Input cell image does not exist')
    if len({path.stem for path in paths})!=len(paths):
        raise ValueError('Input filenames must have distinct stems')
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    engine=FixedCellOCR(create_ocr(args.device),args.device)
    report=[]
    for path in paths:
        folder=out/path.stem
        folder.mkdir()
        crop=load_image(path)
        text,blocks=ocr_cell(engine,crop,folder/path.name)
        retry=None
        if needs_retry(text,blocks,.95):
            retry=retry_row(engine,crop,text,folder/'retries',path.stem,.95,ocr_cell,direct=engine.direct_ocr)
        selected=retry['selected_text'] if retry and retry['selected_text'] is not None else text
        report.append({'input':str(path),'initial_text':text,'initial_blocks':blocks,
                       'retry':retry,'effective_text':selected,'human_verified':False})
        write_json(out/'cell_report.json',report)
        print(f'{path.stem}: initial={text!r}; effective={selected!r}; retry={retry["status"] if retry else "not_needed"}',flush=True)
    print(f'Review {out}/cell_report.json and *_rec_input_*.png')


if __name__=='__main__':
    main()
