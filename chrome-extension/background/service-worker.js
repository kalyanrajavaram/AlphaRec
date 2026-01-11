// Background Service Worker for Activity Tracking

// State management
let currentTab = {
  id: null,
  url: null,
  title: null,
  startTime: null,
  isActive: true
};

let dataQueue = [];
let nativePort = null;
let isTracking = true;
let idleState = 'active';
let pendingStatsCallback = null;

// Constants
const BATCH_INTERVAL = 30000; // 30 seconds
const IDLE_THRESHOLD = 60; // 60 seconds
const HOST_NAME = 'com.airecommender.host';

// Initialize on install
chrome.runtime.onInstalled.addListener(() => {
  console.log('AI Activity Recommender installed');

  // Initialize storage
  chrome.storage.local.set({
    trackingEnabled: true,
    dataRetentionDays: 90
  });

  // Set idle detection threshold
  chrome.idle.setDetectionInterval(IDLE_THRESHOLD);

  // Start native messaging connection
  connectToNativeHost();

  // Start tracking
  initializeTracking();
});

// Initialize tracking on startup
chrome.runtime.onStartup.addListener(() => {
  console.log('Extension started');
  connectToNativeHost();
  initializeTracking();
});

// Connect to native host
function connectToNativeHost() {
  try {
    nativePort = chrome.runtime.connectNative(HOST_NAME);

    nativePort.onMessage.addListener((message) => {
      console.log('Received from native host:', message);

      // Handle stats response
      if (message.status === 'success' && message.sites_visited !== undefined && pendingStatsCallback) {
        pendingStatsCallback(message);
        pendingStatsCallback = null;
      }
    });

    nativePort.onDisconnect.addListener(() => {
      console.error('Native host disconnected:', chrome.runtime.lastError);
      nativePort = null;

      // Try to reconnect after 5 seconds
      setTimeout(connectToNativeHost, 5000);
    });

    // Send initialization message
    sendToNativeHost({
      command: 'start_app_tracking'
    });

    console.log('Connected to native host');
  } catch (error) {
    console.error('Failed to connect to native host:', error);
    // Retry connection after 10 seconds
    setTimeout(connectToNativeHost, 10000);
  }
}

// Initialize tracking
async function initializeTracking() {
  const { trackingEnabled } = await chrome.storage.local.get('trackingEnabled');
  isTracking = trackingEnabled !== false;

  if (isTracking) {
    // Get current active tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      handleTabActivated({ tabId: tabs[0].id });
    }
  }
}

// Tab activated - user switched to a different tab
chrome.tabs.onActivated.addListener((activeInfo) => {
  handleTabActivated(activeInfo);
});

// Tab updated - URL or status changed
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only track when URL changes and page is complete
  if (changeInfo.url && tab.active) {
    handleTabActivated({ tabId });
  }
});

// Handle tab activation
async function handleTabActivated(activeInfo) {
  if (!isTracking) return;

  try {
    // Save current tab data before switching
    if (currentTab.id !== null && currentTab.startTime !== null) {
      await saveCurrentTabData();
    }

    // Get new tab info
    const tab = await chrome.tabs.get(activeInfo.tabId);

    // Don't track incognito tabs
    if (tab.incognito) {
      currentTab = { id: null, url: null, title: null, startTime: null, isActive: false };
      return;
    }

    // Update current tab
    currentTab = {
      id: tab.id,
      url: tab.url,
      title: tab.title,
      startTime: Date.now(),
      isActive: idleState === 'active'
    };

  } catch (error) {
    console.error('Error handling tab activation:', error);
  }
}

// Save current tab data
async function saveCurrentTabData() {
  if (!currentTab.url || currentTab.url.startsWith('chrome://')) {
    return; // Skip chrome internal pages
  }

  const now = Date.now();
  const duration = Math.floor((now - currentTab.startTime) / 1000); // seconds

  if (duration < 1) return; // Skip very short visits

  const visitData = {
    url: currentTab.url,
    title: currentTab.title,
    visit_time: new Date(currentTab.startTime).toISOString(),
    leave_time: new Date(now).toISOString(),
    duration_seconds: duration,
    tab_id: currentTab.id,
    is_active: currentTab.isActive,
    active_duration_seconds: currentTab.isActive ? duration : 0
  };

  // Add to queue
  dataQueue.push({
    type: 'browsing_history',
    data: visitData
  });

  console.log('Saved tab data:', visitData);
}

// Web navigation completed - page finished loading
chrome.webNavigation.onCompleted.addListener((details) => {
  if (details.frameId === 0) { // Main frame only
    chrome.tabs.get(details.tabId, (tab) => {
      if (chrome.runtime.lastError) return;

      // Update title if this is the current tab
      if (currentTab.id === tab.id) {
        currentTab.title = tab.title;
      }
    });
  }
});

// Navigation committed - capture transition type
chrome.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId !== 0) return; // Main frame only
  if (!isTracking) return;
  if (details.url.startsWith('chrome://')) return;

  dataQueue.push({
    type: 'navigation_event',
    data: {
      url: details.url,
      tab_id: details.tabId,
      transition_type: details.transitionType,
      transition_qualifiers: JSON.stringify(details.transitionQualifiers || []),
      is_spa_navigation: false,
      event_time: new Date().toISOString()
    }
  });
});

// SPA navigation - history state updated
chrome.webNavigation.onHistoryStateUpdated.addListener((details) => {
  if (details.frameId !== 0) return;
  if (!isTracking) return;
  if (details.url.startsWith('chrome://')) return;

  dataQueue.push({
    type: 'navigation_event',
    data: {
      url: details.url,
      tab_id: details.tabId,
      transition_type: 'history_state',
      transition_qualifiers: '[]',
      is_spa_navigation: true,
      event_time: new Date().toISOString()
    }
  });
});

