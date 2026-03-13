/**
 * medium-writer UI
 * Calls the Anthropic API directly from the browser to generate Medium articles.
 * Mirrors the logic in src/medium_writer/writer.py and researcher.py.
 */

const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';
const WRITE_MODEL = 'claude-sonnet-4-6';
const RESEARCH_MODEL = 'claude-haiku-4-5-20251001';
const KEY_STORAGE_KEY = 'mw_anthropic_key';
const MAX_TOKENS_WRITE = 4096;
const MAX_TOKENS_RESEARCH = 1024;

// Mirrors prompts/researcher_system.md
const RESEARCHER_SYSTEM = `You are a content strategist who specializes in data engineering, data science, and AI tooling for practitioners who are early in their careers.

Your audience: beginner to intermediate data engineers and data scientists. They know the basics of Python and SQL, and have heard of tools like Spark, Airflow, dbt, or pandas, but are still building intuition for when and why to use them. They want practical guidance, not academic theory.

Topics you cover well:
- Data Engineering: pipelines, orchestration (Airflow, Prefect, dbt), data transformation, data quality, cloud data warehouses, lakehouse basics
- Data Science fundamentals: feature engineering, experiment tracking, model deployment, working with large datasets
- AI Engineering: using LLMs practically, RAG, embeddings, prompt engineering, Claude/OpenAI APIs, AI-powered pipelines
- Developer tooling: Claude Code, productivity tools, VS Code for data practitioners
- Career & learning: how to level up as a data engineer or scientist

When suggesting topics, prioritize:
1. Concepts that confuse beginners but shouldn't — things that become obvious once explained well
2. Practical walkthroughs that go from zero to something working
3. Common mistakes and how to avoid them
4. Tools worth learning now, and why

Avoid overly advanced topics. Avoid pure research/paper summaries. Focus on things someone can apply this week.
Be specific. Vague topics make weak articles.`;

// Loaded from ./writer_system.md at startup
let writerSystemPrompt = null;

// Accumulated article text during streaming
let articleText = '';

// ─── Initialisation ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  loadApiKey();
  addUrlRow(); // start with one empty URL row
  await fetchWriterSystem();
  bindEvents();
});

async function fetchWriterSystem() {
  try {
    const resp = await fetch('./writer_system.md');
    if (resp.ok) {
      writerSystemPrompt = await resp.text();
    } else {
      console.warn('writer_system.md not found — will use a fallback prompt.');
    }
  } catch (e) {
    console.warn('Could not load writer_system.md:', e);
  }
}

// ─── API Key ──────────────────────────────────────────────────────────────────

function loadApiKey() {
  const saved = localStorage.getItem(KEY_STORAGE_KEY);
  if (saved) {
    document.getElementById('apiKey').value = saved;
    updateKeyStatus(true);
  }
}

function saveApiKey() {
  const key = document.getElementById('apiKey').value.trim();
  if (key) {
    localStorage.setItem(KEY_STORAGE_KEY, key);
    updateKeyStatus(true);
    showStatus('API key saved.', 'success');
  }
}

function clearApiKey() {
  localStorage.removeItem(KEY_STORAGE_KEY);
  document.getElementById('apiKey').value = '';
  updateKeyStatus(false);
  showStatus('API key cleared.', 'info');
}

function updateKeyStatus(hasSaved) {
  const el = document.getElementById('keyStatus');
  el.textContent = hasSaved ? '(saved)' : '';
}

function getApiKey() {
  return document.getElementById('apiKey').value.trim();
}

// ─── URL rows ─────────────────────────────────────────────────────────────────

function addUrlRow(value = '') {
  const list = document.getElementById('urlList');
  const row = document.createElement('div');
  row.className = 'url-row';

  const input = document.createElement('input');
  input.type = 'url';
  input.placeholder = 'https://...';
  input.value = value;

  const removeBtn = document.createElement('button');
  removeBtn.type = 'button';
  removeBtn.className = 'btn-remove-url';
  removeBtn.title = 'Remove URL';
  removeBtn.textContent = '×';
  removeBtn.addEventListener('click', () => {
    row.remove();
    // Always keep at least one empty row for clarity
    if (document.querySelectorAll('.url-row').length === 0) {
      addUrlRow();
    }
  });

  row.appendChild(input);
  row.appendChild(removeBtn);
  list.appendChild(row);
  return input;
}

function getUrls() {
  return Array.from(document.querySelectorAll('.url-row input'))
    .map(i => i.value.trim())
    .filter(Boolean);
}

