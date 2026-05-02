const askBtn = document.getElementById('askBtn');
const result = document.getElementById('result');
const meta = document.getElementById('videoMeta');
const timePill = document.getElementById('timePill');
const apiBaseInput = document.getElementById('apiBase');
const questionInput = document.getElementById('question');

let detected = null;

function formatTime(totalSeconds) {
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
  const m = Math.floor(totalSeconds / 60);
  return `${m}:${s}`;
}

function readVideoState() {
  const video = document.querySelector('video');
  if (!video) return { error: 'No <video> element on this page.' };
  const url = location.href;
  return {
    currentTime: video.currentTime,
    url,
    title: document.title.replace(/ - YouTube$/, ''),
  };
}

async function detect() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.includes('youtube.com/watch')) {
      meta.textContent = 'This is not a YouTube watch page.';
      result.textContent = 'Open a youtube.com/watch?v=... tab and reopen this popup.';
      return;
    }
    const [{ result: state } = {}] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readVideoState,
    });
    if (!state || state.error) {
      meta.textContent = state?.error || 'Could not read video state.';
      return;
    }
    detected = state;
    meta.textContent = state.title;
    timePill.textContent = formatTime(state.currentTime);
    result.textContent = 'Type your doubt and click Ask Gemini.';
    askBtn.disabled = false;
  } catch (err) {
    meta.textContent = 'Error: ' + err.message;
  }
}

async function ask() {
  if (!detected) return;
  const question = questionInput.value.trim();
  if (!question) {
    result.textContent = 'Please type a question first.';
    return;
  }
  askBtn.disabled = true;
  result.textContent = 'Thinking...';
  try {
    const apiBase = apiBaseInput.value.trim().replace(/\/$/, '');
    const minute = detected.currentTime / 60.0;
    const response = await fetch(`${apiBase}/ask-doubt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        videoUrl: detected.url,
        minute,
        question,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed');
    result.textContent = data.answer;
    chrome.storage.local.set({ apiBase });
  } catch (err) {
    result.textContent = 'Error: ' + err.message;
  } finally {
    askBtn.disabled = false;
  }
}

chrome.storage.local.get(['apiBase'], ({ apiBase }) => {
  if (apiBase) apiBaseInput.value = apiBase;
});

askBtn.addEventListener('click', ask);
detect();
