#!/usr/bin/env python3
"""arxiv_search.py — arXiv API 客户端。

CLI: python3 arxiv_search.py --keywords "..." [--limit 10] [--ipc IPC] [--output-json path]

- 无需 API key
- 单次调用一次请求；批量调用方负责限速（arXiv 建议 ≥3s 一次）
- 重试：5xx/timeout 退避 3s 重试 1 次；429 退避 6s 重试 1 次；仍失败则记 error
- IPC：arXiv 不支持 IPC 限定，参数被记录但不影响 query；结果 ipc_supported=False
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree as ET


API_BASE = "https://export.arxiv.org/api/query"
RETRY_BACKOFF_5XX = 3
RETRY_BACKOFF_429 = 6
# 注:本模块不在 search() 内做 inter-call 限速。批量调用方(如 N8 串行多次 search)
# 必须自行 sleep ≥3s,按 arXiv 官方建议 (https://info.arxiv.org/help/api/tou.html)。


def _urlopen(url, timeout=30):
    """Wrapped for monkey-patching in tests."""
    return urlopen(url, timeout=timeout)


def _sleep(secs):
    """Wrapped for monkey-patching in tests."""
    time.sleep(secs)


def parse_atom(xml_text: str) -> list:
    """解析 arXiv Atom feed → SearchHit dict 列表。"""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    hits = []
    root = ET.fromstring(xml_text)
    for entry in root.findall("a:entry", ns):
        id_elem = entry.find("a:id", ns)
        title_elem = entry.find("a:title", ns)
        summary_elem = entry.find("a:summary", ns)
        published_elem = entry.find("a:published", ns)
        link_elem = entry.find("a:link[@rel='alternate']", ns)

        full_id = (id_elem.text or "").strip() if id_elem is not None else ""
        # http://arxiv.org/abs/2109.00672v1 → "2109.00672v1"
        identifier = full_id.rsplit("/", 1)[-1] if full_id else ""

        hits.append({
            "title": (title_elem.text or "").strip() if title_elem is not None else "",
            "abstract": (summary_elem.text or "").strip() if summary_elem is not None else "",
            "identifier": identifier,
            "url": (link_elem.get("href") if link_elem is not None else full_id) or full_id,
            "publish_date": (published_elem.text or "").strip() if published_elem is not None else None,
            "source_type": "arxiv-api",
            "ipc": None,
            "applicant": None,
            "raw": {},
        })
    return hits


class ArxivClient:
    source_type = "arxiv-api"
    ipc_supported = False
    assignee_supported = False

    def search(self, keywords: str, ipc: Optional[str] = None,
               assignee: Optional[str] = None, limit: int = 10) -> dict:
        """返回 SearchResult dict（与 spec §2.2 结构一致，省略未用字段）。"""
        params = {
            "search_query": f"all:{keywords}",
            "max_results": str(limit),
        }
        url = f"{API_BASE}?{urlencode(params)}"
        started_at = time.time()

        # 重试一次：5xx / 429 / URLError → 退避后重试
        attempt = 0
        last_error = None
        xml_text = None
        while attempt < 2:
            try:
                resp = _urlopen(url, timeout=30)
                xml_text = resp.read().decode("utf-8")
                last_error = None
                break
            except HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if e.code == 429:
                    _sleep(RETRY_BACKOFF_429)
                elif 500 <= e.code < 600:
                    _sleep(RETRY_BACKOFF_5XX)
                else:
                    break  # 4xx (非 429) 不重试
                attempt += 1
            except URLError as e:
                last_error = f"URLError: {e.reason}"
                _sleep(RETRY_BACKOFF_5XX)
                attempt += 1

        try:
            hits = parse_atom(xml_text) if xml_text else []
        except ET.ParseError as e:
            hits = []
            last_error = f"ParseError: {e}"
        elapsed_ms = int((time.time() - started_at) * 1000)

        return {
            "source_type": "arxiv-api",
            "query": keywords,
            "ipc_filter": ipc,            # 如实记录用户传入值
            "assignee_filter": assignee,
            "hits": hits,
            "hits_count": len(hits),
            "error": last_error,
            "skipped": False,
            "skip_reason": None,
            "elapsed_ms": elapsed_ms,
            "ipc_supported": False,        # arXiv 永远不支持 IPC
            "assignee_supported": False,
        }


def main():
    parser = argparse.ArgumentParser(description="arXiv API search")
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--ipc", default=None)
    parser.add_argument("--assignee", default=None)
    parser.add_argument("--output-json", default=None,
                        help="若给定则写入 JSON 文件，否则 print 到 stdout")
    args = parser.parse_args()

    client = ArxivClient()
    result = client.search(args.keywords, ipc=args.ipc, assignee=args.assignee, limit=args.limit)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            f.write(payload)
    else:
        print(payload)

    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
