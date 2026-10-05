"""Entry boundaries inside a section (PROMPT.md §5 Stage 10.2 rules baseline).

An entry = a head (title/company/date lines) followed by a body (bullets,
description). A new entry opens on a line that carries a date range, or that
repeats the style of the first head (bold / bigger / coloured), once the body
has started. Short plain lines directly after a head line still belong to the
head ("Present" wrapped under a date, a company under a title)."""

import re
from dataclasses import dataclass, field

from ir import Line

from rx3.fields.rules.dates import find_range, strip_range
from rx3.fields.rules.lex import is_company, is_title

CELL = "\t"  # layout joins same-row cells with a tab
_GLYPH = re.compile(r"^[\s•◦▪●■□◆▶►○·*\-–—>]+")
_NOISE = re.compile(r"^[\W_]*$")  # "[]" / "[§]" / lone icon glyphs: nothing readable


_OBULLET = re.compile(r"^\s*o\s+(?=[A-Z0-9(])")  # Word's nested bullet is a Courier "o"; the layout stage does not tag it


def bulletish(l: Line) -> bool:
    return bool(l.features and l.features.is_bullet) or bool(_OBULLET.match(l.text))


def strip_glyph(text: str) -> str:
    return _GLYPH.sub("", _OBULLET.sub("", text)).strip()


def cells(text: str) -> list[str]:
    out = []
    for c in text.split(CELL):
        c = strip_glyph(c)
        if c and not _NOISE.match(c):
            out.append(c)
    return out


@dataclass
class Entry:
    head: list[Line] = field(default_factory=list)
    body: list[Line] = field(default_factory=list)

    @property
    def lines(self) -> list[Line]:
        return self.head + self.body


def _style(l: Line) -> tuple:
    f = l.features
    return (f.bold, round(f.rel_size, 1) >= 1.1, f.color_differs) if f else (False, False, False)


def _is_styled(l: Line) -> bool:
    f = l.features
    return bool(f) and (f.bold or f.rel_size >= 1.1 or f.color_differs) and bool(l.text.strip())


def _has_date(l: Line) -> bool:
    """A range, or a lone date that is (nearly) all the line says; a year inside a sentence isn't one."""
    if len(l.text) > 160:
        return False
    f = find_range(l.text)
    if not f:
        return False
    if f.start or f.current:
        return True
    rest = (l.text[: f.span[0]] + l.text[f.span[1] :]).strip(" \t,;|-–—()")
    return len(rest) <= 20 or any(find_range(c) and not strip_range(c)[0] for c in cells(l.text))


def _has_range(l: Line) -> bool:
    f = find_range(l.text) if len(l.text) <= 160 else None
    return bool(f and (f.start or f.current))


def _short_plain(l: Line) -> bool:
    t = l.text.strip()
    f = l.features
    return len(t) <= 90 and not t.endswith(".") and not (bulletish(l) and not (f and f.bold))


def split_entries(lines: list[Line], extra_open=None) -> list[Entry]:
    """`extra_open(entry, line)`: section-specific rule that opens a new entry regardless of phase."""
    entries: list[Entry] = []
    cur: Entry | None = None
    in_body = False
    sig = None
    for l in lines:
        f = l.features
        bullet = bulletish(l)
        styled_head = _is_styled(l) and (not bullet or f.bold) and len(l.text) <= 160
        dated = _has_date(l) and not (bullet and not (f and f.bold))
        opens = (dated or (styled_head and (sig is None or _style(l) == sig))) and (
            cur is None or in_body or (_has_range(l) and any(_has_range(h) for h in cur.head)))  # a head holds one date range
        if cur is not None and not opens and extra_open and extra_open(cur, l):
            cur, in_body = Entry([l]), False
            entries.append(cur)
            continue
        if cur is None or opens:
            pulled: list[Line] = []
            if cur is not None and in_body and dated and not styled_head:
                # plain-document layout: "Title" sits on the line above its date line, at the end of the previous body
                while cur.body and len(pulled) < 2 and _short_plain(cur.body[-1]) and (
                        is_title(cur.body[-1].text) or is_company(cur.body[-1].text)) and not _has_date(cur.body[-1]):
                    pulled.insert(0, cur.body.pop())
            cur = Entry(pulled + [l])
            entries.append(cur)
            in_body = False
            if sig is None and styled_head:
                sig = _style(l)
            continue
        if not in_body and (styled_head or (_short_plain(l) and not bullet) or dated) and len(cur.head) < 4:
            cur.head.append(l)
        else:
            in_body = True
            cur.body.append(l)
    return entries


def per_line_entries(lines: list[Line]) -> list[Entry]:
    return [Entry([l]) for l in lines if cells(l.text)]
