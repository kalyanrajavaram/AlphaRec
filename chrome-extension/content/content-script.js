// Content Script for Google Search Tracking and Page Interaction

// Send page title to background script
function sendPageTitle() {
  chrome.runtime.sendMessage({
    type: 'page_title',
    title: document.title
  });
}

// Extract search query from Google URL
function extractGoogleSearchQuery() {
  const url = new URL(window.location.href);

  // Check if this is a Google search page
  if (url.hostname.includes('google.com') && url.pathname.includes('/search')) {
    const query = url.searchParams.get('q');
    if (query) {
      chrome.runtime.sendMessage({
        type: 'search_query',
        query: decodeURIComponent(query)
      });
      return query;
    }
  }

  return null;
}

// Track search result clicks
function trackSearchResultClicks() {
  // Check if this is a Google search results page
  if (!window.location.hostname.includes('google.com')) {
    return;
  }

  // Google search result selectors (may need updating as Google changes their HTML)
  const searchResultSelectors = [
    'div.g a[href]:not([href^="#"])', // Standard results
    'div[data-hveid] a[href]:not([href^="#"])', // Alternative selector
    'h3 a[href]' // Heading links
  ];

  let position = 0;

  searchResultSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach((link) => {
      // Skip if already tracked
      if (link.dataset.tracked) return;

      link.dataset.tracked = 'true';
      position++;

      link.addEventListener('click', (event) => {
        const resultUrl = link.href;
        let resultTitle = '';

        // Try to get title from h3 or link text
        const h3 = link.querySelector('h3') || link.closest('h3') || link.parentElement.querySelector('h3');
        if (h3) {
          resultTitle = h3.textContent;
        } else {
          resultTitle = link.textContent;
        }

        chrome.runtime.sendMessage({
          type: 'search_click',
          url: resultUrl,
          title: resultTitle.trim(),
          position: parseInt(link.dataset.position) || position
        });

        console.log('Search result clicked:', resultTitle, resultUrl);
      });

      // Store position for later reference
      link.dataset.position = position;
    });
  });
}

// Monitor page visibility changes
function setupVisibilityTracking() {
  document.addEventListener('visibilitychange', () => {
    chrome.runtime.sendMessage({
      type: 'page_visibility',
      visible: !document.hidden
    });
  });
}

// Initialize when DOM is ready
function initialize() {
  // Send initial page title
  sendPageTitle();

  // Check for Google search query
  const query = extractGoogleSearchQuery();

  // If this is a Google search page, track clicks
  if (query || window.location.hostname.includes('google.com')) {
    // Initial tracking
    trackSearchResultClicks();

    // Re-track when results are dynamically loaded
    const observer = new MutationObserver((mutations) => {
      // Check if search results were added
      const hasNewResults = mutations.some(mutation =>
        mutation.addedNodes.length > 0
      );

      if (hasNewResults) {
        trackSearchResultClicks();
      }
    });

    // Observe the search results container
    const searchContainer = document.querySelector('#search') ||
                           document.querySelector('#rso') ||
                           document.body;

    if (searchContainer) {
      observer.observe(searchContainer, {
        childList: true,
        subtree: true
      });
    }
  }

  // Setup visibility tracking
  setupVisibilityTracking();
}

// Run when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

// Also track title changes (for SPAs)
const titleObserver = new MutationObserver(() => {
  sendPageTitle();

  // Re-check for search query on title change (handles Google's SPA navigation)
  extractGoogleSearchQuery();
});

titleObserver.observe(document.querySelector('title') || document.head, {
  childList: true,
  subtree: true
});

// ============================================
// User Interaction Tracking (Privacy-Preserving)
// ============================================

// Clipboard events - track event type only, no content
['copy', 'paste', 'cut'].forEach(eventType => {
  document.addEventListener(eventType, () => {
    chrome.runtime.sendMessage({
      type: 'user_interaction',
      interaction_type: `clipboard_${eventType}`,
      data: {}
    });
  });
});

// Keyboard activity - bucketed counts every 30 seconds
let keyCount = 0;
document.addEventListener('keydown', () => keyCount++);

setInterval(() => {
  if (keyCount > 0) {
    let level = 'light';
    if (keyCount > 100) level = 'heavy';
    else if (keyCount > 30) level = 'moderate';

    chrome.runtime.sendMessage({
      type: 'user_interaction',
      interaction_type: 'keyboard_activity',
      data: { level, key_count: keyCount }
    });
    keyCount = 0;
  }
}, 30000);

// Input focus - track when user focuses on input fields
document.addEventListener('focusin', (e) => {
  if (e.target.matches('input, textarea, [contenteditable]')) {
    chrome.runtime.sendMessage({
      type: 'user_interaction',
      interaction_type: 'input_focus',
      data: { input_type: e.target.tagName.toLowerCase() }
    });
  }
});

// File upload - track upload events without capturing filename
document.addEventListener('change', (e) => {
  if (e.target.type === 'file') {
    chrome.runtime.sendMessage({
      type: 'user_interaction',
      interaction_type: 'file_upload',
      data: { file_count: e.target.files?.length || 0 }
    });
  }
});

// Print - track print events
window.addEventListener('beforeprint', () => {
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    interaction_type: 'print',
    data: {}
  });
});