// Tab created - capture opener relationship
chrome.tabs.onCreated.addListener((tab) => {
  if (!isTracking) return;
  if (tab.openerTabId) {
    dataQueue.push({
      type: 'navigation_event',
      data: {
        url: tab.pendingUrl || tab.url || '',
        tab_id: tab.id,
        opener_tab_id: tab.openerTabId,
        transition_type: 'new_tab',
        transition_qualifiers: '[]',
        is_spa_navigation: false,
        event_time: new Date().toISOString()
      }
    });
  }
});

// Download tracking
chrome.downloads.onCreated.addListener((downloadItem) => {
  if (!isTracking) return;

  dataQueue.push({
    type: 'download',
    data: {
      filename: downloadItem.filename,
      url: downloadItem.url,
      mime_type: downloadItem.mime,
      file_size: downloadItem.fileSize,
      download_time: new Date().toISOString()
    }
  });
});

// Bookmark tracking
chrome.bookmarks.onCreated.addListener((id, bookmark) => {
  if (!isTracking) return;

  dataQueue.push({
    type: 'bookmark',
    data: {
      url: bookmark.url,
      title: bookmark.title,
      bookmark_time: new Date().toISOString()
    }
  });
});

// Idle state changed
chrome.idle.onStateChanged.addListener((state) => {
  console.log('Idle state changed:', state);
  idleState = state;

  if (state === 'idle' || state === 'locked') {
    // User went idle - save current tab
    if (currentTab.id !== null && currentTab.startTime !== null) {
      saveCurrentTabData();
      currentTab.isActive = false;
    }
  } else if (state === 'active') {
    // User became active again
    if (currentTab.id !== null) {
      currentTab.isActive = true;
      currentTab.startTime = Date.now(); // Restart timer
    }
  }
});

// Listen for messages from content scripts and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'page_title') {
    // Update title for current tab
    if (sender.tab && currentTab.id === sender.tab.id) {
      currentTab.title = message.title;
    }
  } else if (message.type === 'search_query') {
    // Save search query
    dataQueue.push({
      type: 'search_query',
      data: {
        query: message.query,
        search_engine: 'google',
        search_time: new Date().toISOString(),
        url: sender.tab.url
      }
    });
    console.log('Saved search query:', message.query);
  } else if (message.type === 'search_click') {
    // Save search result click
    dataQueue.push({
      type: 'search_click',
      data: {
        result_url: message.url,
        result_title: message.title,
        result_position: message.position,
        click_time: new Date().toISOString()
      }
    });
    console.log('Saved search click:', message.url);
  } else if (message.type === 'page_visibility') {
    // Page visibility changed
    if (currentTab.id === sender.tab.id) {
      currentTab.isActive = message.visible && idleState === 'active';
    }
  } else if (message.type === 'user_interaction') {
    // User interaction from content script
    dataQueue.push({
      type: 'user_interaction',
      data: {
        url: sender.tab?.url || '',
        tab_id: sender.tab?.id,
        interaction_type: message.interaction_type,
        interaction_data: JSON.stringify(message.data || {}),
        event_time: new Date().toISOString()
      }
    });
  } else if (message.type === 'get_stats') {
    // Request stats from native host
    if (nativePort) {
      pendingStatsCallback = sendResponse;
      sendToNativeHost({ command: 'get_stats' });
      return true; // Keep channel open for async response
    } else {
      sendResponse({ status: 'error', message: 'Native host not connected' });
    }
  } else if (message.type === 'update_tracking') {
    // Update tracking enabled state
    isTracking = message.enabled;
    sendToNativeHost({
      command: 'update_settings',
      settings: { tracking_enabled: message.enabled }
    });
    sendResponse({ status: 'ok' });
  } else if (message.type === 'export_data') {
    // Trigger data export
    sendToNativeHost({ command: 'export_data' });
    sendResponse({ status: 'ok' });
  } else if (message.type === 'clear_data') {
    // Clear all data
    sendToNativeHost({ command: 'clear_data' });
    sendResponse({ status: 'ok' });
  }

  return true; // Keep message channel open for async response
});

// Send data to native host
function sendToNativeHost(message) {
  if (nativePort) {
    try {
      nativePort.postMessage(message);
    } catch (error) {
      console.error('Error sending to native host:', error);
      // Try to reconnect
      connectToNativeHost();
    }
  } else {
    console.warn('Native host not connected');
  }
}

// Batch send data periodically
setInterval(() => {
  if (dataQueue.length > 0 && isTracking) {
    const batch = [...dataQueue];
    dataQueue = [];

    sendToNativeHost({
      command: 'save_browser_data',
      data: batch
    });

    console.log('Sent batch of', batch.length, 'items');
  }
}, BATCH_INTERVAL);

// Periodic alarm to keep service worker alive
chrome.alarms.create('keepAlive', { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepAlive') {
    // Check if we need to save current tab data
    if (currentTab.id !== null && currentTab.startTime !== null) {
      const elapsed = (Date.now() - currentTab.startTime) / 1000;
      // If user has been on same page for more than 5 minutes, save intermediate data
      if (elapsed > 300) {
        saveCurrentTabData();
        currentTab.startTime = Date.now(); // Reset timer
      }
    }
  }
});

// Save data when extension is suspended
chrome.runtime.onSuspend.addListener(() => {
  console.log('Service worker suspending');
  if (currentTab.id !== null && currentTab.startTime !== null) {
    saveCurrentTabData();
  }

  // Send any remaining queued data
  if (dataQueue.length > 0) {
    sendToNativeHost({
      command: 'save_browser_data',
      data: dataQueue
    });
  }
});
