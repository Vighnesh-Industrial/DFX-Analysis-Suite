"""Self-contained HTML report for a DFX study.

The output is a single file with no external assets, so it opens anywhere and
prints straight to PDF from the browser. Written with the standard library
only.
"""

from datetime import datetime
from html import escape

CSS = """
:root {
  --ink: #1a202c; --muted: #4a5568; --line: #e2e8f0; --bg: #ffffff;
  --good: #2f855a; --fair: #b7791f; --poor: #c53030; --accent: #3c5ccf;
}
* { box-sizing: border-box; }
body { margin: 0; padding: 2rem; background: #f7fafc; color: var(--ink);
       font: 15px/1.55 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
.sheet { max-width: 900px; margin: 0 auto; background: var(--bg);
         padding: 2.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
h2 { font-size: 1.05rem; text-transform: uppercase; letter-spacing: .06em;
     color: var(--muted); margin: 2.25rem 0 .75rem; padding-bottom: .4rem;
     border-bottom: 1px solid var(--line); }
.sub { color: var(--muted); margin: 0 0 1.5rem; font-size: .9rem; }
.scores { display: flex; flex-wrap: wrap; gap: .75rem; margin: 1.5rem 0; }
.tile { flex: 1 1 130px; border: 1px solid var(--line); border-top: 3px solid var(--accent);
        border-radius: 6px; padding: .8rem .9rem; }
.tile .k { font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
.tile .v { font-size: 1.6rem; font-weight: 600; }
.tile.good { border-top-color: var(--good); } .tile.good .v { color: var(--good); }
.tile.fair { border-top-color: var(--fair); } .tile.fair .v { color: var(--fair); }
.tile.poor { border-top-color: var(--poor); } .tile.poor .v { color: var(--poor); }
table { width: 100%; border-collapse: collapse; margin: .5rem 0 1rem; font-size: .9rem; }
th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--line);
         vertical-align: top; }
th { color: var(--muted); font-weight: 600; width: 34%; }
.finding { border-left: 3px solid var(--line); padding: .6rem .9rem; margin: .6rem 0;
           background: #fafbfc; border-radius: 0 4px 4px 0; }
.finding.fail, .finding.crit { border-left-color: var(--poor); }
.finding.warn { border-left-color: var(--fair); }
.finding.info { border-left-color: var(--accent); }
.tag { display: inline-block; font-size: .68rem; font-weight: 700; letter-spacing: .06em;
       padding: .12rem .45rem; border-radius: 3px; color: #fff; margin-right: .5rem; }
.tag.fail, .tag.crit { background: var(--poor); } .tag.warn { background: var(--fair); }
.tag.info { background: var(--accent); }
.finding .what { font-weight: 600; }
.finding .act { color: var(--muted); margin-top: .3rem; font-size: .88rem; }
.none { color: var(--good); font-size: .9rem; margin: .5rem 0 1rem; }
footer { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--line);
         color: var(--muted); font-size: .8rem; }
@media print {
  body { background: #fff; padding: 0; }
  .sheet { box-shadow: none; max-width: none; padding: 0; }
}
"""


def _band(score):
    if score is None:
        return ''
    if score >= 8:
        return 'good'
    if score >= 6:
        return 'fair'
    return 'poor'


def _tile(label, value):
    shown = '%.1f<span style="font-size:.9rem">/10</span>' % value if value is not None else 'n/a'
    return ('<div class="tile %s"><div class="k">%s</div><div class="v">%s</div></div>'
            % (_band(value), escape(label), shown))


def _finding(tag, title, message, action):
    parts = ['<div class="finding %s">' % tag,
             '<span class="tag %s">%s</span>' % (tag, tag.upper()),
             '<span class="what">%s</span>' % escape(str(title))]
    if message:
        parts.append('<div>%s</div>' % escape(str(message)))
    if action:
        parts.append('<div class="act">%s</div>' % escape(str(action)))
    parts.append('</div>')
    return ''.join(parts)


def _section(title, findings, empty_message):
    html = ['<h2>%s</h2>' % escape(title)]
    if not findings:
        html.append('<p class="none">%s</p>' % escape(empty_message))
    else:
        html.extend(findings)
    return ''.join(html)


