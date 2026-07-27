
const PROFILE = {
  name: "Mahmoud ElHassan",
  title: "Junior .NET Backend Developer",
  email: "mahmoudelhassan9@gmail.com",
  phone: "+966 050 411 6526",
  linkedin: "linkedin.com/in/mahmoud-elhassan-94r",
  github: "github.com/MahmoudElHassan",
  portfolio: "mahmoud-portofolio-eta.vercel.app",
  yearsExp: "5+",
  location: "Egypt (Cairo/Makkah timezone)",
  visa: "Open to sponsorship in KSA / Gulf / Europe / Asia",
  stack: "ASP.NET Core, EF Core, Clean Architecture, REST APIs, JWT, SQL Server, PostgreSQL, MongoDB, Redis, Microsoft Azure, Docker, CI/CD",
  ksaExp: "1.5 years at Digital Tamkeen in Makkah (Jan 2025 – Jan 2026) — KSA market delivery, payment workflows, multi-tenant SaaS",
  finTech: "AWS payment gateway integration (transactional integrity, retries, reconciliation)",
};

const CSV_URL = 'https://raw.githubusercontent.com/MahmoudElHassan/job-hunter/main/data/Job_Listings.csv';

// ===== Fallback dataset (real, strong jobs from previous scans) =====
const FALLBACK_JOBS = [
  {
    id: "talent-360-sifi-2025",
    score: "5", source_type: "main", date_found: "2026-07-26",
    company: "Talent 360 / SiFi", role: "Mid-level Backend Engineer (.NET) — FinTech expense management for KSA",
    location: "Remote, Egypt", remote: "yes", sponsorship: "yes",
    stack_match: "asp.net core, ef core, sql server, postgresql, mongodb, redis, docker, azure",
    board: "Bayt.com", url: "https://www.bayt.com/en/egypt/jobs/.net-backend-jobs/",
    status: "new", notes: "Mid-level + KSA market + FinTech (top match)"
  },
  {
    id: "easycash-2025",
    score: "4", source_type: "main", date_found: "2026-07-26",
    company: "Easycash", role: "Mid-Level .NET Developer (ASP.NET Core / ABP Framework) — ERP",
    location: "Hybrid — Nasr City, Cairo, Egypt", remote: "no", sponsorship: "no",
    stack_match: "asp.net core, abp framework, postgresql, rest apis, git, clean architecture",
    board: "LinkedIn", url: "https://www.linkedin.com/posts/easycashwallet_were-hiring-mid-level-net-developer-activity-7438669637761949697-P_gC",
    status: "new", notes: "ABP Framework direct match for Clean Architecture"
  },
  {
    id: "codetact-2025",
    score: "4", source_type: "main", date_found: "2026-07-26",
    company: "CodeTact Recruit", role: "Backend Engineer (.NET) — FinTech & Enterprise",
    location: "Hybrid, Cairo (2-3 days onsite)", remote: "no", sponsorship: "no",
    stack_match: ".net, asp.net core, web apis, sql server, git, agile",
    board: "LinkedIn", url: "https://www.linkedin.com/posts/codetact-recruit_dotnet-backenddeveloper-egyptjobs-activity-7409358001045680128--9mG",
    status: "new", notes: "USD-based compensation"
  },
  {
    id: "acksession-2025",
    score: "4", source_type: "main", date_found: "2026-07-26",
    company: "Acksession", role: "Mid-Level Backend Engineer (.NET)",
    location: "Remote, Egypt", remote: "yes", sponsorship: "no",
    stack_match: ".net framework, c#, api design, database design, design patterns",
    board: "Direct", url: "https://remoteworkjobs.ai/Job/job-listings-mid-level-backend-engineer-net-remote--155",
    status: "new", notes: "Remote-friendly, mid-level"
  },
  {
    id: "smartware-2025",
    score: "4", source_type: "main", date_found: "2026-07-26",
    company: "SMARTWARE", role: "Junior .NET Core Developer",
    location: "Remote, Egypt", remote: "yes", sponsorship: "no",
    stack_match: ".net core, c#, asp.net, sql server",
    board: "Direct", url: "https://www.linkedin.com/jobs/view/4180360320",
    status: "new", notes: "Junior-level title (matches your self-identification)"
  },
  {
    id: "rtr-software-2025",
    score: "3", source_type: "main", date_found: "2026-07-26",
    company: "RTR Software Solutions", role: "Mid Level Backend Developer (.NET Core)",
    location: "On-site, Cairo, Egypt", remote: "no", sponsorship: "no",
    stack_match: ".net, .net core, c#, sql server, azure, git",
    board: "Wuzzuf", url: "https://wuzzuf.net/jobs/p/gvuqbwokyxyk-mid-level-backend-developernet-core-rtr-software-solutions-cairo-egypt",
    status: "new", notes: "On-site Cairo, mid-level"
  },
  {
    id: "squadio-2025",
    score: "3", source_type: "main", date_found: "2026-07-26",
    company: "Squadio", role: "Mid-Senior .NET Backend Developer — USD-paid contract",
    location: "Remote (Egypt-friendly)", remote: "yes", sponsorship: "no",
    stack_match: ".net core, c#, asp.net, ef, sql server, postgresql, azure, aws",
    board: "Direct", url: "https://3abkry.com/en/saudi-arabia/jobs/mid-senior-net-backend-developer-6002",
    status: "new", notes: "USD-paid contract"
  },
  {
    id: "swatx-2025",
    score: "3", source_type: "main", date_found: "2026-07-26",
    company: "SWATX", role: "Mid-Level .NET Developer",
    location: "Cairo, Egypt", remote: "no", sponsorship: "no",
    stack_match: "asp.net mvc, .net core, sql server, rest apis, ef core, git",
    board: "LinkedIn", url: "https://www.linkedin.com/jobs/view/4180360320",
    status: "new", notes: "On-site Cairo, mid-level"
  },
  {
    id: "adree-2025",
    score: "3", source_type: "main", date_found: "2026-07-26",
    company: "Adree", role: ".NET Backend Developer",
    location: "HQ, Cairo, Egypt", remote: "no", sponsorship: "no",
    stack_match: "c#, asp.net core, web apis, ef, sql, jwt, oop",
    board: "LinkedIn", url: "https://www.linkedin.com/jobs/view/4440006091",
    status: "new", notes: "On-site Cairo, mid-level"
  },
  {
    id: "waffarx-2025",
    score: "3", source_type: "main", date_found: "2026-07-26",
    company: "Waffarx", role: "Net Developer",
    location: "Cairo, Egypt", remote: "no", sponsorship: "no",
    stack_match: "c#, web application, devops, agile",
    board: "NaukriGulf", url: "https://www.naukrigulf.com/dot-net-developer-jobs-in-uae",
    status: "new", notes: "On-site Cairo"
  }
];