// ─── Event binding ────────────────────────────────────────────────────────────

function bindEvents() {
  document.getElementById('saveKeyBtn').addEventListener('click', saveApiKey);
  document.getElementById('clearKeyBtn').addEventListener('click', clearApiKey);
  document.getElementById('addUrlBtn').addEventListener('click', () => addUrlRow());
  document.getElementById('generateForm').addEventListener('submit', handleSubmit);
  document.getElementById('copyBtn').addEventListener('click', copyArticle);
  document.getElementById('downloadBtn').addEventListener('click', downloadArticle);
}

// ─── Main submit handler ──────────────────────────────────────────────────────

async function handleSubmit(e) {
  e.preventDefault();

  const apiKey = getApiKey();
  const title = document.getElementById('title').value.trim();
  const plan = document.getElementById('plan').value.trim();
  const urls = getUrls();

  // Validation
  if (!apiKey) {
    showStatus('Please enter your Anthropic API key above.', 'error');
    document.getElementById('apiKeySection').open = true;
    return;
  }
  if (!title) {
    showStatus('Please enter an article title.', 'error');
    document.getElementById('title').focus();
    return;
  }

  setGenerating(true);
  hideOutput();
  articleText = '';

  try {
    // Phase 1: research brief (skip if user provided a plan)
    let brief;
    if (plan) {
      brief = plan;
      hideBrief();
    } else {
      showStatus('Generating research brief…', 'info');
      brief = await researchPhase(title, apiKey);
      showBrief(brief);
    }

    // Phase 2: article generation
    showStatus('Writing article…', 'info');
    showOutputSection();
    await writePhase(title, brief, urls, apiKey);

    hideStatus();
  } catch (err) {
    showStatus(formatError(err), 'error');
  } finally {
    setGenerating(false);
  }
}

// ─── Phase 1: Research brief ──────────────────────────────────────────────────

/**
 * Mirrors researcher.py research_topic() — calls Haiku with the researcher
 * system prompt and returns a plain-text research brief.
 */
async function researchPhase(topic, apiKey) {
  const userMsg =
    `Write a concise research brief for a Medium article titled: "${topic}"\n\n` +
    'Include:\n' +
    '- Key concepts to cover\n' +
    '- Relevant recent developments (as of your knowledge cutoff)\n' +
    '- Code example ideas\n' +
    '- Potential gotchas or counterintuitive points\n' +
    '- Target audience assumptions (beginner-intermediate data engineers/scientists)\n\n' +
    'Keep it under 500 words. This is for the writer, not the reader.';

  const body = {
    model: RESEARCH_MODEL,
    max_tokens: MAX_TOKENS_RESEARCH,
    system: RESEARCHER_SYSTEM,
    messages: [{ role: 'user', content: userMsg }],
  };

  const resp = await callAnthropicJson(body, apiKey);
  return resp.content[0].text;
}

// ─── Phase 2: Article writing ─────────────────────────────────────────────────

/**
 * Mirrors writer.py generate_article() — calls Sonnet with streaming and
 * appends text chunks to the output area as they arrive.
 */
async function writePhase(topic, brief, urls, apiKey) {
  const systemPrompt = writerSystemPrompt || fallbackWriterSystem();
  const userMsg = buildUserMessage(topic, brief, urls);

  const body = {
    model: WRITE_MODEL,
    max_tokens: MAX_TOKENS_WRITE,
    stream: true,
    system: systemPrompt,
    messages: [{ role: 'user', content: userMsg }],
  };

  const response = await fetch(ANTHROPIC_API_URL, {
    method: 'POST',
    headers: buildHeaders(apiKey),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errBody);
  }

  await consumeStream(response.body);
}

/**
 * Assembles the user message exactly as writer.py does (writer.py:96).
 * URLs are passed as reference text since the browser cannot fetch them.
 */
function buildUserMessage(topic, brief, urls) {
  let msg = `Write a Medium article titled: "${topic}"\n\nResearch brief:\n${brief}`;

  if (urls.length > 0) {
    msg += '\n\n## Reference URLs\n';
    msg +=
      'The user has provided these as source material. ' +
      'Incorporate their key points and examples into the article. ' +
      'Cite them naturally inline:\n';
    for (const url of urls) {
      msg += `- ${url}\n`;
    }
  }

  return msg;
}

// ─── Streaming SSE parser ─────────────────────────────────────────────────────

