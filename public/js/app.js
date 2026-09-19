/**
 * Document Intelligence & Question Extraction Dashboard Logic
 */

const API_BASE = '/api/v1';

function isBackendDown(status) {
  return status === 404 || status === 502 || status === 503 || status === 0;
}

function showBackendOffline() {
  const el = document.getElementById('questionsList');
  if (el) el.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">⏳</div>
      <div class="empty-state-title">Backend Starting Up</div>
      <p>The Render backend is waking up from sleep (free tier). This takes ~30 seconds. Please try again shortly.</p>
    </div>`;
}
let authToken = localStorage.getItem('doc_intel_token') || null;
let currentDocumentId = null;
let pollTimer = null;
let currentQuestionsData = [];
let currentAnswerKeyData = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const statusTracker = document.getElementById('statusTracker');
const progressFill = document.getElementById('progressFill');
const progressPct = document.getElementById('progressPct');
const docIdDisplay = document.getElementById('docIdDisplay');
const docStatusBadge = document.getElementById('docStatusBadge');
const pagesCountDisplay = document.getElementById('pagesCountDisplay');
const questionsCountDisplay = document.getElementById('questionsCountDisplay');
const extractMethodDisplay = document.getElementById('extractMethodDisplay');
const visualFlagsDisplay = document.getElementById('visualFlagsDisplay');

const questionsList = document.getElementById('questionsList');
const answersTableBody = document.getElementById('answersTableBody');
const reviewsTableBody = document.getElementById('reviewsTableBody');
const jsonViewer = document.getElementById('jsonViewer');

const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await ensureAuthentication();
  setupTabs();
  setupDropzone();
  setupSampleButtons();
  setupCopyJsonButton();
});

// Authentication
async function ensureAuthentication() {
  if (authToken) {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        updateAuthBadge('demo@docintel.com');
        return;
      }
    } catch (e) {
      console.warn("Session check failed, refreshing token...");
    }
  }

  // Attempt login or register demo account
  try {
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'demo@docintel.com', password: 'DemoPassword123!' })
    });

    if (loginRes.ok) {
      const data = await loginRes.json();
      authToken = data.access_token;
      localStorage.setItem('doc_intel_token', authToken);
      updateAuthBadge('demo@docintel.com');
    } else {
      // Register demo user
      const regRes = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'demo@docintel.com', password: 'DemoPassword123!' })
      });
      if (regRes.ok) {
        const regData = await regRes.json();
        authToken = regData.access_token;
        localStorage.setItem('doc_intel_token', authToken);
        updateAuthBadge('demo@docintel.com');
      }
    }
  } catch (err) {
    console.error("Auth error:", err);
  }
}

function updateAuthBadge(email) {
  const badge = document.getElementById('userAuthBadge');
  if (badge) badge.textContent = `👤 ${email}`;
}

// Tab navigation
function setupTabs() {
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });
}

// File Drop & Upload
function setupDropzone() {
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      uploadFile(fileInput.files[0]);
    }
  });
}

async function uploadFile(file) {
  await ensureAuthentication();
  const formData = new FormData();
  formData.append('file', file);

  showTracker(`Uploading ${file.name}...`);

  try {
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      body: formData
    });

    if (!res.ok) {
      if (isBackendDown(res.status)) {
        showBackendOffline();
        hideTracker();
        return;
      }
      let errDetail = 'Error uploading document';
      try { const err = await res.json(); errDetail = err.detail || errDetail; } catch(e) {}
      alert(`Upload failed: ${errDetail}`);
      hideTracker();
      return;
    }

    const data = await res.json();
    currentDocumentId = data.document_id;
    startPolling(currentDocumentId);
  } catch (e) {
    alert(`Upload network error: ${e.message}`);
    hideTracker();
  }
}

// Sample buttons
function setupSampleButtons() {
  document.querySelectorAll('.sample-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const sampleName = btn.getAttribute('data-sample');
      if (!sampleName) return;

      await ensureAuthentication();
      showTracker(`Submitting sample ${sampleName}...`);

      try {
        const res = await fetch(`${API_BASE}/documents/upload-sample?sample_name=${encodeURIComponent(sampleName)}`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });

        if (!res.ok) {
          const err = await res.json();
          alert(`Failed to load sample: ${err.detail || 'Error'}`);
          hideTracker();
          return;
        }

        const data = await res.json();
        currentDocumentId = data.document_id;
        startPolling(currentDocumentId);
      } catch (err) {
        alert(`Sample launch error: ${err.message}`);
        hideTracker();
      }
    });
  });
}

// Status Tracker & Poller
function showTracker(initialMsg) {
  if (statusTracker) statusTracker.classList.add('active');
  if (progressFill) progressFill.style.width = '10%';
  if (progressPct) progressPct.textContent = '10%';
  if (docStatusBadge) {
    docStatusBadge.textContent = 'PENDING';
    docStatusBadge.className = 'badge badge-warning';
  }
}

function hideTracker() {
  if (statusTracker) statusTracker.classList.remove('active');
  if (pollTimer) clearInterval(pollTimer);
}

function startPolling(docId) {
  if (pollTimer) clearInterval(pollTimer);
  docIdDisplay.textContent = docId;

  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/status`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (!res.ok) return;

      const statusData = await res.json();
      updateTrackerUI(statusData);

      if (statusData.status === 'COMPLETED') {
        clearInterval(pollTimer);
        await loadDocumentResults(docId);
      } else if (statusData.status === 'FAILED') {
        clearInterval(pollTimer);
        alert(`Document processing failed: ${statusData.error_message || 'Internal error'}`);
      }
    } catch (e) {
      console.warn("Status poll error:", e);
    }
  }, 1200);
}

