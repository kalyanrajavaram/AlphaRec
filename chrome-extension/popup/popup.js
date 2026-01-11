// Popup UI Logic

// Elements
const statusIndicator = document.getElementById('statusIndicator');
const trackingToggle = document.getElementById('trackingToggle');
const sitesVisited = document.getElementById('sitesVisited');
const timeTracked = document.getElementById('timeTracked');
const searchQueries = document.getElementById('searchQueries');
const appsUsed = document.getElementById('appsUsed');
const topSitesList = document.getElementById('topSitesList');
const exportBtn = document.getElementById('exportBtn');
const clearBtn = document.getElementById('clearBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    loadStats();

    // Set up event listeners
    trackingToggle.addEventListener('change', handleTrackingToggle);
    exportBtn.addEventListener('click', handleExport);
    clearBtn.addEventListener('click', handleClearData);
});

// Load settings from storage
async function loadSettings() {
    try {
        const { trackingEnabled } = await chrome.storage.local.get('trackingEnabled');
        trackingToggle.checked = trackingEnabled !== false;
        updateStatusIndicator(trackingEnabled !== false);
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Load statistics from native host
function loadStats() {
    // Request stats from background script
    chrome.runtime.sendMessage({ type: 'get_stats' }, (response) => {
        if (chrome.runtime.lastError) {
            console.error('Error getting stats:', chrome.runtime.lastError);
            showError();
            return;
        }

        if (response && response.status === 'success') {
            updateStatsUI(response);
        } else {
            showError();
        }
    });
}

// Update status indicator
function updateStatusIndicator(isActive) {
    if (isActive) {
        statusIndicator.textContent = 'Active';
        statusIndicator.className = 'status-badge active';
    } else {
        statusIndicator.textContent = 'Inactive';
        statusIndicator.className = 'status-badge inactive';
    }
}

// Handle tracking toggle
async function handleTrackingToggle(event) {
    const enabled = event.target.checked;

    // Save to storage
    await chrome.storage.local.set({ trackingEnabled: enabled });

    // Update UI
    updateStatusIndicator(enabled);

    // Send message to background script
    chrome.runtime.sendMessage({
        type: 'update_tracking',
        enabled: enabled
    });
}

// Update statistics UI
function updateStatsUI(data) {
    // Update stat cards
    sitesVisited.textContent = data.sites_visited || 0;
    searchQueries.textContent = data.search_queries || 0;
    appsUsed.textContent = data.applications_used || 0;

    // Format time
    const seconds = data.total_time_seconds || 0;
    timeTracked.textContent = formatTime(seconds);

    // Update top sites
    if (data.top_sites && data.top_sites.length > 0) {
        topSitesList.innerHTML = data.top_sites.map(site => createSiteItem(site)).join('');
    } else {
        topSitesList.innerHTML = '<p class="no-data">No sites visited today</p>';
    }
}

// Create site item HTML
function createSiteItem(site) {
    const domain = extractDomain(site.url);
    const time = formatTime(site.time);
    const title = site.title || domain;

    return `
        <div class="site-item">
            <div class="site-info">
                <div class="site-title">${escapeHtml(title)}</div>
                <div class="site-url">${escapeHtml(domain)}</div>
            </div>
            <div class="site-time">${time}</div>
        </div>
    `;
}

// Format seconds to readable time
function formatTime(seconds) {
    if (seconds < 60) {
        return `${seconds}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        return `${minutes}m`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

// Extract domain from URL
function extractDomain(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch (e) {
        return url;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show error state
function showError() {
    statusIndicator.textContent = 'Error';
    statusIndicator.className = 'status-badge';
    sitesVisited.textContent = '-';
    timeTracked.textContent = '-';
    searchQueries.textContent = '-';
    appsUsed.textContent = '-';
    topSitesList.innerHTML = '<p class="no-data">Unable to load statistics</p>';
}

// Handle export
function handleExport() {
    chrome.runtime.sendMessage({ type: 'export_data' }, (response) => {
        if (response && response.status === 'success') {
            alert('Data exported successfully! Check your project directory for export files.');
        } else {
            alert('Failed to export data. Please check the logs.');
        }
    });
}

// Handle clear data
function handleClearData() {
    const confirmed = confirm(
        'Are you sure you want to clear all tracked data? This cannot be undone.'
    );

    if (confirmed) {
        chrome.runtime.sendMessage({ type: 'clear_data' }, (response) => {
            if (response && response.status === 'success') {
                alert('All data has been cleared.');
                loadStats(); // Reload stats
            } else {
                alert('Failed to clear data. Please check the logs.');
            }
        });
    }
}

// Add message listener for background script updates
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'stats_updated') {
        loadStats();
    }
    sendResponse({ status: 'ok' });
});
