"""A small Markdown renderer for the site, standard library only.

Covers what MTDI's documents use: headings (with anchors), paragraphs, ordered and
unordered lists (one level of nesting), fenced code (```mermaid is passed through
for the browser to draw), inline code, bold, italic, links, images, tables,
blockquotes and rules. Not a general CommonMark implementation.
"""
import html
import re

_INLINE_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")


def inline(text, link=lambda url: url):
    codes = []

    def keep(m):
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"
    text = _INLINE_CODE.sub(keep, text)
    text = html.escape(text, quote=False)

    def links(m):
        bang, label, url = m.groups()
        url = html.escape(link(html.unescape(url)), quote=True)
        if bang:
            return f'<img src="{url}" alt="{label}" loading="lazy">'
        external = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{url}"{external}>{label}</a>'
    text = _LINK.sub(links, text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    return re.sub("\x00(\\d+)\x00", lambda m: codes[int(m.group(1))], text)


def render(source, link=lambda url: url):
    lines = source.replace("\r\n", "\n").split("\n")
    out, i, toc = [], 0, []
    para = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para), link) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            lang = stripped[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            code = html.escape("\n".join(body))
            out.append(f'<pre class="mermaid">{code}</pre>' if lang == "mermaid"
                       else f'<pre><code class="lang-{html.escape(lang)}">{code}</code></pre>')
            i += 1
            continue
        if not stripped:
            flush()
            i += 1
            continue
        if stripped.startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        m = _HEADING.match(stripped)
        if m:
            flush()
            level, text = len(m.group(1)), inline(m.group(2), link)
            anchor = slug(text)
            if level in (2, 3):
                toc.append((level, anchor, re.sub(r"<[^>]+>", "", text)))
            out.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + render("\n".join(quote), link)[0] + "</blockquote>")
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            flush()
            cells = lambda row: [c.strip() for c in row.strip().strip("|").split("|")]
            head = cells(stripped)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            t = ["<div class=\"md-table\"><table><thead><tr>"] + [f"<th>{inline(h, link)}</th>" for h in head] + ["</tr></thead><tbody>"]
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c, link)}</td>" for c in r) + "</tr>")
            out.append("".join(t) + "</tbody></table></div>")
            continue
        m = _LIST.match(line)
        if m:
            flush()
            ordered = m.group(2)[0].isdigit()
            items = []
            while i < len(lines):
                m = _LIST.match(lines[i])
                if m and len(m.group(1)) < 2:
                    items.append([m.group(3), []])
                elif m and items:
                    items[-1][1].append(m.group(3))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1][0] += " " + lines[i].strip()
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            body = []
            for text, sub in items:
                nested = "<ul>" + "".join(f"<li>{inline(s, link)}</li>" for s in sub) + "</ul>" if sub else ""
                body.append(f"<li>{inline(text, link)}{nested}</li>")
            out.append(f"<{tag}>" + "".join(body) + f"</{tag}>")
            continue
        para.append(stripped)
        i += 1
    flush()
    return "\n".join(out), toc
