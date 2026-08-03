"""Markdown → HTML for notification bodies.

Two callers, one renderer:

**AI investigation reports.** `ai_analyst_report.report_markdown` is a 6–8 KB
document whose substance lives in GFM tables — a reconstructed event timeline,
an IOC verdict table, a recurrence comparison. Delivered as plain text those are
pipe-delimited noise, which is the whole reason #1048 exists.

**Markdown-format templates on the email channel.** A template declaring
`format="markdown"` used to reach an inbox as literal `*Severity:*`, because
`ResendChannel` only ever set an HTML part for `format="html"`. Correct in Slack
and Teams, where those asterisks are bold; wrong in a mail client.

Three things here are load-bearing rather than stylistic:

**`html=False` is not the default.** Both the `commonmark` and `gfm-like`
presets ship `html: True`, so raw HTML in the source passes through unescaped.
Report markdown is LLM-written and templates are operator-authored — neither is
trusted enough for that — so the option is set explicitly. Verified by
`test_raw_html_in_markdown_is_escaped`.

**Tables need enabling.** They are not part of CommonMark. Under the default
preset a GFM table renders as one run-on paragraph with visible pipes, which
looks like working output and is the single easiest thing to get silently wrong
here. `gfm-like` turns them on.

**Styling has to be inline.** Mail clients strip or ignore `<style>` blocks with
enough regularity that a stylesheet is not worth relying on, and an unstyled
`<table>` renders borderless with collapsed spacing. The render rules below
attach `style=` attributes directly to the elements that need them.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markupsafe import Markup

#: Inline styles for the elements whose default rendering is unacceptable in an
#: email. Kept deliberately small — headings, paragraphs and lists look fine
#: unstyled, and every rule here is one more thing to maintain.
_TABLE_STYLE = "border-collapse:collapse;width:100%;margin:16px 0;font-size:14px"
_TH_STYLE = "border:1px solid #d1d5db;padding:6px 10px;background:#f3f4f6;text-align:left;font-weight:600"
_TD_STYLE = "border:1px solid #d1d5db;padding:6px 10px;vertical-align:top"
_PRE_STYLE = "background:#f3f4f6;padding:12px;border-radius:6px;overflow-x:auto;font-size:13px"
_CODE_STYLE = "background:#f3f4f6;padding:2px 4px;border-radius:3px;font-size:13px"
_BLOCKQUOTE_STYLE = "border-left:3px solid #d1d5db;margin:16px 0;padding:0 0 0 16px;color:#4b5563"

#: The wrapper keeps the report visually distinct from whatever surrounds it in
#: the template, and gives one place to set a readable base font.
_WRAPPER_STYLE = "font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:14px;line-height:1.6;color:#374151"


def _styled(tag: str, style: str):
    """A render rule that emits `<tag style="...">`, preserving nothing else.

    Sound for the tags used here because none of them carry markdown-authored
    attributes — a GFM table cell has alignment at most, which is handled
    separately below.
    """

    def rule(self, tokens, idx, options, env):  # noqa: ANN001 — markdown-it's rule signature
        return f'<{tag} style="{style}">'

    return rule


def _td_rule(tag: str, base: str):
    """Cell rule that honours GFM column alignment.

    markdown-it puts alignment in the token's `style` attr (`text-align:right`).
    Dropping it would silently left-align every numeric column in a report.
    """

    def rule(self, tokens, idx, options, env):  # noqa: ANN001
        token = tokens[idx]
        align = token.attrGet("style") or ""
        style = f"{base};{align}" if align else base
        return f'<{tag} style="{style}">'

    return rule


def _build_renderer() -> MarkdownIt:
    md = MarkdownIt(
        "gfm-like",
        {
            # Not the default. See the module docstring.
            "html": False,
            # Off because it needs the optional `linkify-it-py` package, which
            # is not a dependency. Explicit URLs in a report still render as
            # links via normal markdown link syntax.
            "linkify": False,
            "typographer": False,
        },
    )
    md.add_render_rule("table_open", _styled("table", _TABLE_STYLE))
    md.add_render_rule("th_open", _td_rule("th", _TH_STYLE))
    md.add_render_rule("td_open", _td_rule("td", _TD_STYLE))
    md.add_render_rule("blockquote_open", _styled("blockquote", _BLOCKQUOTE_STYLE))
    md.add_render_rule("code_inline", _code_inline_rule)
    md.add_render_rule("fence", _fence_rule)
    md.add_render_rule("code_block", _fence_rule)
    return md


def _code_inline_rule(self, tokens, idx, options, env):  # noqa: ANN001
    from markdown_it.common.utils import escapeHtml

    return f'<code style="{_CODE_STYLE}">{escapeHtml(tokens[idx].content)}</code>'


def _fence_rule(self, tokens, idx, options, env):  # noqa: ANN001
    """Code blocks without syntax highlighting.

    The default fence renderer would add a language class for a highlighter that
    is not present in an email anyway; escaping the content and styling the
    `<pre>` is the whole job.
    """
    from markdown_it.common.utils import escapeHtml

    return f'<pre style="{_PRE_STYLE}"><code>{escapeHtml(tokens[idx].content)}</code></pre>\n'


_RENDERER = _build_renderer()


def markdown_to_html(source: str) -> Markup:
    """Render `source` as HTML, wrapped and safe to inject into a template.

    Returns `Markup` rather than `str` because `_render_body` turns Jinja
    autoescaping ON for `format="html"` templates. A plain string would arrive
    at the recipient as visible `&lt;table&gt;` tags. Marking it safe is
    justified by the escaping done during conversion, not in spite of it — every
    byte of the source has been through markdown-it with `html=False`.

    An empty source produces empty output rather than an empty wrapper, so
    `{% if context.ai_report.html %}` behaves the way a template author expects.
    """
    if not source or not source.strip():
        return Markup("")
    return Markup(f'<div style="{_WRAPPER_STYLE}">{_RENDERER.render(source)}</div>')