function updateTrackerUI(data) {
  const pct = data.progress || 0;
  if (progressFill) progressFill.style.width = `${pct}%`;
  if (progressPct) progressPct.textContent = `${pct}%`;

  if (docStatusBadge) {
    docStatusBadge.textContent = data.status;
    docStatusBadge.className = `badge ${data.status === 'COMPLETED' ? 'badge-confidence-high' : 'badge-warning'}`;
  }

  if (pagesCountDisplay) {
    pagesCountDisplay.textContent = data.total_pages > 0 ? `${data.processed_pages}/${data.total_pages}` : 'Analyzing...';
  }

  if (questionsCountDisplay) {
    questionsCountDisplay.textContent = data.questions_extracted || 0;
  }
}

// Load Document Results
async function loadDocumentResults(docId) {
  try {
    // 1. Fetch Questions
    const qRes = await fetch(`${API_BASE}/documents/${docId}/questions?limit=100`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const qData = await qRes.json();
    currentQuestionsData = qData.items || [];
    renderQuestions(currentQuestionsData);

    // 2. Fetch Answer Keys
    const aRes = await fetch(`${API_BASE}/documents/${docId}/answer-key`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    currentAnswerKeyData = await aRes.json();
    renderAnswerKeys(currentAnswerKeyData);

    // 3. Fetch Flagged Reviews
    const rRes = await fetch(`${API_BASE}/reviews/flagged?document_id=${docId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const rData = await rRes.json();
    renderReviews(rData.items || []);

    // 4. Update JSON viewer
    updateJsonViewer({
      document_id: docId,
      status: "COMPLETED",
      questions: currentQuestionsData,
      answer_keys: currentAnswerKeyData,
      review_items: rData.items || []
    });

    // Update Tab Badges
    document.getElementById('questionsCountBadge').textContent = currentQuestionsData.length;
    document.getElementById('reviewsCountBadge').textContent = (rData.items || []).length;

  } catch (err) {
    console.error("Failed to load results:", err);
  }
}

// Render Questions
function renderQuestions(questions) {
  if (!questionsList) return;

  if (questions.length === 0) {
    questionsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <div class="empty-state-title">No questions detected</div>
        <p>Ensure the document contains recognizable question headers or examination material.</p>
      </div>`;
    return;
  }

  questionsList.innerHTML = questions.map(q => {
    const isHighConf = (q.confidence_score || 0) >= 0.75;
    const pagesStr = (q.source_pages && q.source_pages.length > 0)
      ? `Pages: ${q.source_pages.join(', ')}`
      : 'Page: ?';

    const matchedAns = q.answer ? (q.answer.answer_text || q.answer.answer_key) : null;
    const ansStatus = q.answer ? (q.answer.match_type || q.answer.match_status) : 'unmatched';

    const optionsHtml = (q.options && q.options.length > 0) ? `
      <div class="options-grid">
        ${q.options.map(opt => {
          const optKey = opt.option_key || opt.option_label;
          const isSelected = matchedAns && (matchedAns.toUpperCase() === (optKey || '').toUpperCase());
          return `
            <div class="option-item ${isSelected ? 'correct' : ''}">
              <span class="option-label">${optKey}</span>
              <span>${escapeHtml(opt.option_text)}</span>
            </div>`;
        }).join('')}
      </div>` : '';

    const answerBanner = `
      <div class="answer-banner">
        <div>
          ${matchedAns 
            ? `<span class="answer-matched">✓ Matched Answer: <strong>${matchedAns}</strong></span> <span class="badge ${ansStatus === 'matched' ? 'badge-confidence-high' : 'badge-warning'}">${ansStatus}</span>` 
            : `<span class="answer-unmatched">No answer key matched</span>`}
        </div>
        <div>
          ${q.review_status === 'FLAGGED' ? `<span class="badge badge-warning">⚠ In Review Queue</span>` : ''}
        </div>
      </div>`;

    return `
      <div class="question-card">
        <div class="question-card-header">
          <div class="q-number-title">
            <span>${q.question_number ? `Question ${q.question_number}` : 'Unnumbered Question'}</span>
          </div>
          <div class="badges-row">
            <span class="badge badge-type">${q.question_type}</span>
            <span class="badge badge-pages">${pagesStr}</span>
            <span class="badge ${isHighConf ? 'badge-confidence-high' : 'badge-confidence-low'}">
              Score: ${Math.round((q.confidence_score || 0) * 100)}%
            </span>
          </div>
        </div>
        <div class="question-text">${escapeHtml(q.question_text)}</div>
        ${optionsHtml}
        ${answerBanner}
      </div>`;
  }).join('');
}

// Render Answer Keys
function renderAnswerKeys(data) {
  if (!answersTableBody) return;

  const matches = data.answers || data.matched_answers || [];
  if (matches.length === 0) {
    answersTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No answer keys identified for this document.</td></tr>`;
    return;
  }

  answersTableBody.innerHTML = matches.map(m => {
    const ansKey = m.matched_answer || m.answer_key || '—';
    const statusType = m.match_type || m.match_status || 'unmatched';
    const srcPage = m.source_page || (m.source_pages && m.source_pages[0]) || '—';
    return `
      <tr>
        <td><strong>${m.question_number || 'N/A'}</strong></td>
        <td><span style="font-weight: 700; color: #34d399;">${ansKey}</span></td>
        <td>
          <span class="badge ${statusType === 'matched' ? 'badge-confidence-high' : 'badge-warning'}">
            ${statusType}
          </span>
        </td>
        <td>${srcPage !== '—' ? `Page ${srcPage}` : '—'}</td>
        <td>${Math.round((m.confidence_score || 0) * 100)}%</td>
      </tr>`;
  }).join('');
}

// Render Reviews
function renderReviews(reviews) {
  if (!reviewsTableBody) return;

  if (reviews.length === 0) {
    reviewsTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No flagged review items. Document processed with high confidence!</td></tr>`;
    return;
  }

  reviewsTableBody.innerHTML = reviews.map(r => {
    return `
      <tr>
        <td><strong>${r.question_number || 'Question'}</strong></td>
        <td><span class="badge badge-warning">${r.warning_code}</span></td>
        <td>${escapeHtml(r.flag_reason)}</td>
        <td>${Math.round((r.confidence_score || 0) * 100)}%</td>
        <td>
          <button class="btn-secondary" onclick="resolveReviewItem('${r.id}', this)">Mark Verified</button>
        </td>
      </tr>`;
  }).join('');
}

window.resolveReviewItem = async function(reviewId, btnElement) {
  try {
    const res = await fetch(`${API_BASE}/reviews/${reviewId}/status?status=RESOLVED&resolution_notes=Verified+via+Web+Dashboard`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      btnElement.textContent = 'Resolved ✓';
      btnElement.disabled = true;
      btnElement.style.opacity = '0.5';
    }
  } catch (e) {
    alert(`Could not resolve: ${e.message}`);
  }
};

// JSON Viewer & Copy
function updateJsonViewer(data) {
  if (jsonViewer) {
    jsonViewer.textContent = JSON.stringify(data, null, 2);
  }
}

function setupCopyJsonButton() {
  const copyBtn = document.getElementById('copyJsonBtn');
  if (copyBtn && jsonViewer) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(jsonViewer.textContent).then(() => {
        const orig = copyBtn.textContent;
        copyBtn.textContent = 'Copied! ✓';
        setTimeout(() => copyBtn.textContent = orig, 2000);
      });
    });
  }
}

// Utility
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