let ALL_JOBS = [];
let DATA_SOURCE = 'fallback';
let APPROVALS = JSON.parse(localStorage.getItem('cl_approvals') || '{}');
let GENERATED = JSON.parse(localStorage.getItem('cl_generated') || '{}');

// ===== Data loading (CSV first, fallback if fails or empty) =====
async function loadData(forceReload = false) {
  setStatus('⏳ Loading jobs from CSV…', 'loading');
  document.getElementById('source-status').textContent = '⏳ Loading…';

  let csvJobs = [];
  let csvError = null;
  try {
    const resp = await fetch(CSV_URL + (forceReload ? '?t=' + Date.now() : ''), { cache: 'no-store' });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const text = await resp.text();
    const parsed = parseCSV(text);
    csvJobs = parsed.filter(r => r.id);
  } catch (e) {
    csvError = e.message;
  }

  if (csvJobs.length >= 5) {
    ALL_JOBS = csvJobs;
    DATA_SOURCE = 'csv';
    setStatus(`✅ Loaded ${csvJobs.length} jobs from your GitHub CSV (last refresh: ${new Date().toLocaleTimeString()})`, 'success');
    document.getElementById('source-status').textContent = `✅ ${csvJobs.length} from CSV`;
  } else {
    // Fallback
    ALL_JOBS = FALLBACK_JOBS;
    DATA_SOURCE = 'fallback';
    const reason = csvError ? `CSV error: ${csvError}` : `CSV returned only ${csvJobs.length} valid rows`;
    setStatus(`⚠️ ${reason}. Showing embedded fallback dataset (${FALLBACK_JOBS.length} strong jobs) — click 🔄 to retry`, 'warning');
    document.getElementById('source-status').textContent = `⚠️ Fallback (${FALLBACK_JOBS.length})`;
  }

  document.getElementById('last-fetch').textContent = new Date().toLocaleString();
  render();
  updateStats();
}

function setStatus(msg, type) {
  const area = document.getElementById('status-area');
  area.innerHTML = `<div class="status-banner ${type}">${msg}</div>`;
  setTimeout(() => {
    if (area.querySelector('.status-banner')?.textContent === msg) {
      area.innerHTML = '';
    }
  }, 5000);
}

