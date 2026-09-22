"""Authored AcroForm fixtures with duplicate names, shared views and hidden values."""

from __future__ import annotations

import pikepdf

from tests.native_pdf_helpers import build_pdf, rewrite


def form_pdf():
    def add(pdf):
        roots = pikepdf.Array()
        pdf.Root.AcroForm = pikepdf.Dictionary(
            Fields=roots,
            DA=pikepdf.String("/Helv 11 Tf 0 g"),
            Q=0,
            DR=pikepdf.Dictionary(
                Font=pikepdf.Dictionary(
                    Helv=pdf.make_indirect(
                        pikepdf.Dictionary(
                            Type=pikepdf.Name.Font,
                            Subtype=pikepdf.Name.Type1,
                            BaseFont=pikepdf.Name.Helvetica,
                        )
                    )
                )
            ),
        )

        def appearance(color):
            stream = pdf.make_stream(f"q {color} rg 0 0 100 20 re f Q".encode())
            stream.Type = pikepdf.Name.XObject
            stream.Subtype = pikepdf.Name.Form
            stream.BBox = pikepdf.Array([0, 0, 100, 20])
            stream.Resources = pikepdf.Dictionary()
            return stream

        def widget(page, parent=None, on=None):
            obj = pdf.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Widget,
                    Rect=pikepdf.Array([60, 200, 160, 220]),
                    F=4,
                    P=pdf.pages[page].obj,
                    AP=pikepdf.Dictionary(N=appearance("0.8 0.9 1")),
                )
            )
            if on is not None:
                obj.AP.N = pikepdf.Dictionary(
                    {"/Off": appearance("1 1 1"), on: appearance("0.1 0.2 0.3")}
                )
                obj.AS = pikepdf.Name.Off
            if parent is not None:
                obj.Parent = parent
            pdf.pages[page].obj.Annots.append(obj)
            return obj

        for page, value in enumerate(("第一筆 007 µg", "second 0008")):
            obj = widget(page)
            obj.FT = pikepdf.Name.Tx
            obj.T = pikepdf.String("duplicate")
            obj.V = pikepdf.String(value)
            roots.append(obj)
        group = pdf.make_indirect(
            pikepdf.Dictionary(
                T=pikepdf.String("person"),
                FT=pikepdf.Name.Tx,
                Ff=2,
                MaxLen=40,
                DA=pikepdf.String("/Helv 9 Tf 1 0 0 rg"),
                Q=2,
                AA=pikepdf.Dictionary(
                    K=pikepdf.Dictionary(
                        S=pikepdf.Name.JavaScript,
                        JS=pikepdf.String("event.value = 'unchanged';"),
                    )
                ),
            )
        )
        hidden = pdf.make_indirect(
            pikepdf.Dictionary(
                T=pikepdf.String("hidden"), V=pikepdf.String("007"), Parent=group
            )
        )
        group.Kids = pikepdf.Array([hidden])
        roots.append(group)
        radio = pdf.make_indirect(
            pikepdf.Dictionary(
                T=pikepdf.String("radio"),
                FT=pikepdf.Name.Btn,
                Ff=32768,
                V=pikepdf.Name.Off,
            )
        )
        radio.Kids = pikepdf.Array(
            [widget(0, radio, "/First"), widget(1, radio, "/Second")]
        )
        roots.append(radio)
        repeated = pdf.make_indirect(
            pikepdf.Dictionary(
                T=pikepdf.String("across"),
                FT=pikepdf.Name.Tx,
                V=pikepdf.String("shared value"),
            )
        )
        repeated.Kids = pikepdf.Array([widget(0, repeated), widget(2, repeated)])
        roots.append(repeated)
        choice = widget(1)
        choice.T = pikepdf.String("choice")
        choice.FT = pikepdf.Name.Ch
        choice.Ff = 2097152
        choice.Opt = pikepdf.Array(
            [pikepdf.Array(["a", "甲"]), "middle", pikepdf.Array(["b", "乙"])]
        )
        choice.V = pikepdf.Array(["a", "b"])
        choice.I = pikepdf.Array([0, 2])
        choice.TI = 1
        roots.append(choice)

    return rewrite(build_pdf(links=True, labels=True), add)
