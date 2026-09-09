"""Main JavaScript for DFX Dashboard"""

// API health check
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        console.log('API Health:', data);
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Load supported formats
async function loadFormats() {
    try {
        const response = await fetch('/api/formats');
        const formats = await response.json();
        console.log('Supported Formats:', formats);
    } catch (error) {
        console.error('Failed to load formats:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadFormats();
});
