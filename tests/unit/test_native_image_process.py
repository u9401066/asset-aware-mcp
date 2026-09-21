import hashlib
import io
import multiprocessing

import pytest
from PIL import Image

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_image import (
    NativeImageBlank,
    NativeImageFrameLocator,
    NativeImageFrameMap,
)
from src.infrastructure.native_image_process import ProcessNativeImage
from tests.native_image_helpers import encoded
from tests.unit.test_native_image_compose import request_for
from tests.unit.test_native_image_revision import (
    CANDIDATE_ID,
    SOURCE_ID,
    plan_for,
    references,
)


def test_worker_read_preview_and_mutation_transport_preserves_native_bytes():
    native = ProcessNativeImage(timeout=20)
    data = encoded()
    record = native.records(data)[0]
    _, old = references(data, SOURCE_ID)
    _, new = references(data, CANDIDATE_ID)
    assert record["decoded_pixels_sha256"]
    preview = native.render(data, NativeImageFrameLocator(frame_index=0), 64)
    assert hashlib.sha256(preview["png"]).hexdigest() == preview["png_sha256"]
    with Image.open(io.BytesIO(preview["png"])) as image:
        assert image.size == (12, 8)
    output, receipt = native.accept_candidate(
        data,
        data,
        plan_for(data, data, [NativeImageFrameMap(before=old[0], after=new[0])]),
        SOURCE_ID,
    )
    assert output == data and isinstance(receipt, NativeEditResult)
    blank, _ = native.create(
        NativeImageBlank(name="canvas.png", width=2, height=2, rgba=[1, 2, 3, 4])
    )
    assert native.inspect(blank)["frame_count"] == 1
    request, sources = request_for(data)
    composed, receipt = native.compose(request, sources)
    assert composed[:2] in {b"II", b"MM"}
    assert len(receipt.changes) == 1


def test_worker_failures_timeout_and_result_limit_leave_no_live_children(
    monkeypatch, tmp_path
):
    from src.infrastructure import native_image_process

    children_before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(ValueError, match="unsupported raster"):
        ProcessNativeImage().records(b"invalid")
    with pytest.raises(ValueError, match="Unknown"):
        ProcessNativeImage()._run("__class__")
    with pytest.raises(ValueError, match="time limit"):
        ProcessNativeImage(timeout=0.000001).records(encoded())
    monkeypatch.setattr(native_image_process, "MAX_RESULT_BYTES", 100)
    with pytest.raises(ValueError):
        ProcessNativeImage()._execute(
            tmp_path / "too-large.msgpack", "records", (encoded(),)
        )
    assert not (tmp_path / "too-large.msgpack").exists()
    assert {p.pid for p in multiprocessing.active_children()} == children_before


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_worker_requires_finite_positive_timeout(value):
    with pytest.raises(ValueError, match="finite and positive"):
        ProcessNativeImage(timeout=value)