function parseCSV(text) {
  // State machine that respects quoted fields with embedded commas and
  // newlines. The previous version did `text.split('\n')` which broke any
  // row whose `notes` field contained a newline (causing it to be counted
  // twice and shown as duplicate cards).
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"' && inQuotes && text[i + 1] === '"') {
      field += '"'; i++;
    } else if (c === '"') {
      inQuotes = !inQuotes;
    } else if (c === ',' && !inQuotes) {
      row.push(field); field = '';
    } else if ((c === '\n' || c === '\r') && !inQuotes) {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.length > 1 || (row[0] && row[0].trim())) rows.push(row);
      row = [];
    } else {
      field += c;
    }
  }
  if (field !== '' || row.length > 0) {
    row.push(field);
    if (row.length > 1 || (row[0] && row[0].trim())) rows.push(row);
  }

  if (rows.length === 0) return [];
  const headers = rows[0].map(h => h.trim());
  return rows.slice(1).map(values => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = (values[i] || '').trim());
    return obj;
  }).filter(r => r.id);  // skip blank rows
}

function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"' && line[i+1] === '"' && inQuotes) { current += '"'; i++; }
    else if (c === '"') { inQuotes = !inQuotes; }
    else if (c === ',' && !inQuotes) { result.push(current); current = ''; }
    else { current += c; }
  }
  result.push(current);
  return result;
}

// ===== Cover letter generation =====
function generateCoverLetter(v, type) {
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const isFreelance = type === 'Freelance';
  const isPartTime = type === 'Part-time';

  const opening = isFreelance
    ? `I'd like to discuss a potential freelance engagement for the ${v.role} role at ${v.company}.`
    : `I'm applying for the ${v.role} role at ${v.company}.`;

  const typeSpecific = isPartTime
    ? `I'm particularly interested in part-time arrangements, with capacity for ${(v.location || '').toLowerCase().includes('remote') ? 'remote collaboration across timezones' : 'flexible scheduling'}.`
    : isFreelance
    ? `For freelance work, I can scope to a defined deliverable, ship against a milestone plan, and invoice through a contractor agreement. My typical availability is 30-40 hours/week with overlap on Cairo/Makkah business hours.`
    : `I'm available full-time, Egypt-based, and can start within 2-4 weeks of an accepted offer.`;

  const stack = v.stack_match || 'ASP.NET Core, .NET, backend';
  const fitBody = `What makes this role a strong match:\n\n• Stack overlap: ${stack}\n• ${v.location || 'Location TBD'} ${v.remote === 'yes' ? '(remote-friendly)' : ''}\n• Score: ${v.score || '—'}★ (from the job-hunter scoring system)\n\nThe stack maps directly to my production work at Astro Pvt (Khzama, NumeriiSoft — multi-tenant SaaS on Azure) and Digital Tamkeen (Matrix — ad-tech with AWS payment gateway).`;

  const experienceBody = `\n\nI bring three signals that are uncommon together: ${PROFILE.yearsExp} of professional .NET work, **${PROFILE.ksaExp}**, and **${PROFILE.finTech}**.`;

  const close = isFreelance
    ? `Happy to share my rate card, references from prior engagements, and a short scope for evaluation.`
    : `Happy to do a paid take-home or technical screen to let the work speak for itself.`;

  const subject = isFreelance
    ? `Freelance Inquiry — ${v.role} — ${v.company}`
    : `Application — ${v.role} — ${v.company}`;

  return `Subject: ${subject}

Dear ${v.company} Hiring Team,

${opening} ${typeSpecific}

${fitBody}${experienceBody}

Production highlights from the last ${PROFILE.yearsExp} years:
- Khzama — multi-tenant charity donation SaaS on Azure App Service, built on strict Clean Architecture (Domain → Application → Infrastructure → API), JWT-secured REST APIs, payment workflows under KSA-considerate audit and reconciliation
- Matrix — social-media ad-tech platform integrating Meta Marketing API + TikTok Ads API, with AWS payment gateway integration (transactional integrity, retries, reconciliation)
- NumeriiSoft — numerology API platform with 3+ third-party integrations unified behind a single JSON contract
- Aqwon — financial aid application portal with multi-step approval workflow and role-based access

${close}

Best,
Mahmoud ElHassan
${PROFILE.email} · ${PROFILE.phone}
LinkedIn: ${PROFILE.linkedin}
GitHub: ${PROFILE.github}
Portfolio: ${PROFILE.portfolio}

---
Generated ${today} · ${v.company} (${v.role}) · ${type} · Source: ${v.source_type || 'main'}`;
}

