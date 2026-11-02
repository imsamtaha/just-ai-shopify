"""Assemble customer bundles from verified bilingual downloads; retain original inputs."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import posixpath
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
OLD = ROOT / "outputs/sale-packages-2026-11-01"
OUT = ROOT / "outputs/sale-packages-2026-11-02"
SOURCES = {
    "BASIC": "JUST_AI_Sales_Kit_BASIC_EN_AR_v2.zip",
    "PRO": "JUST_AI_Sales_Kit_PRO_EN_AR_v2.zip",
    "SPRINT": "JUST_AI_Content_Sprint_EN_AR_v2.zip",
}
EXPECTED = {"BASIC": 6, "PRO": 30, "SPRINT": 6}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
RETAIN = ("HOW_TO.mp4", "CAPTIONS_EN.vtt", "TRANSCRIPT_EN_AR.md", "VIDEO_POSTER.png")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_zip(path: Path) -> dict[str, bytes]:
    with ZipFile(path) as z:
        assert z.testzip() is None, f"ZIP CRC failed: {path.name}"
        names = [n for n in z.namelist() if not n.endswith("/")]
        assert len(names) == len(set(names)), "Duplicate ZIP paths"
        for name in names:
            p = PurePosixPath(name)
            assert not p.is_absolute() and ".." not in p.parts and "\\" not in name and ":" not in name, name
        return {n: z.read(n) for n in names}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in ("href", "src", "poster") and v)


def validate_files(files: dict[str, bytes]) -> dict:
    stats = {"office_files": 0, "xml_parts": 0, "csv_files": 0,
             "html_links": 0, "javascript_syntax_checks": 0, "bilingual_documents": []}
    for name, data in files.items():
        ext = PurePosixPath(name).suffix.lower()
        if ext in (".docx", ".xlsx"):
            with ZipFile(io.BytesIO(data)) as office:
                assert office.testzip() is None, name
                assert "[Content_Types].xml" in office.namelist(), name
                for part in office.namelist():
                    if part.endswith((".xml", ".rels")):
                        ET.fromstring(office.read(part))
                        stats["xml_parts"] += 1
                if ext == ".docx":
                    doc = ET.fromstring(office.read("word/document.xml"))
                    paragraphs = ["".join(t.text or "" for t in p.iter(W + "t")) for p in doc.iter(W + "p")]
                    text = "\n".join(paragraphs)
                    assert re.search(r"[\u0600-\u06ff]", text) and re.search(r"[A-Za-z]{3}", text), name
                    expected = next((n for marker, n in (("WhatsApp_50", 50), ("Instagram_30", 30), ("AI_Prompts_12", 12)) if marker in name), None)
                    pairs = Counter(int(m.group(1)) for p in paragraphs if (m := re.match(r"^(\d{2})[.)]?\s", p)))
                    if expected:
                        assert all(pairs[i] >= 2 for i in range(1, expected + 1)), (name, dict(pairs))
                    stats["bilingual_documents"].append({"file": name, "paired_numbered_templates": expected})
                else:
                    assert "xl/workbook.xml" in office.namelist(), name
                    workbook = ET.fromstring(office.read("xl/workbook.xml"))
                    sheets = [x.attrib["name"] for x in workbook.iter() if x.tag.endswith("}sheet")]
                    assert {"Leads", "Orders", "Dashboard"}.issubset(sheets), sheets
            stats["office_files"] += 1
        elif ext == ".pdf":
            assert data.startswith(b"%PDF-") and b"%%EOF" in data[-2048:], name
        elif ext == ".csv":
            rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
            assert len(rows) > 1 and all(len(row) == len(rows[0]) for row in rows), name
            stats["csv_files"] += 1
        elif ext == ".html":
            html = data.decode("utf-8-sig")
            parser = Links()
            parser.feed(html)
            for link in parser.links:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
                assert target in files, (name, link, target)
                stats["html_links"] += 1
            for script in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I):
                check_js(script, name)
                stats["javascript_syntax_checks"] += 1
        elif ext == ".js":
            check_js(data.decode("utf-8-sig"), name)
            stats["javascript_syntax_checks"] += 1
    return stats


def check_js(script: str, name: str):
    with tempfile.TemporaryDirectory(prefix="just-ai-syntax-") as temp:
        p = Path(temp) / "check.js"
        p.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        assert result.returncode == 0, (name, result.stderr)


def make_guide(old: bytes) -> bytes:
    text = old.decode("utf-8").replace("v2", "v3")
    text = text.replace(
        "The original messaging examples are Arabic; this English tutorial does not translate all templates.",
        "The updated messaging templates pair English and Arabic. Review and personalize the language you will use.",
    ).replace(
        "أمثلة الرسائل الأصلية بالعربية؛ الشرح الإنجليزي لا يعني ترجمة كل القوالب.",
        "تجمع قوالب الرسائل المحدّثة بين الإنجليزية والعربية. راجع اللغة التي ستستخدمها وخصّص النص قبل الإرسال.",
    ).replace(
        "The original kit is in Original/. Its existing license and language limitations still apply.",
        "The updated English and Arabic resources are in Original/. The included source licenses still apply. "
        "<span lang=\"ar\" dir=\"rtl\">الموارد المحدّثة بالإنجليزية والعربية داخل مجلد Original. تبقى تراخيص الملفات المرفقة سارية.</span>",
    )
    note = ('<section><h2>Updated bilingual edition / الإصدار المحدّث باللغتين</h2>'
            '<p>Complete bundle v3 · 2 November 2026. The resource files are the bilingual v2 edition. '
            'The existing v2 tutorial video, captions, transcript and poster are retained. '
            'The video may mention the older bundle or Arabic-only templates; the files in this bundle are the updated bilingual resources. '
            'Follow this written guide for current file information.</p>'
            '<p lang="ar" dir="rtl">الحزمة الكاملة v3 — ٢ نوفمبر ٢٠٢٦. ملفات الموارد هي الإصدار v2 الثنائي اللغة. '
            'احتفظنا بفيديو الشرح السابق وترجمته النصية ونصه وصورته. قد يذكر الفيديو الحزمة السابقة أو قوالب عربية فقط؛ '
            'الموارد داخل هذه الحزمة محدّثة بالإنجليزية والعربية. اتبع هذا الدليل المكتوب لمعلومات الملفات الحالية.</p>'
            '<p><a href="VERSION_NOTES_EN_AR.md">Version notes / ملاحظات الإصدار</a></p></section>')
    return text.replace("</header>", "</header>" + note, 1).encode("utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"built_on": "2026-11-02", "source": "Local Downloads; Google Drive checked separately", "packages": []}
    for key, source_name in SOURCES.items():
        source_path = DOWNLOADS / source_name
        old_path = OLD / f"JUST_AI_{key}_COMPLETE_v2.zip"
        resources = read_zip(source_path)
        old = read_zip(old_path)
        assert len(resources) == EXPECTED[key], (key, len(resources))
        manifest = json.loads(old["MANIFEST.json"])
        assert set(manifest) == set(old) - {"MANIFEST.json"}, key
        for name, meta in manifest.items():
            assert meta["bytes"] == len(old[name]) and meta["sha256"] == digest(old[name]), name
        assert set(resources) == {n.removeprefix("Original/") for n in old if n.startswith("Original/")}, key
        files = {n: old[n] for n in RETAIN}
        files.update({"Original/" + n: data for n, data in resources.items()})
        files["START_HERE.html"] = make_guide(old["START_HERE.html"])
        files["VERSION_NOTES_EN_AR.md"] = (
            f"# JUST AI {key} — complete bilingual bundle v3\n\n"
            f"Assembled 2 November 2026 from `{source_name}` and the existing complete v2 tutorial assets. "
            f"All {len(resources)} resource files in `Original/` were replaced with the verified bilingual v2 files. "
            "Source version labels remain v2; v3 identifies this complete assembly.\n\n"
            "Extract the whole ZIP and open START_HERE.html. English synthetic narration is unchanged. "
            "The previous video and its matching transcript/captions are retained, including historical version/language references. "
            "The updated written guide describes the current bilingual resources. This bundle does not contain a newly recorded video.\n\n"
            "Existing source licenses apply. Template utilities do not connect accounts, send messages or publish content automatically. "
            "No priced promotional artwork or seller-only packages were added.\n\n"
            "## العربية\n\n"
            f"جُمعت هذه الحزمة في ٢ نوفمبر ٢٠٢٦. تم استبدال جميع ملفات الموارد وعددها {len(resources)} داخل مجلد Original "
            "بالنسخة v2 التي تم التحقق من احتوائها على الإنجليزية والعربية. يشير v3 إلى الحزمة الكاملة الجديدة، "
            "بينما تبقى أرقام إصدارات المصادر كما هي.\n\n"
            "فك ضغط الملف كاملاً وافتح START_HERE.html. احتفظنا بفيديو الشرح السابق بصوته الاصطناعي الإنجليزي ونصه وترجمته النصية، "
            "بما في ذلك إشاراته إلى الإصدار واللغات السابقة. الدليل المكتوب محدّث لشرح الملفات الحالية. لم يُسجّل فيديو جديد في هذا التحديث.\n\n"
            "تظل تراخيص المصادر سارية. لا تربط الأدوات الحسابات ولا ترسل الرسائل ولا تنشر المحتوى تلقائياً. "
            "لم تُضف صور ترويجية بأسعار أو حزم خاصة بالبائع.\n"
        ).encode("utf-8")
        validation = validate_files(files)
        new_manifest = {n: {"bytes": len(data), "sha256": digest(data)} for n, data in sorted(files.items())}
        files["MANIFEST.json"] = json.dumps(new_manifest, indent=2, ensure_ascii=False).encode("utf-8")
        target = OUT / f"JUST_AI_{key}_COMPLETE_EN_AR_v3.zip"
        assert not target.exists(), f"Refusing to overwrite {target}"
        with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=6) as z:
            for name, data in sorted(files.items()):
                z.writestr(name, data)
        reread = read_zip(target)
        assert reread == files
        verified_manifest = json.loads(reread["MANIFEST.json"])
        assert set(verified_manifest) == set(reread) - {"MANIFEST.json"}
        for name, meta in verified_manifest.items():
            assert len(reread[name]) == meta["bytes"] and digest(reread[name]) == meta["sha256"]
        assert all(reread[n] == old[n] for n in RETAIN)
        record = {
            "kit": key, "path": str(target), "bytes": target.stat().st_size,
            "sha256": digest(target.read_bytes()), "files": len(files), "resources_replaced": len(resources),
            "source_zip": str(source_path), "source_sha256": digest(source_path.read_bytes()),
            "tutorial_source_zip": str(old_path), "tutorial_source_sha256": digest(old_path.read_bytes()),
            "retained_assets_sha256": {n: digest(old[n]) for n in RETAIN},
            "all_resources_match_selected_source": True, "manifest_and_crc_passed": True,
            "validation": validation,
        }
        report["packages"].append(record)
        print(json.dumps({k: record[k] for k in ("kit", "bytes", "files", "resources_replaced", "validation")}, ensure_ascii=False))
    (OUT / "PACKAGE_VALIDATION.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
