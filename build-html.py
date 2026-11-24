# ponytail: one-pass markdown for this repo only. Upgrade path is a real markdown lib.
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent
PAGES = [ROOT / "LEIA-ME.md"]
PAGES += sorted((ROOT / "historia-principal").glob("*.md"))
PAGES += sorted((ROOT / "decisoes").glob("*.md"))
PAGES += [ROOT / "laminas" / "ONDE-USAR.md"]

IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
CODE = re.compile(r"`([^`]+)`")


def inline(text):
    text = html.escape(text)
    slots = []

    def park(fragment):
        slots.append(fragment)
        return f"\x00{len(slots) - 1}\x00"

    def image(alt, url):
        label = html.escape(alt or "lâmina")
        src = html.escape(url, quote=True)
        return park(f'<a class="mostrar" href="{src}">Mostrar: {label}</a>')

    def link(label, url):
        href = url[:-3] + ".html" if url.endswith(".md") else url
        if href.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return image(label, href)
        return park(f'<a href="{html.escape(href, quote=True)}">{label}</a>')

    text = IMG.sub(lambda m: image(html.unescape(m.group(1)), html.unescape(m.group(2))), text)
    text = LINK.sub(lambda m: link(m.group(1), html.unescape(m.group(2))), text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = CODE.sub(r"<code>\1</code>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m.group(1))], text)


def convert(md):
    out = []
    para, quote, items, table = [], [], [], []

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    def flush_quote():
        if quote:
            out.append("<blockquote>" + "".join(f"<p>{inline(p)}</p>" for p in quote) + "</blockquote>")
            quote.clear()

    def flush_items():
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    def flush_table():
        if not table:
            return
        rows = [r for r in table if not re.match(r"^\|?\s*-+", r.replace("|", ""))]
        if not rows:
            table.clear()
            return
        head, *body = rows

        def cells(row, tag):
            parts = [c.strip() for c in row.strip().strip("|").split("|")]
            return "".join(f"<{tag}>{inline(c)}</{tag}>" for c in parts)

        body_html = "".join(f"<tr>{cells(r, 'td')}</tr>" for r in body)
        out.append(f"<table><thead><tr>{cells(head, 'th')}</tr></thead><tbody>{body_html}</tbody></table>")
        table.clear()

    def flush():
        flush_para()
        flush_quote()
        flush_items()
        flush_table()

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line.startswith(">"):
            flush_para()
            flush_items()
            flush_table()
            bit = line[1:].strip()
            if bit:
                quote.append(bit)
        elif line.startswith("|"):
            flush_para()
            flush_quote()
            flush_items()
            table.append(line)
        elif line.startswith("- "):
            flush_para()
            flush_quote()
            flush_table()
            items.append(line[2:].strip())
        else:
            flush_quote()
            flush_items()
            flush_table()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def page(title, body, depth, aside=None):
    home = "index.html" if depth == 0 else "../" * depth + "index.html"
    if aside:
        content = f'<div class="mesa">\n<main>\n{body}\n</main>\n<aside class="ficha">\n{aside}\n</aside>\n</div>'
    else:
        content = f"<main>\n{body}\n</main>"
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{"../" * depth}site.css">
</head>
<body>
<header><a href="{home}">Flechas de goblin</a></header>
{content}
<div id="visor" hidden>
<img alt="">
<p>Clica outra vez para fechar</p>
</div>
<script>
const visor = document.getElementById("visor");
const foto = visor.querySelector("img");
document.body.addEventListener("click", (e) => {{
  const start = e.target instanceof Element ? e.target : e.target.parentElement;
  const btn = start && start.closest(".mostrar");
  if (!btn) return;
  e.preventDefault();
  foto.src = btn.getAttribute("href");
  foto.alt = btn.textContent;
  visor.hidden = false;
}});
visor.addEventListener("click", () => {{ visor.hidden = true; }});
document.addEventListener("keydown", (e) => {{
  if (e.key === "Escape") visor.hidden = true;
}});
</script>
</body>
</html>
"""


def main():
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    for path in PAGES:
        md = path.read_text(encoding="utf-8")
        title = next((ln[2:].strip() for ln in md.splitlines() if ln.startswith("# ")), path.stem)
        depth = len(path.relative_to(ROOT).parts) - 1
        body = convert(md)
        dest = ROOT / "index.html" if path.name == "LEIA-ME.md" else path.with_suffix(".html")
        aside = None
        if dest.name == "index.html":
            sheet = convert((ROOT / "historia-principal" / "00-sera-e-relogio.md").read_text(encoding="utf-8"))
            aside = sheet.replace('href="../', 'href="')
        dest.write_text(page(title, body, 0 if dest.name == "index.html" else depth, aside), encoding="utf-8")
        text = dest.read_text(encoding="utf-8")
        if "<p></p>" in text or "<h" not in text or "<img src=" in text or "parentElement" not in text:
            raise SystemExit(f"bad html: {dest}")
        print(dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
