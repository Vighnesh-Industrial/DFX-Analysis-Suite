"""Design for Serviceability (DFS) Analyzer"""

RULE = "=" * 74

SEVERITY_TAG = {'CRITICAL': '[CRIT]', 'WARNING': '[WARN]', 'INFO': '[INFO]'}

# Above this a part is a two-person lift under most manual handling rules.
TWO_PERSON_LIFT_G = 20000.0
ONE_HAND_LIFT_G = 5000.0


class DFSAnalyzer:
    """Analyzes assemblies for serviceability and maintenance accessibility."""

    def __init__(self, min_tool_clearance_mm=15.0):
        self.serviceability_issues = []
        self.modularity_score = 0
        self.accessibility_score = 0
        self.min_tool_clearance = min_tool_clearance_mm
        self._score = None

    def add_issue(self, component_name, issue_type, message, recommendation,
                  severity='WARNING'):
        """Record serviceability issue"""
        self.serviceability_issues.append({
            'Component': component_name,
            'Issue': issue_type,
            'Type': severity,
            'Message': message,
            'Recommendation': recommendation
        })

    # -------------------------------------------------------------- analysis

    def analyze(self, geom=None, params=None, part_name=None):
        """Assess serviceability from geometry plus the supplied parameters.

        Serviceability is largely an assembly-level property, so this uses
        the answers given in ``params`` (fastener count, tool clearance,
        mass) and sharpens them with whatever the CAD file can confirm.
        """
        params = params or {}
        name = part_name or (geom.product_name if geom else None) or 'Component'

        deductions = 0.0

        fasteners = int(params.get('num_fasteners', 0) or 0)
        if fasteners > 4:
            deductions += min(2.0, (fasteners - 4) * 0.5)
            self.add_issue(
                name, 'Fastener count',
                '%d fasteners must be removed to service this component.'
                % fasteners,
                'Reduce the count, or switch to captive or quarter-turn '
                'fasteners so nothing is dropped during service.')
        elif fasteners == 0 and not params.get('use_snap_fit'):
            self.add_issue(
                name, 'Retention not stated',
                'No fasteners and no snap-fit were declared.',
                'Confirm how the part is retained; it affects removal time.',
                severity='INFO')

        clearance = float(params.get('tool_clearance_mm', self.min_tool_clearance) or 0)
        if clearance < self.min_tool_clearance:
            deductions += 2.0
            self.add_issue(
                name, 'Tool clearance',
                'Declared clearance is %.0f mm against a %.0f mm minimum for '
                'a socket or driver.' % (clearance, self.min_tool_clearance),
                'Open up the access envelope, or relocate the fasteners to a '
                'face a technician can reach.',
                severity='CRITICAL' if clearance < self.min_tool_clearance / 2 else 'WARNING')

        mass = self._resolve_mass(geom, params)
        if mass is not None:
            if mass > TWO_PERSON_LIFT_G:
                deductions += 2.0
                self.add_issue(
                    name, 'Handling mass',
                    'Estimated mass %.1f kg exceeds a one-person lift.'
                    % (mass / 1000.0),
                    'Add lifting points or hoist provision, and mark the part '
                    'as a two-person lift in the service manual.',
                    severity='CRITICAL')
            elif mass > ONE_HAND_LIFT_G:
                deductions += 0.5
                self.add_issue(
                    name, 'Handling mass',
                    'Estimated mass %.1f kg needs two hands.' % (mass / 1000.0),
                    'Add a grip feature so the part can be supported while '
                    'the last fastener is removed.')

        if geom is not None and geom.max_dimension and geom.max_dimension > 600:
            deductions += 0.5
            self.add_issue(
                name, 'Removal envelope',
                'Largest dimension is %.0f mm.' % geom.max_dimension,
                'Check that a straight-line removal path of this length '
                'exists in the installed position.')

        parts = int(params.get('num_parts', 1) or 1)
        if parts > 5:
            deductions += 1.0
            self.add_issue(
                name, 'Low modularity',
                '%d separate parts must be handled during service.' % parts,
                'Group the parts into a replaceable module so field service '
                'is a single swap.')

        self.modularity_score = max(0.0, 10.0 - max(0, parts - 1) * 0.8)
        self.accessibility_score = max(0.0, 10.0 - deductions)
        self._score = max(0.0, min(10.0, 10.0 - deductions))
        return self

    def _resolve_mass(self, geom, params):
        """Prefer a mass computed from real volume; fall back to the answer given."""
        if geom is not None:
            density = float(params.get('density_g_cm3', 7.85) or 7.85)
            measured = geom.estimated_mass_g(density)
            if measured is not None:
                return measured
        stated = params.get('part_mass_g')
        return float(stated) if stated not in (None, '') else None

    # ---------------------------------------------------------------- report

    def generate_dfs_report(self, overall_score=None):
        """Generate Design for Serviceability report"""
        if overall_score is None:
            overall_score = self._score if self._score is not None else 7.5

        report = "\n%s\nDFS ANALYSIS REPORT\nDesign for Serviceability\n%s\n" % (RULE, RULE)
        report += "\nOverall Serviceability Score: %.1f/10   (%s)\n" % (
            overall_score, self._get_serviceability_rating(overall_score))
        report += "  Accessibility: %.1f/10    Modularity: %.1f/10\n" % (
            self.accessibility_score, self.modularity_score)

        report += "\nISSUES FOUND (%d):\n" % len(self.serviceability_issues)
        if not self.serviceability_issues:
            report += "  [OK]   No serviceability issues found in the checks that could be run.\n"

        for issue in self.serviceability_issues:
            tag = SEVERITY_TAG.get(issue['Type'], '[WARN]')
            report += "\n  %s %s - %s\n" % (
                tag, issue.get('Component', ''), issue['Issue'])
            report += "         %s\n" % issue['Message']
            report += "         Action:   %s\n" % issue['Recommendation']

        return report + "\n"

    def _get_serviceability_rating(self, score):
        if score >= 8:
            return "EXCELLENT - easy to service"
        if score >= 6:
            return "GOOD - moderate serviceability"
        if score >= 4:
            return "FAIR - some service challenges"
        return "POOR - difficult to service"
