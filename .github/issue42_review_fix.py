from pathlib import Path

path = Path("src/cal_mcp/concordance.py")
text = path.read_text()
old = '''    linked_row_indexes: list[int] = []
    for index, line in enumerate(lines):
        text = getattr(line, "text", "")
        if _FREQUENCY_RE.match(text) is None:
            continue
        links = getattr(line, "links", ())
        if any(_is_path(getattr(link, "href", ""), "showKWIC.php") for link in links):
            linked_row_indexes.append(index)

    if not linked_row_indexes:
        return None

    start = linked_row_indexes[0]
    while start > 0 and _FREQUENCY_RE.match(getattr(lines[start - 1], "text", "")) is not None:
        start -= 1
    end = linked_row_indexes[0]
    while (
        end + 1 < len(lines)
        and _FREQUENCY_RE.match(getattr(lines[end + 1], "text", "")) is not None
    ):
        end += 1
    if any(index > end for index in linked_row_indexes):
        raise ConcordanceParseError("CAL inline concordance lemma rows are not contiguous")
'''
new = '''    kwic_row_indexes: list[int] = []
    linked_frequency_row_indexes: list[int] = []
    for index, line in enumerate(lines):
        text = getattr(line, "text", "")
        links = getattr(line, "links", ())
        has_kwic_link = any(
            _is_path(getattr(link, "href", ""), "showKWIC.php") for link in links
        )
        if not has_kwic_link:
            continue
        kwic_row_indexes.append(index)
        if _FREQUENCY_RE.match(text) is not None:
            linked_frequency_row_indexes.append(index)

    if not linked_frequency_row_indexes:
        return None

    start = kwic_row_indexes[0]
    while start > 0 and _FREQUENCY_RE.match(getattr(lines[start - 1], "text", "")) is not None:
        start -= 1
    end = kwic_row_indexes[-1]
    while (
        end + 1 < len(lines)
        and _FREQUENCY_RE.match(getattr(lines[end + 1], "text", "")) is not None
    ):
        end += 1
'''
if text.count(old) != 1:
    raise SystemExit("expected parser block not found exactly once")
path.write_text(text.replace(old, new))
