#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

DEFAULT_ITEMS_DIR = Path('/home/erickesc/data/platform_v2/items/by_id')
DEFAULT_OUT_DIR = Path('/home/erickesc/repos/blog_web/src/content/blog/generated')
DEFAULT_STAGE_ALLOW = 'draft,ready'


@dataclass
class BlogItem:
    item_id: str
    stage: str
    created_at: str
    title: str
    markdown: str
    topic: str
    use_case: str
    sources: list[str]


def slugify(text: str) -> str:
    s = (text or '').strip().lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s[:120] or 'post'


def parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime(1970, 1, 1, tzinfo=UTC)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)


def build_summary(markdown: str, max_len: int = 180) -> str:
    lines = [ln.strip() for ln in markdown.splitlines() if ln.strip()]
    text = ' '.join(lines)
    text = re.sub(r'[#>*_`\-\[\]\(\)]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + '…'


def load_item(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def to_blog_item(data: dict[str, Any], allow_stages: set[str]) -> BlogItem | None:
    if data.get('source_type') != 'owned.blog.post':
        return None
    stage = str(data.get('stage') or '').strip().lower()
    if stage not in allow_stages:
        return None

    item_id = str(data.get('id') or '').strip()
    ts = data.get('timestamps') or {}
    artifacts = data.get('artifacts') or {}
    enrich = data.get('editorial_enrichment') or {}
    lineage = data.get('lineage') or {}

    created_at = str(ts.get('created_at') or '')
    title = str(artifacts.get('title') or '').strip()
    markdown = str(artifacts.get('content_markdown') or '').strip()

    topic = str(((enrich.get('topic') or {}).get('primary')) or '')
    use_case = str(((enrich.get('use_case') or {}).get('primary')) or '')
    sources = [str(x) for x in ((lineage.get('derived_from_item_ids') or []) if isinstance(lineage.get('derived_from_item_ids'), list) else [])]

    if not item_id or not title or not markdown:
        return None

    return BlogItem(
        item_id=item_id,
        stage=stage,
        created_at=created_at,
        title=title,
        markdown=markdown,
        topic=topic,
        use_case=use_case,
        sources=sources,
    )


def render_markdown(item: BlogItem) -> str:
    slug = f"{slugify(item.title)}-{item.item_id[-6:]}"
    summary = build_summary(item.markdown)

    fm = {
        'title': item.title,
        'description': summary,
        'pubDate': item.created_at or datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'canonical_id': item.item_id,
        'stage': item.stage,
        'topic': item.topic,
        'use_case': item.use_case,
        'sources': item.sources,
    }

    lines = ['---']
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f'{k}:')
            for it in v:
                lines.append(f'  - "{it}"')
        else:
            safe = str(v).replace('"', "'")
            lines.append(f'{k}: "{safe}"')
    lines.append('---')
    lines.append('')
    lines.append(item.markdown.strip())
    lines.append('')

    return slug, '\n'.join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description='Sync platform_v2 owned.blog.post items into Astro markdown posts')
    ap.add_argument('--items-dir', default=str(DEFAULT_ITEMS_DIR))
    ap.add_argument('--out-dir', default=str(DEFAULT_OUT_DIR))
    ap.add_argument('--stage-allow', default=DEFAULT_STAGE_ALLOW, help='Comma-separated allowed stages (default: draft,ready)')
    ap.add_argument('--limit', type=int, default=0, help='Optional max items to export (0 = no limit)')
    ap.add_argument('--item-id', default='', help='Optional specific platform_v2 item id to export (e.g. ci_v1_blog_xxx)')
    args = ap.parse_args()

    items_dir = Path(args.items_dir)
    out_dir = Path(args.out_dir)
    allow_stages = {s.strip().lower() for s in str(args.stage_allow).split(',') if s.strip()}

    if not items_dir.exists():
        raise SystemExit(f'items_dir_not_found:{items_dir}')

    out_dir.mkdir(parents=True, exist_ok=True)

    found = 0
    exported = 0

    if args.item_id:
        files = [items_dir / f"{args.item_id}.json"]
    else:
        files = sorted(items_dir.glob('ci_v1_blog_*.json'))
    for fp in files:
        data = load_item(fp)
        if not data:
            continue
        item = to_blog_item(data, allow_stages)
        if not item:
            continue
        found += 1

        slug, body = render_markdown(item)
        target = out_dir / f'{slug}.md'
        target.write_text(body, encoding='utf-8')
        exported += 1

        if args.limit and exported >= args.limit:
            break

    print(json.dumps({
        'ok': True,
        'found': found,
        'exported': exported,
        'items_dir': str(items_dir),
        'out_dir': str(out_dir),
        'allowed_stages': sorted(allow_stages),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
