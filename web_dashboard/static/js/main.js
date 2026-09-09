// Main JavaScript for the DFX Analysis Suite dashboard.

async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        console.log('API health:', await response.json());
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Show which of the accepted formats can actually be measured, so nobody
// uploads a Creo .prt expecting geometry checks to run.
async function loadFormats() {
    const target = document.getElementById('formatNote');
    if (!target) {
        return;
    }
    try {
        const response = await fetch('/api/formats');
        const data = await response.json();
        const measurable = data.formats.filter(f => f.measurable)
            .map(f => f.extension).join(', ');
        const other = data.formats.filter(f => !f.measurable)
            .map(f => f.extension).join(', ');
        target.textContent =
            'Geometry is measured from: ' + measurable +
            '. Accepted but not measurable without export: ' + other + '.';
    } catch (error) {
        console.error('Failed to load formats:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadFormats();
});