// ===== Render =====
function render() {
  const search = document.getElementById('search').value.toLowerCase();
  const minScore = parseInt(document.getElementById('filter-score').value);
  const source = document.getElementById('filter-source').value;
  const status = document.getElementById('filter-status').value;
  // filter-company: 'all' (default, show all) or 'no' (hide Unknown companies)
  const companyFilter = document.getElementById('filter-company').value;
  const hideUnknown = companyFilter === 'no';

  let rows = ALL_JOBS.filter(r => {
    if (parseInt(r.score || 0) < minScore) return false;
    if (source && r.source_type !== source) return false;
    const currentStatus = GENERATED[r.id] ? 'generated' : (APPROVALS[r.id] ? 'approved' : 'new');
    if (status && currentStatus !== status) return false;
    if (hideUnknown && (!r.company || r.company.toLowerCase().trim() === 'unknown' || r.company.trim() === '')) return false;
    if (search) {
      const haystack = `${r.company} ${r.role} ${r.stack_match} ${r.location}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });

  if (rows.length === 0) {
    document.getElementById('vacancies').innerHTML = '<div class="empty">No jobs match your filters. Try lowering "Min score" or toggling "Hide Unknown".</div>';
    return;
  }

  document.getElementById('vacancies').innerHTML = rows.map(v => cardHTML(v)).join('');
  updateStats();
}

function cardHTML(v) {
  const type = APPROVALS[v.id]?.type || 'Full-time';
  const isApproved = !!APPROVALS[v.id];
  const isGenerated = !!GENERATED[v.id];
  const status = isGenerated ? 'generated' : (isApproved ? 'approved' : 'pending');
  const statusLabel = isGenerated ? 'GENERATED' : isApproved ? 'APPROVED' : 'NEW';

  const loc = v.remote === 'yes' ? `${v.location || '—'} 🏠` : (v.location || '—');
  const scoreClass = v.score === '5' ? 'score5' : v.score === '4' ? 'score4' : v.score === '3' ? 'score3' : '';
  const stack = (v.stack_match || '').split(',').slice(0, 4).map(s => s.trim()).filter(Boolean).join(' · ');

  return `
    <div class="vacancy status-${status}" id="vcard-${escapeHtml(v.id)}">
      <div class="vac-head">
        <div class="vac-info">
          <h2>${escapeHtml(v.company || 'Unknown')} ${v.score ? `<span class="badge ${scoreClass}">${v.score}★</span>` : ''} <span class="badge status-${status}">${statusLabel}</span></h2>
          <div class="role">${escapeHtml(v.role || '—')}</div>
          <div class="meta">
            <span class="badge">📍 ${escapeHtml(loc)}</span>
            <span class="badge">🏷 ${escapeHtml(v.source_type || '—')}</span>
            <span class="badge">📅 ${escapeHtml((v.date_found || '—').slice(0, 10))}</span>
            <span class="badge">ID: <code>${escapeHtml(v.id || '—')}</code></span>
          </div>
          ${stack ? `<div class="key-fits"><div class="stack"><strong>Stack:</strong> ${escapeHtml(stack)}</div></div>` : ''}
          ${v.notes ? `<div class="key-fits"><div class="stack" style="color:#6e6e73;font-style:italic;">💡 ${escapeHtml(v.notes)}</div></div>` : ''}
        </div>
      </div>

      <div class="controls">
        <label style="font-size:12px;color:#6e6e73;">Type:</label>
        <select class="type-select" id="type-${escapeHtml(v.id)}" onchange="setType('${escapeHtml(v.id)}', this.value)">
          <option value="Full-time" ${type==='Full-time'?'selected':''}>Full-time</option>
          <option value="Part-time" ${type==='Part-time'?'selected':''}>Part-time</option>
          <option value="Freelance" ${type==='Freelance'?'selected':''}>Freelance</option>
        </select>
        <button class="btn-primary" onclick="approveAndGenerate('${escapeHtml(v.id)}')" id="genbtn-${escapeHtml(v.id)}">
          ${isGenerated ? '🔄 Regenerate' : '✨ Generate Cover Letter'}
        </button>
        ${isApproved && !isGenerated ? '<button class="btn-warning" onclick="unapprove(\'' + escapeHtml(v.id) + '\')">↩ Unapprove</button>' : ''}
        ${isGenerated ? '<button class="btn-secondary" onclick="markPending(\'' + escapeHtml(v.id) + '\')">↩ Reset</button>' : ''}
        <button class="btn-secondary" onclick="copyJobId('${escapeHtml(v.id)}')">📋 Copy ID</button>
        ${v.url ? `<a class="btn-secondary" href="${escapeHtml(v.url)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;display:inline-flex;align-items:center;">🔗 Open</a>` : ''}
      </div>

      <div class="cover-letter ${isGenerated ? 'show' : ''}" id="cl-${escapeHtml(v.id)}">
        <textarea id="ta-${escapeHtml(v.id)}" readonly>${escapeHtml(GENERATED[v.id] || '')}</textarea>
        <div class="actions">
          <button class="btn-primary" onclick="copyCoverLetter('${escapeHtml(v.id)}')">📋 Copy Letter</button>
          <button class="btn-success" onclick="downloadPDF('${escapeHtml(v.id)}')">📄 Save as PDF</button>
          <button class="btn-success" onclick="downloadDOCX('${escapeHtml(v.id)}')">📝 Save as DOCX</button>
        </div>
      </div>
    </div>
  `;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ===== Actions =====
function setType(id, type) {
  if (!APPROVALS[id]) APPROVALS[id] = {};
  APPROVALS[id].type = type;
  localStorage.setItem('cl_approvals', JSON.stringify(APPROVALS));
  updateStats();
}

function approveAndGenerate(id) {
  const v = ALL_JOBS.find(x => x.id === id);
  if (!v) { toast('Job not found', 'error'); return; }
  const type = APPROVALS[id]?.type || document.getElementById(`type-${id}`).value || 'Full-time';
  if (!APPROVALS[id]) APPROVALS[id] = {};
  APPROVALS[id].type = type;
  APPROVALS[id].approvedAt = new Date().toISOString();
  APPROVALS[id].jobSnapshot = v;
  const text = generateCoverLetter(v, type);
  GENERATED[id] = text;
  localStorage.setItem('cl_approvals', JSON.stringify(APPROVALS));
  localStorage.setItem('cl_generated', JSON.stringify(GENERATED));
  document.getElementById(`cl-${id}`).classList.add('show');
  document.getElementById(`ta-${id}`).value = text;
  render();
  toast('Cover letter generated for ' + v.company, 'success');
}

function unapprove(id) {
  delete APPROVALS[id];
  localStorage.setItem('cl_approvals', JSON.stringify(APPROVALS));
  render();
  toast('Approval removed');
}

function markPending(id) {
  delete APPROVALS[id];
  delete GENERATED[id];
  localStorage.setItem('cl_approvals', JSON.stringify(APPROVALS));
  localStorage.setItem('cl_generated', JSON.stringify(GENERATED));
  render();
  toast('Reset to pending');
}

function copyCoverLetter(id) {
  const ta = document.getElementById(`ta-${id}`);
  ta.select();
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(ta.value).then(() => {
      toast('Cover letter copied', 'success');
    }).catch(() => fallbackCopy(ta.value, 'Cover letter'));
  } else {
    fallbackCopy(ta.value, 'Cover letter');
  }
}

function copyJobId(id) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(id).then(() => {
      toast('Job ID copied: ' + id, 'success');
    }).catch(() => fallbackCopy(id, 'Job ID'));
  } else {
    fallbackCopy(id, 'Job ID');
  }
}

function fallbackCopy(text, label) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);padding:12px;font-size:14px;width:80%;max-width:500px;height:160px;z-index:9999;background:#fff8e1;border:2px solid #ffd54f;border-radius:8px;';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9998;';
  overlay.onclick = () => cleanup();
  document.body.appendChild(overlay);
  function cleanup() {
    document.body.removeChild(ta);
    if (document.body.contains(overlay)) document.body.removeChild(overlay);
  }
  setTimeout(cleanup, 10000);
  toast(`${label} — selection shown, press Ctrl+C (or Cmd+C) to copy`, 'success');
}

function copyApprovals() {
  const approved = Object.keys(APPROVALS)
    .map(id => ({ id, ...APPROVALS[id], job: ALL_JOBS.find(j => j.id === id) }))
    .filter(x => x.job);
  if (approved.length === 0) {
    toast('No approvals yet — click "Generate Cover Letter" first', 'error');
    return;
  }
  const list = approved.map(a =>
    `• ${a.id} — ${a.job.company} (${a.job.role}) — ${a.type} — ${a.job.location || ''} ${a.job.remote === 'yes' ? '🏠 remote' : ''}`
  ).join('\n');
  const msg = `Approved cover letters (${approved.length}):\n\n${list}\n\nPaste this in chat with Job Hunter.`;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(msg).then(() => {
      toast(`${approved.length} approvals copied`, 'success');
    }).catch(() => fallbackCopy(msg, 'Approvals list'));
  } else {
    fallbackCopy(msg, 'Approvals list');
  }
}

function sendApprovalsToJobHunter() {
  copyApprovals();
}

function clearAll() {
  if (!confirm('Clear all approvals and generated cover letters?')) return;
  APPROVALS = {};
  GENERATED = {};
  localStorage.removeItem('cl_approvals');
  localStorage.removeItem('cl_generated');
  render();
  toast('All cleared', 'success');
}

function downloadPDF(id) {
  const v = ALL_JOBS.find(x => x.id === id);
  if (!v) { toast('Job not found', 'error'); return; }
  if (!GENERATED[id]) { toast('Generate the letter first', 'error'); return; }
  const companyName = sanitizeFilename(v.company || 'Unknown');
  const filename = `Cover Letter - ${companyName}.pdf`;
  const html = generateCoverLetterHTML(v, APPROVALS[id]?.type || 'Full-time');
  const w = window.open('', '_blank');
  const scriptOpen = '<scr' + 'ipt>';
  const scriptClose = '</' + 'script>';
  w.document.write(`<!DOCTYPE html><html><head><title>${escapeHtml(filename)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
      @page { size: A4; margin: 14mm 12mm; }
      html, body { margin: 0; padding: 0; background: #fff; }
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      @media print { .letter { box-shadow: none !important; padding: 0 !important; max-width: 100% !important; } }
    </style></head><body>
    <div class="letter-wrap" style="background:#fafafa;padding:24px 0;">
      ${html}
    </div>
    <p style="font-family:-apple-system,sans-serif;font-size:11px;color:#999;text-align:center;padding:8px 20px 24px;margin:0;">In the print dialog, choose "Save as PDF" as the destination. Suggested filename: <strong>${escapeHtml(filename)}</strong></p>
    ${scriptOpen}setTimeout(() => window.print(), 500);${scriptClose}
    </body></html>`);
  w.document.close();
  toast(`📄 PDF — suggested filename: "${filename}"`, 'success');
}

function downloadDOCX(id) {
  const v = ALL_JOBS.find(x => x.id === id);
  if (!v) { toast('Job not found', 'error'); return; }
  if (!GENERATED[id]) { toast('Generate the letter first', 'error'); return; }
  const companyName = sanitizeFilename(v.company || 'Unknown');
  const filename = `Cover Letter - ${companyName}.docx`;
  const letterHTML = generateCoverLetterHTML(v, APPROVALS[id]?.type || 'Full-time');
  // Wrap in Word-compatible HTML document with same styling + Google Fonts fallback
  const html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
<head>
<meta charset="utf-8">
<title>${escapeHtml(filename)}</title>
<!--[if gte mso 9]>
<xml>
  <w:WordDocument>
    <w:View>Print</w:View>
    <w:Zoom>100</w:Zoom>
    <w:DoNotOptimizeForBrowser/>
  </w:WordDocument>
</xml>
<![endif]-->
<style>
  @page { size: A4; margin: 14mm 12mm; }
  body { background: #fff; color: #1a1a1a; }
  .letter { font-family: 'Inter', -apple-system, 'Segoe UI', Calibri, sans-serif; max-width: 680px; margin: 0 auto; padding: 64px 68px; line-height: 1.7; font-size: 14.5px; }
  .letter header { margin-bottom: 0; }
  .letter header > div:nth-child(1) { font-family: 'Lora', 'Source Serif Pro', Georgia, serif; font-size: 30px; font-weight: 600; letter-spacing: -0.02em; color: #0a0a0a; line-height: 1.15; }
  .letter header > div:nth-child(2) { font-size: 12.5px; color: #6b7280; margin-top: 6px; font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; }
  .letter header > div:nth-child(3) { font-size: 13px; color: #4b5563; margin-top: 18px; line-height: 1.75; }
  .letter header > div:nth-child(3) a { color: #4b5563; text-decoration: none; border-bottom: 1px solid #d1d5db; }
  .letter section { margin: 0 0 24px; }
  .letter footer { margin-top: 32px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
  .letter footer > div:nth-child(1) { margin-bottom: 4px; color: #6b7280; font-size: 13px; }
  .letter footer > div:nth-child(2) { font-family: 'Lora', 'Source Serif Pro', Georgia, serif; font-size: 20px; font-weight: 600; color: #0a0a0a; margin-top: 2px; letter-spacing: -0.01em; }
  .letter footer > div:nth-child(3) { font-size: 12.5px; color: #6b7280; margin-top: 10px; line-height: 1.7; }
  .letter footer > div:nth-child(3) a { color: #6b7280; text-decoration: none; }
  .letter p { margin: 0 0 16px; text-align: justify; }
  .letter ul { margin: 0; padding: 0; list-style: none; }
  .letter ul li { margin-bottom: 10px; padding-left: 18px; position: relative; line-height: 1.65; }
  .letter ul li > span:nth-child(1) { position: absolute; left: 0; top: 0; color: #0a0a0a; font-weight: 700; }
  .letter ul li > strong { color: #0a0a0a; font-weight: 600; }
  .letter ul li > span:nth-child(3) { color: #4b5563; }
  .letter a { color: inherit; }
</style>
</head>
<body>
${letterHTML}
</body></html>`;
  const blob = new Blob([html], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast(`📝 DOCX — filename: "${filename}"`, 'success');
}

function updateStats() {
  document.getElementById('stat-total').textContent = ALL_JOBS.length;
  document.getElementById('stat-5').textContent = ALL_JOBS.filter(r => r.score === '5').length;
  document.getElementById('stat-4').textContent = ALL_JOBS.filter(r => r.score === '4').length;
  document.getElementById('stat-approved').textContent = Object.keys(APPROVALS).length;
  document.getElementById('stat-generated').textContent = Object.keys(GENERATED).length;
  document.getElementById('queue-count').textContent = Object.keys(APPROVALS).length;
}

function toast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type ? ' ' + type : '');
  setTimeout(() => t.className = 'toast', 3500);
}

// ===== Filename helper — keep spaces, hyphens; replace special chars with spaces =====
function sanitizeFilename(s) {
  return (s || 'Unknown')
    .replace(/[^a-z0-9\s-]/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// ===== Styled HTML cover letter (for PDF + DOCX export) =====
function generateCoverLetterHTML(v, type) {
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const isFreelance = type === 'Freelance';
  const isPartTime = type === 'Part-time';

  const opening = isFreelance
    ? `I'd like to discuss a potential freelance engagement for the ${v.role} role at ${v.company}.`
    : `I'm applying for the ${v.role} role at ${v.company}.`;

  const typeSpecific = isPartTime
    ? `I'm particularly interested in part-time arrangements${(v.location || '').toLowerCase().includes('remote') ? ', with capacity for remote collaboration across timezones' : ' with flexible scheduling'}.`
    : isFreelance
    ? `For freelance work, I can scope to a defined deliverable, ship against a milestone plan, and invoice through a contractor agreement. My typical availability is 30-40 hours/week with overlap on Cairo/Makkah business hours.`
    : `I'm available full-time, Egypt-based, and can start within 2-4 weeks of an accepted offer.`;

  const stack = v.stack_match || 'ASP.NET Core, .NET, backend';
  const fitParts = [
    `<strong>${escapeHtml(stack)}</strong>`,
    v.location ? escapeHtml(v.location) + (v.remote === 'yes' ? ' · remote-friendly' : '') : null,
    v.score ? `${v.score}★ match score` : null
  ].filter(Boolean);

  const closing = isFreelance
    ? `Happy to share my rate card, references from prior engagements, and a short scope for evaluation.`
    : `Happy to do a paid take-home or technical screen to let the work speak for itself.`;

  const highlights = [
    { name: 'Khzama',     desc: 'multi-tenant charity donation SaaS on Azure App Service (Clean Architecture, JWT-secured REST APIs, KSA-aligned payment workflows).' },
    { name: 'Matrix',     desc: 'social-media ad-tech platform with Meta + TikTok Ads API integration and AWS payment gateway (transactional integrity, retries, reconciliation).' },
    { name: 'NumeriiSoft',desc: 'numerology API platform unifying 3+ third-party providers behind a single JSON contract.' },
    { name: 'Aqwon',      desc: 'financial aid application portal with multi-step approval workflow and role-based access control.' }
  ];

  const subject = isFreelance
    ? `Freelance Inquiry — ${v.role}`
    : `Application — ${v.role}`;

  // Modern, structured, print-safe typography.
  // Fonts: Inter (body) + Lora (name heading) — both via Google Fonts.
  return `<div class="letter" style="
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    max-width: 680px;
    margin: 0 auto;
    padding: 64px 68px;
    color: #1a1a1a;
    line-height: 1.7;
    font-size: 14.5px;
    background: #fff;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-feature-settings: 'cv11', 'ss01', 'ss03';
  ">
    <!-- Letterhead: name (serif) + title + contact -->
    <header style="margin-bottom: 0;">
      <div style="
        font-family: 'Lora', 'Source Serif Pro', Georgia, 'Times New Roman', serif;
        font-size: 30px;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: #0a0a0a;
        line-height: 1.15;
      ">Mahmoud ElHassan</div>
      <div style="
        font-size: 12.5px;
        color: #6b7280;
        margin-top: 6px;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      ">Junior .NET Backend Developer</div>
      <div style="
        font-size: 13px;
        color: #4b5563;
        margin-top: 18px;
        line-height: 1.75;
      ">
        <a href="mailto:${PROFILE.email}" style="color:#4b5563;text-decoration:none;border-bottom:1px solid #d1d5db;">${PROFILE.email}</a>
        &nbsp;·&nbsp; ${PROFILE.phone}
        <br>Cairo, Egypt &nbsp;·&nbsp; open to sponsorship and remote
      </div>
    </header>

    <!-- Accent divider -->
    <div style="height: 2px; background: linear-gradient(90deg, #0a0a0a 0%, #0a0a0a 30%, #d4d4d8 30%, #d4d4d8 100%); margin: 30px 0 26px;"></div>

    <!-- Date + Recipient block -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 32px; margin-bottom: 28px;">
      <div style="flex: 1; min-width: 0;">
        <div style="font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; margin-bottom: 6px;">To</div>
        <div style="font-weight: 600; color: #0a0a0a; font-size: 15px;">${escapeHtml(v.company)} Hiring Team</div>
        <div style="font-size: 13px; color: #6b7280; margin-top: 3px;">${escapeHtml(v.location || 'Location TBD')}${v.remote === 'yes' ? ' · Remote' : ''}</div>
      </div>
      <div style="text-align: right; flex-shrink: 0;">
        <div style="font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; margin-bottom: 6px;">Date</div>
        <div style="font-size: 13px; color: #4b5563;">${today}</div>
      </div>
    </div>

    <!-- Subject line -->
    <div style="
      font-size: 14px;
      font-weight: 600;
      color: #0a0a0a;
      margin-bottom: 22px;
      padding: 10px 14px;
      background: #f9fafb;
      border-left: 3px solid #0a0a0a;
      border-radius: 0 4px 4px 0;
    ">Re: ${escapeHtml(subject)}</div>

    <!-- Salutation -->
    <div style="margin-bottom: 16px;">Dear ${escapeHtml(v.company)} Hiring Team,</div>

    <!-- Opening paragraph -->
    <p style="margin: 0 0 16px; text-align: justify; hyphens: auto;">${escapeHtml(opening)} ${escapeHtml(typeSpecific)}</p>

    <!-- Fit block -->
    <p style="margin: 0 0 16px; text-align: justify; hyphens: auto;">
      <strong style="color:#0a0a0a;">What makes this a strong match:</strong>
      ${fitParts.join(' &nbsp;·&nbsp; ')}.
    </p>

    <!-- Three-signal value prop -->
    <p style="margin: 0 0 24px; text-align: justify; hyphens: auto;">
      I bring three signals uncommon together:
      <strong>${PROFILE.yearsExp} years of professional .NET work</strong>,
      <strong>1.5 years at Digital Tamkeen in Makkah with KSA market delivery</strong>, and
      <strong>AWS payment gateway integration in production</strong>.
    </p>

    <!-- Highlights section -->
    <section style="margin: 0 0 24px;">
      <div style="
        font-size: 11px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 700;
        margin-bottom: 12px;
      ">Selected production highlights</div>
      <ul style="margin: 0; padding: 0; list-style: none;">
        ${highlights.map(h => `
          <li style="margin-bottom: 10px; padding-left: 18px; position: relative; line-height: 1.65;">
            <span style="position: absolute; left: 0; top: 0; color: #0a0a0a; font-weight: 700;">▸</span>
            <strong style="color: #0a0a0a; font-weight: 600;">${h.name}</strong>
            <span style="color: #4b5563;"> — ${h.desc}</span>
          </li>
        `).join('')}
      </ul>
    </section>

    <!-- Closing paragraph -->
    <p style="margin: 0 0 28px; text-align: justify; hyphens: auto;">${escapeHtml(closing)}</p>

    <!-- Signature -->
    <footer style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
      <div style="margin-bottom: 4px; color: #6b7280; font-size: 13px;">Best regards,</div>
      <div style="
        font-family: 'Lora', 'Source Serif Pro', Georgia, serif;
        font-size: 20px;
        font-weight: 600;
        color: #0a0a0a;
        margin-top: 2px;
        letter-spacing: -0.01em;
      ">Mahmoud ElHassan</div>
      <div style="font-size: 12.5px; color: #6b7280; margin-top: 10px; line-height: 1.7;">
        <a href="https://linkedin.com/in/mahmoud-elhassan-94r" style="color:#6b7280;text-decoration:none;">linkedin.com/in/mahmoud-elhassan-94r</a>
        &nbsp;·&nbsp;
        <a href="https://github.com/MahmoudElHassan" style="color:#6b7280;text-decoration:none;">github.com/MahmoudElHassan</a>
        &nbsp;·&nbsp;
        <a href="https://mahmoud-portofolio-eta.vercel.app" style="color:#6b7280;text-decoration:none;">mahmoud-portofolio-eta.vercel.app</a>
      </div>
    </footer>
  </div>`;
}

// Event listeners
['search', 'filter-score', 'filter-source', 'filter-status', 'filter-company'].forEach(id => {
  document.getElementById(id).addEventListener('input', render);
  document.getElementById(id).addEventListener('change', render);
});

// Init
loadData();
