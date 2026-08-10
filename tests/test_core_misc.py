from __future__ import annotations

from typing import TYPE_CHECKING

from fava.core.misc import sidebar_links

if TYPE_CHECKING:  # pragma: no cover
    from fava.beans.abc import Custom


def test_sidebar_links(load_doc_custom_entries: list[Custom]) -> None:
    """
    2016-01-01 custom "fava-sidebar-link" "title" "link"
    2016-01-02 custom "fava-sidebar-link" "titl1" "lin1"
    """
    links = sidebar_links(load_doc_custom_entries)
    assert links == [("title", "link"), ("titl1", "lin1")]
