// AI Chat Downloader - Popup Script
// Handles UI interactions and communicates with content/background scripts

document.addEventListener('DOMContentLoaded', () => {
  const btnScan = document.getElementById('btn-scan');
  const btnDownloadAll = document.getElementById('btn-download-all');
  const btnDownloadCurrent = document.getElementById('btn-download-current');
  const progressSection = document.getElementById('progress-section');
  const progressBar = document.getElementById('progress-bar');
  const statusText = document.getElementById('status-text');
  const logArea = document.getElementById('log-area');
  const outputFormat = document.getElementById('output-format');
  const outputDir = document.getElementById('output-dir');
  const includeMetadata = document.getElementById('include-metadata');

  let currentPlatform = null;
  let detectedPlatform = null;

  // Platform detection patterns
  const PLATFORMS = {
    chatgpt: { patterns: ['chat.openai.com', 'chatgpt.com'], name: 'ChatGPT' },
    gemini: { patterns: ['gemini.google.com'], name: 'Gemini' },
    deepseek: { patterns: ['chat.deepseek.com'], name: 'DeepSeek' },
    zai: { patterns: ['chat.zai.com'], name: 'ZAI' },
    grok: { patterns: ['grok.x.ai'], name: 'Grok' },
    perplexity: { patterns: ['www.perplexity.ai', 'perplexity.ai'], name: 'Perplexity' }
  };

  // Load saved settings
  chrome.storage.sync.get(['outputFormat', 'outputDir', 'includeMetadata'], (data) => {
    if (data.outputFormat) outputFormat.value = data.outputFormat;
    if (data.outputDir) outputDir.value = data.outputDir;
    if (data.includeMetadata) includeMetadata.value = data.includeMetadata;
  });

  // Save settings on change
  const saveSettings = () => {
    chrome.storage.sync.set({
      outputFormat: outputFormat.value,
      outputDir: outputDir.value,
      includeMetadata: includeMetadata.value
    });
  };
  outputFormat.addEventListener('change', saveSettings);
  outputDir.addEventListener('input', saveSettings);
  includeMetadata.addEventListener('change', saveSettings);

  // Logging
  function log(message, type = 'info') {
    logArea.classList.add('visible');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const ts = new Date().toLocaleTimeString();
    entry.textContent = `[${ts}] ${message}`;
    logArea.appendChild(entry);
    logArea.scrollTop = logArea.scrollHeight;
  }

  function showProgress(show) {
    progressSection.classList.toggle('visible', show);
  }

  function setProgress(percent, text) {
    progressBar.style.width = percent + '%';
    if (text) statusText.textContent = text;
  }

  function setActivePlatform(platform) {
    Object.keys(PLATFORMS).forEach(p => {
      const dot = document.getElementById(`dot-${p}`);
      const badge = document.getElementById(`badge-${p}`);
      if (p === platform) {
        dot.classList.remove('inactive');
        dot.classList.add('active');
        badge.textContent = 'Active';
        badge.classList.add('current');
      } else {
        dot.classList.remove('active');
        dot.classList.add('inactive');
        badge.textContent = '—';
        badge.classList.remove('current');
      }
    });
  }

  // Detect current platform from active tab
  async function detectPlatform() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url) return null;

      for (const [key, config] of Object.entries(PLATFORMS)) {
        for (const pattern of config.patterns) {
          if (tab.url.includes(pattern)) {
            return key;
          }
        }
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  // Send message to content script
  function sendToContent(message) {
    return new Promise((resolve, reject) => {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) return reject(new Error('No active tab'));
        chrome.tabs.sendMessage(tabs[0].id, message, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(response);
          }
        });
      });
    });
  }

  // Send message to background
  function sendToBackground(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
  }

  // Scan button click
  btnScan.addEventListener('click', async () => {
    log('Scanning active tab...', 'info');
    btnScan.disabled = true;
    setProgress(10, 'Detecting platform...');
    showProgress(true);

    try {
      const platform = await detectPlatform();
      if (!platform) {
        log('No supported AI platform detected in current tab', 'error');
        setProgress(100, 'No platform detected');
        showProgress(false);
        btnScan.disabled = false;
        return;
      }

      currentPlatform = platform;
      setActivePlatform(platform);
      log(`Detected: ${PLATFORMS[platform].name}`, 'success');
      setProgress(30, `Querying ${PLATFORMS[platform].name}...`);

      // Ask content script to scan
      const scanResult = await sendToContent({
        action: 'scan',
        platform: platform
      });

      if (scanResult && scanResult.success) {
        detectedPlatform = scanResult;
        const chatCount = scanResult.chatCount || 0;
        log(`Found ${chatCount} conversations`, 'success');

        // Update badge
        const badge = document.getElementById(`badge-${platform}`);
        badge.textContent = `${chatCount} chats`;

        setProgress(100, `Found ${chatCount} conversations`);
        btnDownloadAll.disabled = chatCount === 0;
        btnDownloadCurrent.disabled = false;
      } else {
        const error = scanResult ? scanResult.error : 'No response from content script';
        log(`Scan error: ${error}`, 'error');
        setProgress(100, 'Scan failed');
      }
    } catch (e) {
      log(`Error: ${e.message}`, 'error');
      setProgress(100, 'Error occurred');
    }

    btnScan.disabled = false;
    setTimeout(() => showProgress(false), 2000);
  });

  // Download All Chats
  btnDownloadAll.addEventListener('click', async () => {
    if (!currentPlatform) return;
    log('Starting download of all chats...', 'info');
    showProgress(true);
    btnDownloadAll.disabled = true;
    setProgress(5, 'Initializing download...');

    try {
      // Tell content script to extract all chats
      const extractResult = await sendToContent({
        action: 'extractAll',
        platform: currentPlatform,
        settings: {
          format: outputFormat.value,
          outputDir: outputDir.value,
          includeMetadata: includeMetadata.value === 'yes'
        }
      });

      if (extractResult && extractResult.success) {
        const totalChats = extractResult.chats ? extractResult.chats.length : 0;
        log(`Extracted ${totalChats} chats, saving...`, 'success');

        // Send to background for download orchestration
        setProgress(50, 'Saving files...');
        const downloadResult = await sendToBackground({
          action: 'downloadChats',
          chats: extractResult.chats,
          platform: currentPlatform,
          settings: {
            format: outputFormat.value,
            outputDir: outputDir.value,
            includeMetadata: includeMetadata.value === 'yes'
          }
        });

        if (downloadResult && downloadResult.success) {
          setProgress(100, `Downloaded ${totalChats} chats!`);
          log(`Successfully saved ${totalChats} chat files`, 'success');
        } else {
          log('Download failed: ' + (downloadResult ? downloadResult.error : 'No response'), 'error');
          setProgress(100, 'Download failed');
        }
      } else {
        const error = extractResult ? extractResult.error : 'Extraction failed';
        log(`Extraction error: ${error}`, 'error');
        setProgress(100, 'Extraction failed');
      }
    } catch (e) {
      log(`Error: ${e.message}`, 'error');
      setProgress(100, 'Error occurred');
    }

    btnDownloadAll.disabled = false;
    setTimeout(() => showProgress(false), 3000);
  });

  // Download Current Chat
  btnDownloadCurrent.addEventListener('click', async () => {
    if (!currentPlatform) return;
    log('Downloading current chat...', 'info');
    showProgress(true);
    btnDownloadCurrent.disabled = true;
    setProgress(20, 'Extracting current conversation...');

    try {
      const extractResult = await sendToContent({
        action: 'extractCurrent',
        platform: currentPlatform,
        settings: {
          format: outputFormat.value,
          includeMetadata: includeMetadata.value === 'yes'
        }
      });

      if (extractResult && extractResult.success) {
        log('Current chat extracted, saving...', 'success');
        setProgress(70, 'Saving file...');

        const downloadResult = await sendToBackground({
          action: 'downloadChats',
          chats: [extractResult.chat],
          platform: currentPlatform,
          settings: {
            format: outputFormat.value,
            outputDir: outputDir.value,
            includeMetadata: includeMetadata.value === 'yes'
          }
        });

        if (downloadResult && downloadResult.success) {
          setProgress(100, 'Downloaded current chat!');
          log('Current chat saved successfully', 'success');
        } else {
          log('Download failed', 'error');
          setProgress(100, 'Download failed');
        }
      } else {
        log('Could not extract current chat: ' + (extractResult ? extractResult.error : 'No response'), 'error');
        setProgress(100, 'Extraction failed');
      }
    } catch (e) {
      log(`Error: ${e.message}`, 'error');
      setProgress(100, 'Error occurred');
    }

    btnDownloadCurrent.disabled = false;
    setTimeout(() => showProgress(false), 3000);
  });

  // Auto-detect on open
  detectPlatform().then(platform => {
    if (platform) {
      currentPlatform = platform;
      setActivePlatform(platform);
      log(`Auto-detected: ${PLATFORMS[platform].name}`, 'success');
      btnDownloadCurrent.disabled = false;
      btnScan.click();
    } else {
      log('Navigate to an AI chat platform to begin', 'info');
    }
  });
});
