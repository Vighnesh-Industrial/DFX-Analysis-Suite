"""Design for Inspection (DFI) Analyzer"""

RULE = "=" * 74
THIN_RULE = "-" * 74

SEVERITY_TAG = {'CRITICAL': '[CRIT]', 'WARNING': '[WARN]', 'INFO': '[INFO]'}


class DFIAnalyzer:
    """Analyzes components for measurement and inspection feasibility."""

    def __init__(self, probe_diameter_mm=5.0, cmm_clearance_min=15.0,
                 cmm_table_mm=1000.0):
        self.inspection_issues = []
        self.cmm_clearance_min = cmm_clearance_min
        self.probe_diameter = probe_diameter_mm
        self.cmm_table_mm = cmm_table_mm
        # Kept for backwards compatibility with earlier callers.
        self.probe_radius = probe_diameter_mm / 2.0

    # ------------------------------------------------------------- recording

    def add_critical_issue(self, part_name, issue_type, message, recommendation):
        """Record critical inspection issue"""
        self._add(part_name, issue_type, message, recommendation, 'CRITICAL')

    def add_warning(self, part_name, issue_type, message, recommendation):
        """Record inspection warning"""
        self._add(part_name, issue_type, message, recommendation, 'WARNING')

    def add_info(self, part_name, issue_type, message, recommendation):
        """Record inspection information note"""
        self._add(part_name, issue_type, message, recommendation, 'INFO')

    def _add(self, part_name, issue_type, message, recommendation, severity):
        self.inspection_issues.append({
            'Part': part_name,
            'Issue': issue_type,
            'Type': severity,
            'Message': message,
            'Recommendation': recommendation
        })

    # -------------------------------------------------------------- analysis

    def analyze_geometry(self, geom, part_name=None):
        """Run inspection checks against geometry measured from a CAD file."""
        name = part_name or geom.product_name or geom.file_name or 'Component'

        if not geom.readable or not geom.has_measurable_geometry:
            self.add_info(
                name, 'Not inspected',
                '; '.join(geom.read_notes) or 'No geometry available.',
                'Supply a STEP or STL file with solid geometry to run '
                'inspection checks.')
            return self

        self._check_probe_access(geom, name)
        self._check_inspection_effort(geom, name)
        self._check_fixturing(geom, name)
        self._check_source_fidelity(geom, name)
        return self

    def _check_probe_access(self, geom, name):
        diameters = geom.cylindrical_diameters
        if not diameters:
            return
        too_small = [d for d in diameters if d < self.probe_diameter]
        tight = [d for d in diameters
                 if self.probe_diameter <= d < self.probe_diameter * 1.5]
        if too_small:
            self.add_critical_issue(
                name, 'Probe cannot enter',
                'Feature diameters %s mm are smaller than the %.1f mm '
                'standard touch probe.'
                % (', '.join('%.2f' % d for d in too_small), self.probe_diameter),
                'These features cannot be measured on a CMM. Either enlarge '
                'them, accept an optical or pin-gauge check, or mark them '
                'as reference-only on the drawing.')
        if tight:
            self.add_warning(
                name, 'Tight probe access',
                'Feature diameters %s mm leave little clearance around a '
                '%.1f mm probe.'
                % (', '.join('%.2f' % d for d in tight), self.probe_diameter),
                'Specify a smaller stylus, or expect longer cycle times and '
                'higher measurement uncertainty.')

    def _check_inspection_effort(self, geom, name):
        diameters = geom.cylindrical_diameters
        if len(diameters) > 3:
            self.add_warning(
                name, 'Many distinct sizes',
                '%d distinct cylindrical diameters must each be verified.'
                % len(diameters),
                'Consolidate sizes so one gauge covers several features.')
        if geom.face_count > 150:
            self.add_warning(
                name, 'High feature count',
                '%d faces to sample.' % geom.face_count,
                'Agree a sampling plan with quality rather than measuring '
                'every feature.')

    def _check_fixturing(self, geom, name):
        largest = geom.max_dimension
        smallest = geom.min_dimension
        if largest and largest > self.cmm_table_mm:
            self.add_warning(
                name, 'Exceeds CMM table',
                'Largest dimension %.0f mm exceeds the assumed %.0f mm table.'
                % (largest, self.cmm_table_mm),
                'Confirm machine capacity, or plan a two-setup measurement '
                'with a datum transfer.')
        if smallest is not None and smallest < 1.0:
            self.add_warning(
                name, 'Fragile section',
                'Thinnest dimension is %.2f mm.' % smallest,
                'Thin sections deflect under probe force. Reduce probing '
                'force or use non-contact measurement.')

    def _check_source_fidelity(self, geom, name):
        if geom.file_format == 'STL':
            self.add_info(
                name, 'Tessellated source',
                'STL is a faceted approximation, so measurements taken from '
                'it carry the tessellation error, not the true nominal.',
                'Use the STEP model as the dimensional master for inspection '
                'programming.')
        if geom.is_watertight is False:
            self.add_warning(
                name, 'Open mesh',
                'The mesh is not closed, so derived dimensions are unreliable.',
                'Repair the mesh or supply a STEP file.')

    # ---------------------------------------------------------------- report

    def generate_dfi_report(self):
        """Generate DFI analysis report"""
        report = "\n%s\nDFI ANALYSIS REPORT\nDesign for Inspection\n%s\n" % (RULE, RULE)
        report += "\nFINDINGS (%d):\n" % len(self.inspection_issues)

        if not self.inspection_issues:
            report += "  [OK]   No inspection issues found in the checks that could be run.\n"
            return report + "\n"

        for severity in ('CRITICAL', 'WARNING', 'INFO'):
            group = [i for i in self.inspection_issues if i['Type'] == severity]
            if not group:
                continue
            report += "\n%s\n%s (%d):\n" % (THIN_RULE, severity, len(group))
            for issue in group:
                report += "\n  %s %s - %s\n" % (
                    SEVERITY_TAG[severity], issue['Part'], issue['Issue'])
                report += "         %s\n" % issue['Message']
                report += "         Action:   %s\n" % issue['Recommendation']

        return report + "\n"
