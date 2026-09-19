"""Equal values require original-byte proof; ambiguous dictionaries still fail."""

import io

import pikepdf
import pytest

from src.domain.native_pdf import NativePdfCreate, NativePdfPageEdit
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_pdf_lengths import _Dictionary, verified_parser_checks
from src.infrastructure.native_pdf_package import NativePdfPackage
from tests.native_pdf_helpers import page_reference
from tests.native_pdf_length_helpers import duplicate_length_pdf


@pytest.mark.parametrize(
    "dictionary",
    [
        b"/Length 4 /Length 4",
        b"/Length +04 % second spelling\n/L#65ngth 4",
        b"/Length 4 /Nested << /Length 7 /Flags [0 1 true null] >> /Length 4",
        b"/Length 4 /Length 4 /Length 4",
    ],
)
def test_equal_direct_lengths_are_proven_without_rewriting_source(dictionary):
    data = duplicate_length_pdf(dictionary)
    native = NativePdf()
    listing = native.inspect(data)
    checks = listing["parser_checks"][0]
    assert checks["verified_stream_count"] == 1 and checks["source_bytes_preserved"]
    reference = page_reference(data, 0)
    with NativePdfPackage(data) as p:
        assert (
            p.data == data and p.record(0)["parser_checks"] == listing["parser_checks"]
        )
    png = native.render(data, reference.locator, 128)
    assert png.startswith(b"\x89PNG")
    changed, receipt = native.edit(
        data, [NativePdfPageEdit(reference=reference, rotation=90)]
    )
    assert "canonicalized_equal_duplicate_stream_lengths" in receipt.repairs
    with NativePdfPackage(changed) as checked:
        assert not checked.parser_checks and checked.pdf.pages[0].obj.Rotate == 90
    request = NativePdfCreate(name="copied.pdf", pages=[{"reference": reference}])
    copied, receipt = native.create(
        request, {f"{reference.asset_id}:{reference.revision}": data}
    )
    assert "canonicalized_equal_duplicate_stream_lengths" in receipt.repairs
    assert "parser_checks" not in native.inspect(copied)


@pytest.mark.parametrize(
    "dictionary",
    [
        b"/Length 3 /Length 4",
        b"/Length 4 /Length 4.0",
        b"/Length 4 /Length 5 0 R",
        b"/Length 4 /Length 4 /Other 1 /Other 1",
        b"/Length 4 /Nested << /Length 4 /Length 4 >>",
        b"/Length 4 /Nested << /Length 7 /Length 7 >> /Length 4",
        b"/Length 4 /Note (not /Length 4) /Length 4",
        b"/Length 4 /Note <00> /Length 4",
        b"/Length 3 /Length 3",
    ],
)
def test_conflicts_indirect_nested_and_unsupported_lengths_fail(dictionary):
    with pytest.raises(ValueError):
        NativePdf().inspect(duplicate_length_pdf(dictionary))


def test_unknown_or_mislocated_diagnostic_is_not_silently_accepted():
    data = duplicate_length_pdf()
    with pikepdf.Pdf.open(io.BytesIO(data), attempt_recovery=False) as pdf:
        assert len(pdf.objects) == 4
        warnings = pdf.get_warnings()
        with pytest.raises(ValueError, match="repair separately"):
            verified_parser_checks(data, pdf, ["unknown warning"])
        with pytest.raises(ValueError, match="root stream"):
            verified_parser_checks(
                data, pdf, [warnings[0].replace("offset ", "offset 9")]
            )


def test_dictionary_resource_bounds_and_original_endstream_are_enforced():
    for data in [
        b"<< /Length 4 " + b" " * 65536 + b"/Length 4 >>",
        b"<< /A " + b"[" * 40 + b"0" + b"]" * 40 + b">>",
    ]:
        with pytest.raises(ValueError, match=r"oversized|nesting"):
            p = _Dictionary(data, 0)
            p.value(p.token(), 0)
    with pytest.raises(ValueError):
        NativePdf().inspect(duplicate_length_pdf(stream=b"q\nQ\njunk"))
