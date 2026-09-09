"""Design for Manufacturability (DFM) Analyzer"""

# Report text is deliberately plain ASCII.  Windows consoles and file handles
# default to cp1252, which cannot encode box-drawing characters or emoji.
RULE = "=" * 74
THIN_RULE = "-" * 74

# Fallback limits used when a process has no entry of its own.
GENERAL_LIMITS = {
    'min_hole_diameter': 2.0,
    'min_feature_size': 1.0,
    'min_wall_thickness': 1.0,
}


class DFMAnalyzer:
    """Analyzes components for manufacturing feasibility."""

    def __init__(self, process_type='general'):
        self.process = process_type
        self.violations = []
        self.warnings = []

        self.thresholds = {
            'injection_molding': {
                'min_wall_thickness': 1.5,
                'max_wall_thickness': 5.0,
                'min_draft_angle': 1.0,
                'rib_ratio': 0.6,
                'min_fillet_radius': 0.5
            },
            'cnc_machining': {
                'min_hole_diameter': 2.0,
                'min_feature_size': 1.0,
                'corner_radius_ratio': 1.0,
                'min_slot_width': 2.0
            },
            'sheet_metal': {
                'min_bend_radius_ratio': 1.0,
                'min_hole_diameter_ratio': 1.5,
                'min_flange_ratio': 4.0
            },
            '3d_printing': {
                'min_wall_thickness': 1.0,
                'max_overhang_angle': 45,
                'min_feature_size': 0.5
            }
        }

    # ------------------------------------------------------------- recording

    def limits(self):
        """Threshold set for the selected process, with general fallbacks."""
        merged = dict(GENERAL_LIMITS)
        merged.update(self.thresholds.get(self.process, {}))
        return merged

    def add_violation(self, part_name, issue_type, value, required, recommendation):
        """Record a DFM violation"""
        self.violations.append({
            'Part': part_name,
            'Type': issue_type,
            'Value': value,
            'Required': required,
            'Status': 'FAIL',
            'Recommendation': recommendation
        })

    def add_warning(self, part_name, issue_type, message, recommendation):
        """Record a DFM warning"""
        self.warnings.append({
            'Part': part_name,
            'Type': issue_type,
            'Status': 'WARNING',
            'Message': message,
            'Recommendation': recommendation
        })

    # -------------------------------------------------------------- analysis

    def analyze_geometry(self, geom, part_name=None):
        """Run DFM checks against geometry measured from a CAD file.

        Every check is skipped rather than guessed when the underlying
        measurement is unavailable, so an empty result means "nothing found
        in what could be measured", not "the part is fine".
        """
        name = part_name or geom.product_name or geom.file_name or 'Component'

        if not geom.readable:
            self.add_warning(
                name, 'File not analysed',
                '; '.join(geom.read_notes) or 'File could not be read.',
                'Export the model as STEP (AP203/AP214) or STL and re-run.')
            return self
        if not geom.has_measurable_geometry:
            self.add_warning(
                name, 'No geometry',
                '; '.join(geom.read_notes) or 'No solid geometry in file.',
                'Re-export the model including solid geometry.')
            return self

        limits = self.limits()
        self._check_small_features(geom, name, limits)
        self._check_thin_sections(geom, name, limits)
        self._check_tooling_variety(geom, name)
        self._check_process_specifics(geom, name)
        self._check_envelope_and_complexity(geom, name)
        self._check_mesh_quality(geom, name)
        return self

    def _check_small_features(self, geom, name, limits):
        diameter = geom.min_cylindrical_diameter
        if diameter is None:
            return
        floor = limits.get('min_hole_diameter') or limits.get('min_feature_size')
        if floor and diameter < floor:
            self.add_violation(
                name, 'Small cylindrical feature',
                '%.2f mm diameter' % diameter,
                '>= %.2f mm' % floor,
                'A %.2f mm feature needs a fragile small-diameter tool and a '
                'slow peck cycle. Open it up to %.2f mm, or call it out as a '
                'drilled pilot with a separate operation.' % (diameter, floor))

    def _check_thin_sections(self, geom, name, limits):
        thinnest = geom.min_dimension
        if thinnest is None:
            return
        floor = limits.get('min_wall_thickness')
        if floor and thinnest < floor:
            self.add_violation(
                name, 'Thin overall section',
                '%.2f mm' % thinnest,
                '>= %.2f mm' % floor,
                'The part envelope is thinner than the process minimum. '
                'Thicken the section or change process.')

        slenderness = geom.slenderness
        if slenderness and slenderness > 12:
            self.add_warning(
                name, 'Slender part',
                'Longest edge is %.0fx the shortest (%.0f mm vs %.1f mm).'
                % (slenderness, geom.max_dimension, geom.min_dimension),
                'Long thin parts chatter when machined and warp when moulded. '
                'Plan for extra fixturing or a stress-relief step.')

    def _check_tooling_variety(self, geom, name):
        diameters = geom.cylindrical_diameters
        if len(diameters) > 3:
            self.add_warning(
                name, 'Tooling variety',
                '%d distinct cylindrical diameters: %s mm.'
                % (len(diameters), ', '.join('%.2f' % d for d in diameters)),
                'Each distinct diameter is a tool change. Standardise on as '
                'few drill and cutter sizes as the design allows.')

    def _check_process_specifics(self, geom, name):
        if self.process == 'injection_molding':
            if geom.cone_count == 0 and geom.plane_count > 0:
                self.add_warning(
                    name, 'No draft detected',
                    'No conical faces were found, which usually means the '
                    'vertical walls have no draft.',
                    'Add at least %.1f degree of draft to every face parallel '
                    'to the pull direction.'
                    % self.thresholds['injection_molding']['min_draft_angle'])
            if not geom.torus_minor_radii and geom.plane_count >= 6:
                self.add_warning(
                    name, 'Sharp corners',
                    'No fillet (toroidal) faces were found on a part with '
                    '%d planar faces.' % geom.plane_count,
                    'Fillet internal corners to at least R%.1f mm to avoid '
                    'stress risers and to help the melt flow.'
                    % self.thresholds['injection_molding']['min_fillet_radius'])
        elif self.process == 'cnc_machining':
            if not geom.torus_minor_radii and geom.plane_count >= 6:
                self.add_warning(
                    name, 'Sharp internal corners',
                    'No fillet faces were found; a square internal corner '
                    'cannot be produced by a rotating cutter.',
                    'Add a corner radius of at least half the intended cutter '
                    'diameter to every internal corner.')

    def _check_envelope_and_complexity(self, geom, name):
        largest = geom.max_dimension
        if largest and largest > 500:
            self.add_warning(
                name, 'Large envelope',
                'Largest dimension is %.0f mm.' % largest,
                'Confirm the part fits the available machine or mould base '
                'envelope before releasing the design.')
        if geom.face_count > 150:
            self.add_warning(
                name, 'High face count',
                'The model has %d faces.' % geom.face_count,
                'High face counts drive programming and inspection time. '
                'Simplify non-functional detail where possible.')
        if geom.bspline_surface_count:
            self.add_warning(
                name, 'Freeform surfaces',
                '%d freeform (B-spline) faces present.'
                % geom.bspline_surface_count,
                'Freeform faces need 3-axis-plus toolpaths and slow the cycle. '
                'Replace with prismatic geometry where function allows.')

    def _check_mesh_quality(self, geom, name):
        if geom.file_format == 'STL':
            self.add_warning(
                name, 'Tessellated source',
                'A mesh carries no feature data, so the hole size, fillet, '
                'draft and tooling checks could not run. This score reflects '
                'fewer checks, not a cleaner design.',
                'Supply the STEP model to get the full DFM check set.')

        if geom.is_watertight is False:
            self.add_violation(
                name, 'Mesh not watertight',
                'open mesh',
                'closed manifold mesh',
                'The mesh has holes, so it cannot be sliced or quoted '
                'reliably. Repair the mesh or supply a STEP file.')

    # ---------------------------------------------------------------- report

    def generate_dfm_report(self):
        """Generate DFM analysis report"""
        report = "\n%s\nDFM ANALYSIS REPORT (%s)\nDesign for Manufacturability\n%s\n" % (
            RULE, self.process.upper().replace('_', ' '), RULE)

        report += "\nVIOLATIONS (%d):\n" % len(self.violations)
        if not self.violations:
            report += "  [OK]   No violations found in the checks that could be run.\n"
        for item in self.violations:
            report += "\n  [FAIL] %s - %s: %s\n" % (
                item['Part'], item['Type'], item.get('Value', 'N/A'))
            report += "         Required: %s\n" % item.get('Required', 'N/A')
            report += "         Action:   %s\n" % item['Recommendation']

        report += "\n%s\nWARNINGS (%d):\n" % (THIN_RULE, len(self.warnings))
        if not self.warnings:
            report += "  [OK]   No warnings.\n"
        for item in self.warnings:
            report += "\n  [WARN] %s - %s\n" % (item['Part'], item['Type'])
            if item.get('Message'):
                report += "         %s\n" % item['Message']
            report += "         Action:   %s\n" % item['Recommendation']

        return report + "\n"