async function consumeStream(readableStream) {
  const reader = readableStream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const outputEl = document.getElementById('articleOutput');

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Split on newlines; keep any incomplete trailing line in the buffer
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === '[DONE]') continue;

      let event;
      try {
        event = JSON.parse(raw);
      } catch {
        continue;
      }

      if (
        event.type === 'content_block_delta' &&
        event.delta?.type === 'text_delta'
      ) {
        const chunk = event.delta.text;
        articleText += chunk;
        outputEl.textContent = articleText;
        outputEl.scrollTop = outputEl.scrollHeight;
      }

      if (event.type === 'message_stop') {
        return;
      }
    }
  }
}

// ─── Anthropic API helpers ────────────────────────────────────────────────────

function buildHeaders(apiKey) {
  return {
    'content-type': 'application/json',
    'x-api-key': apiKey,
    'anthropic-version': '2023-06-01',
    'anthropic-dangerous-direct-browser-access': 'true',
  };
}

/** Non-streaming call — used for the research phase. */
async function callAnthropicJson(body, apiKey) {
  const response = await fetch(ANTHROPIC_API_URL, {
    method: 'POST',
    headers: buildHeaders(apiKey),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errBody);
  }

  return response.json();
}

class ApiError extends Error {
  constructor(status, body) {
    const msg = body?.error?.message || `API error ${status}`;
    super(msg);
    this.status = status;
    this.body = body;
  }
}

function formatError(err) {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return 'Invalid API key. Please check your Anthropic API key and try again.';
    }
    if (err.status === 429) {
      return 'Rate limit reached. Please wait a moment and try again.';
    }
    if (err.status === 529) {
      return 'Claude is currently overloaded. Please try again in a moment.';
    }
    return `API error: ${err.message}`;
  }
  if (err instanceof TypeError && err.message.includes('fetch')) {
    return 'Network error. Please check your internet connection and try again.';
  }
  return `Unexpected error: ${err.message}`;
}

// ─── Download & copy ──────────────────────────────────────────────────────────

function copyArticle() {
  navigator.clipboard.writeText(articleText).then(() => {
    const btn = document.getElementById('copyBtn');
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = original; }, 2000);
  });
}

function downloadArticle() {
  const title = document.getElementById('title').value.trim();
  const slug = slugify(title);
  const date = new Date().toISOString().slice(0, 10);
  const filename = `${date}-${slug}.md`;

  const blob = new Blob([articleText], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Mirrors writer.py _slugify() (writer.py:55).
 * Lowercase, strip non-word chars, replace spaces with hyphens, cap at 80 chars.
 */
function slugify(title) {
  let slug = title.toLowerCase();
  slug = slug.replace(/[^\w\s-]/g, '');
  slug = slug.replace(/[\s_]+/g, '-');
  slug = slug.replace(/-+/g, '-').replace(/^-|-$/g, '');
  return slug.slice(0, 80);
}

// ─── UI state helpers ─────────────────────────────────────────────────────────

function setGenerating(active) {
  const btn = document.getElementById('generateBtn');
  const label = document.getElementById('generateBtnLabel');
  const spinner = document.getElementById('generateBtnSpinner');
  btn.disabled = active;
  label.textContent = active ? 'Generating…' : 'Generate Article';
  spinner.hidden = !active;
}

function showStatus(msg, type = 'info') {
  const bar = document.getElementById('statusBar');
  bar.textContent = msg;
  bar.className = `status-bar ${type}`;
  bar.hidden = false;
}

function hideStatus() {
  document.getElementById('statusBar').hidden = true;
}

function showBrief(text) {
  const section = document.getElementById('briefSection');
  const content = document.getElementById('briefContent');
  content.textContent = text;
  section.hidden = false;
  section.open = false; // collapsed by default
}

function hideBrief() {
  document.getElementById('briefSection').hidden = true;
}

function showOutputSection() {
  document.getElementById('outputSection').hidden = false;
  document.getElementById('articleOutput').textContent = '';
}

function hideOutput() {
  document.getElementById('outputSection').hidden = true;
}

// ─── Fallback writer system prompt ───────────────────────────────────────────
// Used if writer_system.md could not be loaded (e.g. running on file://)

function fallbackWriterSystem() {
  return `You are a technical writer for Medium. Write articles for beginner to intermediate data engineers and data scientists. Tone: conversational, encouraging, practical. Target 1000-1800 words. Output raw Markdown with a single H1 title, H2 section headings, and fenced code blocks with language tags.`;
}
