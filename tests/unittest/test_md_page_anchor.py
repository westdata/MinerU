# Copyright (c) Opendatalab. All rights reserved.
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make
from mineru.utils.enum_class import BlockType, ContentType, MakeMode
from mineru.utils.table_merge import merge_table


def _table_block(html):
    return {
        "type": BlockType.TABLE,
        "bbox": [0, 0, 100, 100],
        "blocks": [
            {
                "type": BlockType.TABLE_BODY,
                "lines": [
                    {
                        "spans": [
                            {
                                "type": ContentType.TABLE,
                                "html": html,
                            }
                        ]
                    }
                ],
            }
        ],
    }


def test_pipeline_md_page_anchor_lists_pages_covered_by_merged_table():
    pdf_info = [
        {
            "page_idx": 0,
            "page_size": [100, 100],
            "discarded_blocks": [],
            "para_blocks": [
                _table_block(
                    "<table><tbody>"
                    "<tr><td>Name</td><td>Value</td></tr>"
                    "<tr><td>A</td><td>1</td></tr>"
                    "</tbody></table>"
                )
            ],
        },
        {
            "page_idx": 1,
            "page_size": [100, 100],
            "discarded_blocks": [],
            "para_blocks": [
                _table_block(
                    "<table><tbody>"
                    "<tr><td>Name</td><td>Value</td></tr>"
                    "<tr><td>B</td><td>2</td></tr>"
                    "</tbody></table>"
                )
            ],
        },
    ]

    merge_table(pdf_info)

    markdown = union_make(
        pdf_info,
        MakeMode.MM_MD,
        md_page_anchor=True,
    )

    assert markdown.startswith("[PAGE=1,2]\n")
    assert "[PAGE=2]" not in markdown
