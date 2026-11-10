from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def rwf(value):
    try:
        return f"{int(value):,} RWF"
    except (TypeError, ValueError):
        return "—"


@register.filter
def doc_body(text):
    """Render contract text: '## Heading' lines become headings, blank lines split paragraphs,
    lines starting with '- ' become list items. Everything is escaped first."""
    out, items = [], []

    def flush():
        if items:
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
            items.clear()

    for block in (text or "").replace("\r\n", "\n").split("\n"):
        line = block.rstrip()
        if line.startswith("## "):
            flush(); out.append(f"<h3>{escape(line[3:])}</h3>")
        elif line.startswith("- "):
            items.append(escape(line[2:]))
        elif line.strip() == "":
            flush()
        else:
            flush(); out.append(f"<p>{escape(line)}</p>")
    flush()
    return mark_safe("\n".join(out))


@register.filter
def lines(text):
    return [l.strip() for l in (text or "").splitlines() if l.strip()]
