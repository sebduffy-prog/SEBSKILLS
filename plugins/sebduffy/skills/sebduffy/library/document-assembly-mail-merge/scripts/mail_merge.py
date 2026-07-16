#!/usr/bin/env python3
"""Batch mail-merge: one .docx template + a data source -> many personalised .docx.

Stdlib-only data readers (CSV, JSON). Requires `docxtpl` (pip install docxtpl).
Optional combine step requires `docxcompose`.

Usage:
    python3 mail_merge.py TEMPLATE.docx DATA.csv OUTDIR \
        [--name "{{last_name}}-offer.docx"] [--combine all.docx] [--dry-run]

The --name pattern uses the SAME {{field}} placeholders as your data columns.
Every field is available inside the Word template as {{ field }} (Jinja2).
"""
import argparse
import csv
import json
import os
import re
import sys

SAFE = re.compile(r'[^A-Za-z0-9._-]+')


def read_rows(path):
    """Return list[dict]. Supports .csv and .json (list of objects)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        with open(path, newline='', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    if ext == '.json':
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError('JSON data must be a list of objects (one per document).')
        return data
    raise ValueError(f'Unsupported data extension: {ext} (use .csv or .json)')


def fill_name(pattern, row, index):
    """Resolve {{field}} tokens in a filename pattern; fall back to row index."""
    def sub(m):
        return SAFE.sub('_', str(row.get(m.group(1).strip(), '')).strip())
    name = re.sub(r'\{\{\s*(.*?)\s*\}\}', sub, pattern)
    name = name.strip() or f'doc-{index:04d}.docx'
    if not name.lower().endswith('.docx'):
        name += '.docx'
    return name


def main(argv=None):
    ap = argparse.ArgumentParser(description='Batch docx mail-merge with docxtpl.')
    ap.add_argument('template', help='Path to the .docx template (Jinja2 tags inside).')
    ap.add_argument('data', help='Data source: .csv (header row) or .json (list of objects).')
    ap.add_argument('outdir', help='Output directory for generated docs.')
    ap.add_argument('--name', default='{{index}}.docx',
                    help='Output filename pattern using {{field}} tokens.')
    ap.add_argument('--combine', metavar='FILE.docx',
                    help='Also merge every output into one docx (needs docxcompose).')
    ap.add_argument('--dry-run', action='store_true',
                    help='Validate template + data and print planned filenames only.')
    args = ap.parse_args(argv)

    if not os.path.isfile(args.template):
        ap.error(f'Template not found: {args.template}')
    rows = read_rows(args.data)
    if not rows:
        ap.error('Data source contained zero rows.')
    os.makedirs(args.outdir, exist_ok=True)

    if args.dry_run:
        from docxtpl import DocxTemplate  # import validates it renders/parses
        DocxTemplate(args.template).get_undeclared_template_variables()
        for i, row in enumerate(rows):
            row.setdefault('index', i)
            print(fill_name(args.name, row, i))
        print(f'[dry-run] {len(rows)} document(s) planned from {args.data}', file=sys.stderr)
        return 0

    from docxtpl import DocxTemplate
    written = []
    for i, row in enumerate(rows):
        row.setdefault('index', i)
        doc = DocxTemplate(args.template)  # fresh instance per row (templates are stateful)
        doc.render(row)
        out = os.path.join(args.outdir, fill_name(args.name, row, i))
        doc.save(out)
        written.append(out)
    print(f'Wrote {len(written)} document(s) to {args.outdir}', file=sys.stderr)

    if args.combine:
        from docx import Document
        from docxcompose.composer import Composer
        master = Document(written[0])
        composer = Composer(master)
        for path in written[1:]:
            composer.append(Document(path))
        composer.save(args.combine)
        print(f'Combined {len(written)} docs -> {args.combine}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
