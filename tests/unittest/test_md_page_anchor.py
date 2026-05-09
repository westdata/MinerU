# Copyright (c) Opendatalab. All rights reserved.
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
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


def _title_block(text):
    return {
        "type": BlockType.TITLE,
        "lines": [
            {
                "spans": [
                    {
                        "type": ContentType.TEXT,
                        "content": text,
                    }
                ]
            }
        ],
    }


def _image_block(image_path):
    return {
        "type": BlockType.IMAGE,
        "bbox": [0, 0, 100, 100],
        "blocks": [
            {
                "type": BlockType.IMAGE_BODY,
                "lines": [
                    {
                        "spans": [
                            {
                                "type": ContentType.IMAGE,
                                "image_path": image_path,
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


def test_pipeline_md_page_anchor_includes_merged_table_pages_after_title():
    pdf_info = [
        {
            "page_idx": 0,
            "page_size": [100, 100],
            "discarded_blocks": [],
            "para_blocks": [
                _title_block("Basic Info"),
                _table_block(
                    "<table><tbody>"
                    "<tr><td>Name</td><td>Value</td></tr>"
                    "<tr><td>A</td><td>1</td></tr>"
                    "</tbody></table>"
                ),
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
    assert "# Basic Info" in markdown


def test_pipeline_content_list_image_text_uses_markdown_image_path():
    pdf_info = [
        {
            "page_idx": 0,
            "page_size": [100, 100],
            "discarded_blocks": [],
            "para_blocks": [
                _image_block("abc123.jpg")
            ],
        }
    ]

    markdown = union_make(pdf_info, MakeMode.MM_MD, "images")
    content_list = union_make(pdf_info, MakeMode.CONTENT_LIST, "images")

    assert content_list[0]["text"] == "images/abc123.jpg"
    assert content_list[0]["text"] in markdown


def test_vlm_content_list_image_text_uses_markdown_image_path():
    pdf_info = [
        {
            "page_idx": 0,
            "page_size": [100, 100],
            "discarded_blocks": [],
            "para_blocks": [
                _image_block("abc123.jpg")
            ],
        }
    ]

    markdown = vlm_union_make(pdf_info, MakeMode.MM_MD, "images")
    content_list = vlm_union_make(pdf_info, MakeMode.CONTENT_LIST, "images")

    assert content_list[0]["text"] == "images/abc123.jpg"
    assert content_list[0]["text"] in markdown


def test_pipeline_content_list_table_continuation_text_matches_merged_markdown():
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
                    "<tr><td>ContinuationAnchor</td><td>2</td></tr>"
                    "</tbody></table>"
                )
            ],
        },
    ]

    merge_table(pdf_info)

    markdown = union_make(pdf_info, MakeMode.MM_MD)
    content_list = union_make(pdf_info, MakeMode.CONTENT_LIST)
    continuation_item = next(item for item in content_list if item["page_idx"] == 1)

    assert continuation_item["text"] == "ContinuationAnchor"
    assert continuation_item["text"] in markdown


def test_pipeline_content_list_table_continuation_text_matches_escaped_html():
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
                    "<tr><td>R&amp;D</td><td>2</td></tr>"
                    "</tbody></table>"
                )
            ],
        },
    ]

    merge_table(pdf_info)

    markdown = union_make(pdf_info, MakeMode.MM_MD)
    content_list = union_make(pdf_info, MakeMode.CONTENT_LIST)
    continuation_item = next(item for item in content_list if item["page_idx"] == 1)

    assert continuation_item["text"] == "R&amp;D"
    assert continuation_item["text"] in markdown
