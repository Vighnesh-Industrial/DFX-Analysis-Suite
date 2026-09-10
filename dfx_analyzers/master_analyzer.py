"""Master Comprehensive DFX Analyzer"""

from datetime import datetime

from .cad_reader import read_cad, read_step_edges
from .dfa_analyzer import DFAAnalyzer
from .dfm_analyzer import DFMAnalyzer
from .dfi_analyzer import DFIAnalyzer
from .dfs_analyzer import DFSAnalyzer

RULE = "=" * 74

# How much each finding costs the composite index, out of 10.
PENALTY = {'violation': 1.5, 'critical': 1.5, 'warning': 0.4}


class ComprehensiveDFXAnalyzer:
    """Master analyzer combining DFA, DFM, DFI, and DFS analyses.

    Unlike a checklist tool, this reads the CAD file first: the DFM and DFI
    findings are driven by geometry measured from the file, while DFA and the
    serviceability answers come from the parameters supplied by the engineer.
    """

    def __init__(self, cad_file_path, process_type='general', component_name=None,
                 pull_direction=(0.0, 0.0, 1.0), progress=None):
        self.cad_file = cad_file_path
        self.process_type = process_type
        self.pull_direction = pull_direction
        self.geometry = read_cad(cad_file_path, progress=progress)
        self._views = None
        self._view_note = None
        self.component_name = (component_name
                               or self.geometry.product_name
                               or self.geometry.file_name
                               or 'Component')
        self.dfa_analyzer = DFAAnalyzer(self.component_name)
        self.dfm_analyzer = DFMAnalyzer(process_type, pull_direction)
        self.dfi_analyzer = DFIAnalyzer()
        self.dfs_analyzer = DFSAnalyzer()
        self.results = {}

    @property
    def subjects(self):
        """What the geometry checks run against.

        An assembly's components, when they could be separated; otherwise the
        model as a whole.
        """
        return self.geometry.components or [self.geometry]

    @property
    def is_assembly(self):
        return len(self.geometry.components) > 1

    def findings_by_component(self):
        """Finding counts per component, keyed by component label."""
        tally = {}
        for subject in self.subjects:
            tally[subject.label] = {'violations': 0, 'warnings': 0,
                                    'critical': 0, 'dfi_warnings': 0}
        for item in self.dfm_analyzer.violations:
            entry = tally.get(item['Part'])
            if entry:
                entry['violations'] += 1
        for item in self.dfm_analyzer.warnings:
            entry = tally.get(item['Part'])
            if entry:
                entry['warnings'] += 1
        for item in self.dfi_analyzer.inspection_issues:
            entry = tally.get(item['Part'])
            if not entry:
                continue
            if item['Type'] == 'CRITICAL':
                entry['critical'] += 1
            elif item['Type'] == 'WARNING':
                entry['dfi_warnings'] += 1
        return tally

    # -------------------------------------------------------------- analysis

    def run_all_analyses(self, component_params):
        """Run DFA, DFM, DFI, DFS for a component"""
        params = dict(component_params or {})
        process = params.pop('process_type', None)
        if process:
            self.process_type = process
            self.dfm_analyzer = DFMAnalyzer(process, self.pull_direction)

        # A STEP assembly states its own part count. Use it unless the caller
        # gave one, and record that it came from the file.
        self.part_count_source = 'supplied'
        measured_parts = self.geometry.part_count
        if not params.get('num_parts') and measured_parts:
            params['num_parts'] = measured_parts
            self.part_count_source = 'measured from the file'

        dfa_params = {k: v for k, v in params.items()
                      if k not in ('density_g_cm3',)}

        # You manufacture and inspect components, not assemblies, so the
        # geometry checks run per component and each finding names the
        # component it came from. Serviceability stays assembly-level.
        for subject in self.subjects:
            self.dfm_analyzer.analyze_geometry(subject, subject.label)
            self.dfi_analyzer.analyze_geometry(subject, subject.label)
        self.dfs_analyzer.analyze(self.geometry, params, self.component_name)

        results = {
            'DFA': self.dfa_analyzer.generate_dfa_report(**dfa_params),
            'DFM': self.dfm_analyzer.generate_dfm_report(),
            'DFI': self.dfi_analyzer.generate_dfi_report(),
            'DFS': self.dfs_analyzer.generate_dfs_report()
        }
        self.results = results
        return results

    def scores(self):
        """Numeric roll-up of the analyses that have been run."""
        dfa_score = (sum(self.dfa_analyzer.scores[k] * self.dfa_analyzer.weight[k]
                         for k in self.dfa_analyzer.scores)
                     if self.dfa_analyzer.scores else None)

        violations = len(self.dfm_analyzer.violations)
        dfm_warnings = len(self.dfm_analyzer.warnings)
        criticals = len([i for i in self.dfi_analyzer.inspection_issues
                         if i['Type'] == 'CRITICAL'])
        dfi_warnings = len([i for i in self.dfi_analyzer.inspection_issues
                            if i['Type'] == 'WARNING'])

        # DFM and DFI are geometry-driven. With nothing measurable in the
        # file there is no score to give: reporting 10 minus a couple of
        # warnings would say the part passed checks that never ran.
        if self.geometry.has_measurable_geometry:
            # For an assembly, score each component and average, so one bad
            # part does not drag three good ones to the floor - and so the
            # number of components does not by itself lower the score.
            per_component = self.findings_by_component()
            dfm_parts = [max(0.0, 10.0 - counts['violations'] * PENALTY['violation']
                             - counts['warnings'] * PENALTY['warning'])
                         for counts in per_component.values()]
            dfi_parts = [max(0.0, 10.0 - counts['critical'] * PENALTY['critical']
                             - counts['dfi_warnings'] * PENALTY['warning'])
                         for counts in per_component.values()]
            dfm_score = sum(dfm_parts) / len(dfm_parts) if dfm_parts else None
            dfi_score = sum(dfi_parts) / len(dfi_parts) if dfi_parts else None
        else:
            dfm_score = None
            dfi_score = None
        dfs_score = self.dfs_analyzer._score

        parts = [s for s in (dfa_score, dfm_score, dfi_score, dfs_score)
                 if s is not None]
        composite = sum(parts) / len(parts) if parts else None

        return {
            'dfa': dfa_score,
            'dfm': dfm_score,
            'dfi': dfi_score,
            'dfs': dfs_score,
            'composite': composite,
            'geometry_measured': self.geometry.has_measurable_geometry,
            'dfm_violations': violations,
            'dfm_warnings': dfm_warnings,
            'dfi_critical': criticals,
            'dfi_warnings': dfi_warnings,
        }

    def to_dict(self, component_params=None):
        """Machine-readable result, for JSON export or the web dashboard."""
        if not self.results:
            self.run_all_analyses(component_params or {})
        return {
            'component': self.component_name,
            'cad_file': self.cad_file,
            'process_type': self.process_type,
            'generated_at': datetime.now().isoformat(timespec='seconds'),
            'geometry': self.geometry.to_dict(),
            'scores': self.scores(),
            'components': self.findings_by_component(),
            'dfm_violations': self.dfm_analyzer.violations,
            'dfm_warnings': self.dfm_analyzer.warnings,
            'dfi_findings': self.dfi_analyzer.inspection_issues,
            'dfs_issues': self.dfs_analyzer.serviceability_issues,
        }

    # ----------------------------------------------------------------- views

    def views(self, names=None):
        """Rendered orthographic views of the part, as SVG.

        Shaded when the file is a mesh, wireframe when it is a STEP B-rep.
        Cached, because reading a STEP file's edges is a second pass over it.
        """
        if self._views is None:
            from .render import render_views, render_note, DEFAULT_VIEWS
            edges = None
            if not self.geometry.triangles and self.geometry.readable:
                edges = read_step_edges(self.cad_file)
            self._views = render_views(self.geometry, edges=edges,
                                       views=names or DEFAULT_VIEWS)
            self._view_note = render_note(self.geometry, edges)
        return self._views

    def view_note(self):
        """Why there are no views, or None when there are."""
        if self._views is None:
            self.views()
        return self._view_note

    # ---------------------------------------------------------------- report

    def _components_section(self):
        """Per-component breakdown, for an assembly."""
        if not self.is_assembly:
            return ''
        tally = self.findings_by_component()
        lines = ["\n%s\nCOMPONENTS\n%s\n" % (RULE, RULE), ""]
        lines.append("  %-24s %-22s %s" % ('Component', 'Envelope (mm)',
                                           'Findings'))
        lines.append("  " + "-" * 70)
        for subject in self.subjects:
            dims = subject.dimensions
            size = ("%.1f x %.1f x %.1f" % dims) if dims else 'not measurable'
            counts = tally.get(subject.label, {})
            findings = ("%d violation(s), %d critical, %d warning(s)"
                        % (counts.get('violations', 0),
                           counts.get('critical', 0),
                           counts.get('warnings', 0)
                           + counts.get('dfi_warnings', 0)))
            lines.append("  %-24s %-22s %s"
                         % (subject.label[:24], size, findings))
        lines.append("")
        lines.append("  Manufacturability and inspection are checked per "
                     "component; every")
        lines.append("  finding below names the component it came from.")
        return "\n".join(lines) + "\n"

    def _geometry_section(self):
        lines = ["\n%s\nMEASURED GEOMETRY\nRead directly from the CAD file\n%s\n" % (RULE, RULE), ""]
        for line in self.geometry.summary_lines():
            lines.append("  " + line)
        walls = self.geometry.wall_draft_angles(self.pull_direction)
        if walls:
            lines.append("  Wall draft:      %.1f to %.1f deg from the %s pull "
                         "direction (%d wall faces)"
                         % (min(walls), max(walls),
                            self.dfm_analyzer._pull_label(), len(walls)))
        if self.geometry.read_notes:
            lines.append("")
            for note in self.geometry.read_notes:
                lines.append("  [NOTE] " + note)
        return "\n".join(lines) + "\n"

    def _summary_section(self):
        scores = self.scores()
        lines = ["\n%s\nSUMMARY\n%s\n" % (RULE, RULE), ""]

        def fmt(value):
            return "%.1f/10" % value if value is not None else "  n/a"

        lines.append("  DFA (assembly, from your answers):   %s" % fmt(scores['dfa']))
        lines.append("  DFM (manufacturability, measured):   %s   %d violation(s), %d warning(s)"
                     % (fmt(scores['dfm']), scores['dfm_violations'], scores['dfm_warnings']))
        lines.append("  DFI (inspection, measured):          %s   %d critical, %d warning(s)"
                     % (fmt(scores['dfi']), scores['dfi_critical'], scores['dfi_warnings']))
        lines.append("  DFS (serviceability):                %s" % fmt(scores['dfs']))
        lines.append("")
        lines.append("  COMPOSITE DFX INDEX:                 %s" % fmt(scores['composite']))
        lines.append("")
        if not scores['geometry_measured']:
            lines.append("  WARNING: no geometry could be measured in this file, so the")
            lines.append("  manufacturability and inspection checks did not run. The index")
            lines.append("  above reflects only the answers you supplied.")
            lines.append("")
        lines.append("  Index = mean of the four scores. DFM and DFI start at 10 and lose")
        lines.append("  %.1f per violation or critical finding and %.1f per warning."
                     % (PENALTY['violation'], PENALTY['warning']))

        blockers = self.dfm_analyzer.violations + [
            i for i in self.dfi_analyzer.inspection_issues if i['Type'] == 'CRITICAL']
        lines.append("")
        if blockers:
            lines.append("  FIX FIRST:")
            for item in blockers:
                lines.append("    - %s: %s" % (
                    item.get('Type') if 'Issue' not in item else item['Issue'],
                    item['Recommendation']))
        else:
            lines.append("  No blocking findings in the checks that could be run.")
        return "\n".join(lines) + "\n"

    def to_html(self, component_params=None, include_views=True):
        """Render the analysis as a self-contained, printable HTML page."""
        from .html_report import build_html
        if not self.results:
            self.run_all_analyses(component_params or {})
        return build_html(self, include_views=include_views)

    def generate_master_report(self, component_params):
        """Generate master DFX report for component"""
        all_results = self.run_all_analyses(component_params)

        header = (
            "\n%s\n"
            "MASTER DFX ANALYSIS REPORT\n"
            "%s\n"
            "%s\n"
            "Component: %s\n"
            "File:      %s\n"
            "Process:   %s\n"
            % (RULE, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), RULE,
               self.component_name, self.cad_file,
               self.process_type.replace('_', ' ')))

        return (header
                + self._geometry_section()
                + self._components_section()
                + all_results['DFA']
                + all_results['DFM']
                + all_results['DFI']
                + all_results['DFS']
                + self._summary_section()
                + "\n" + RULE + "\nEND OF REPORT\n" + RULE + "\n")
