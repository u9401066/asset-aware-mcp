"""Independent string/byte/region oracles; no production mutation helpers."""

import csv
import io

from tests.codex_pdf.trace import require


def csv_bytes(rows):
    text = io.StringIO(newline="")
    csv.writer(text, lineterminator="\r\n").writerows(rows)
    return b"\xef\xbb\xbf" + text.getvalue().encode()


def expected_revisions(case):
    rows = [case["columns"], *case["rows"]]
    original = csv_bytes(rows)
    edited = [r[:] for r in rows]
    edited[1][1] = "__review__"
    inserted = [*rows, ["temporary"] * len(rows[0])]
    column = [[*r, "Review" if i == 0 else "checked"] for i, r in enumerate(inserted)]
    return [
        original,
        csv_bytes(edited),
        original,
        csv_bytes(inserted),
        csv_bytes(column),
        csv_bytes(column[:-1]),
        original,
    ]


def differences(actual, expected):
    result = []
    for r in range(max(len(actual), len(expected))):
        a, e = (
            actual[r] if r < len(actual) else [],
            expected[r] if r < len(expected) else [],
        )
        for c in range(max(len(a), len(e))):
            av, ev = a[c] if c < len(a) else None, e[c] if c < len(e) else None
            if av != ev:
                result.append({"row": r, "column": c, "actual": av, "expected": ev})
    return result


def require_coverage(rect, bounds):
    require(
        len(rect) == 4
        and 0 <= rect[0] < rect[2] <= 1
        and 0 <= rect[1] < rect[3] <= 1
        and rect[0] <= bounds[0]
        and rect[1] <= bounds[1]
        and rect[2] >= bounds[2]
        and rect[3] >= bounds[3],
        "Chosen region clips calibrated table glyph coverage",
    )