def build_html(analyzer):
    """Render a finished :class:`ComprehensiveDFXAnalyzer` as an HTML page."""
    geom = analyzer.geometry
    scores = analyzer.scores()

    tiles = ''.join([
        _tile('Composite DFX', scores['composite']),
        _tile('DFA assembly', scores['dfa']),
        _tile('DFM manufacture', scores['dfm']),
        _tile('DFI inspection', scores['dfi']),
        _tile('DFS service', scores['dfs']),
    ])

    rows = []
    for line in geom.summary_lines():
        if ':' in line:
            key, _, value = line.partition(':')
            rows.append('<tr><th>%s</th><td>%s</td></tr>'
                        % (escape(key.strip()), escape(value.strip())))
        else:
            rows.append('<tr><td colspan="2">%s</td></tr>' % escape(line.strip()))
    geometry_table = '<table>%s</table>' % ''.join(rows)

    notes = ''.join('<div class="finding info"><span class="tag info">NOTE</span>%s</div>'
                    % escape(note) for note in geom.read_notes)

    dfm = ([_finding('fail', '%s: %s' % (v['Type'], v.get('Value', '')),
                     'Required: %s' % v.get('Required', ''), v['Recommendation'])
            for v in analyzer.dfm_analyzer.violations]
           + [_finding('warn', w['Type'], w.get('Message', ''), w['Recommendation'])
              for w in analyzer.dfm_analyzer.warnings]
           + [_finding('info', n['Type'], n.get('Message', ''), n.get('Recommendation', ''))
              for n in getattr(analyzer.dfm_analyzer, 'notes', [])])

    tag_for = {'CRITICAL': 'crit', 'WARNING': 'warn', 'INFO': 'info'}
    dfi = [_finding(tag_for.get(i['Type'], 'info'), i['Issue'],
                    i.get('Message', ''), i['Recommendation'])
           for i in analyzer.dfi_analyzer.inspection_issues]
    dfs = [_finding(tag_for.get(i['Type'], 'warn'), i['Issue'],
                    i.get('Message', ''), i['Recommendation'])
           for i in analyzer.dfs_analyzer.serviceability_issues]

    dfa_rows = ''.join(
        '<tr><th>%s</th><td>%.1f / 10</td></tr>' % (key.replace('_', ' ').title(), value)
        for key, value in (analyzer.dfa_analyzer.scores or {}).items())

    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DFX Report - %(component)s</title>
<style>%(css)s</style></head>
<body><div class="sheet">
<h1>DFX Analysis Report</h1>
<p class="sub">%(component)s &middot; %(process)s &middot; %(generated)s</p>

<div class="scores">%(tiles)s</div>

<h2>Measured geometry</h2>
<p class="sub">Read directly from <code>%(file)s</code>.</p>
%(geometry)s
%(notes)s

%(dfm)s
%(dfi)s
%(dfs)s

<h2>DFA - Design for Assembly</h2>
<p class="sub">These scores come from the parameters supplied, not from the CAD file.</p>
<table>%(dfa_rows)s</table>

<footer>
Generated by the DFX Analysis Suite. Findings marked FAIL or CRIT are blocking.
An empty section means nothing was found by the checks that could be run on this
file - not that every check passed.
</footer>
</div></body></html>
""" % {
        'css': CSS,
        'component': escape(str(analyzer.component_name)),
        'process': escape(analyzer.process_type.replace('_', ' ')),
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'file': escape(str(analyzer.cad_file)),
        'tiles': tiles,
        'geometry': geometry_table,
        'notes': notes,
        'dfm': _section('DFM - Design for Manufacturability', dfm,
                        'No manufacturability findings from the checks that could be run.'),
        'dfi': _section('DFI - Design for Inspection', dfi,
                        'No inspection findings from the checks that could be run.'),
        'dfs': _section('DFS - Design for Serviceability', dfs,
                        'No serviceability findings from the checks that could be run.'),
        'dfa_rows': dfa_rows,
    }
