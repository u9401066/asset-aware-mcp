"""Independent PDF checks for the specifically observed title and hidden-sheet cuts."""

import pymupdf


def title_pixels(page, color):
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    data = pix.samples
    channel = 0 if color == "red" else 2
    other = 2 if color == "red" else 0
    return sum(
        data[i + channel] > 180 and data[i + other] < 100 and data[i + 1] < 100
        for i in range(0, len(data), pix.n)
    )


def check_corrected_pdf(original: bytes, corrected: bytes):
    with (
        pymupdf.open(stream=original, filetype="pdf") as before,
        pymupdf.open(stream=corrected, filetype="pdf") as after,
    ):
        assert len(before) == len(after) == 4
        assert "HIDDEN CONTENT" not in before[2].get_text()
        assert "HIDDEN CONTENT" in after[2].get_text()
        assert not before[1].get_text() and not after[1].get_text()
        assert "3" in after[0].get_text().splitlines()
        assert "OUTSIDE PRINT RANGE" in after[0].get_text()
        pixels = {}
        for index, color, text in (
            (0, "red", "FIRST PRINT"),
            (3, "blue", "LAST PRINT"),
        ):
            assert text in after[index].get_text()
            old, new = (
                title_pixels(before[index], color),
                title_pixels(after[index], color),
            )
            assert old > 0 and new > old * 1.15, (color, old, new)
            pixels[color] = {"before": old, "after": new}
        return pixels
