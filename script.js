// =============================================================================
// script.js — CONNECTED TO FLASK BACKEND
// Structure is identical to your original.
// localStorage replaced with fetch() calls to app.py.
// HTML/CSS is untouched.
// =============================================================================

// ── AUTHENTICATED FETCH ───────────────────────────────────────────────────────
// Wraps every fetch() call with the instructor email header
// so Flask knows which instructor is making the request.
function authFetch(url, options = {}) {
    const session = JSON.parse(localStorage.getItem('active_session') || '{}');
    const email   = session.email || '';
    options.headers = Object.assign(options.headers || {}, {
        'X-Instructor-Email': email
    });
    return fetch(url, options);
}

let schedules       = [];
let classFolders    = [];
let historyFolders  = [];
let attendanceLogs  = {};
let selectedDay     = "MON";
let searchVal       = "";
let currentType     = 'home';
let editIdx                 = -1;
let editSchedId             = -1;
let _editingSchedOldSubject = '';
let selectedHistoryIdx  = 0;
let showAllHistoryFiles = false;
let currentOpenedFolder = "";   // stores class_code of the open folder
let currentStatusFilter  = 'All'; // student list filter: All/Enrolled/Unenrolled/Dropped
let studentSearchVal     = '';    // student name/SR search inside folder view

// ── ON LOAD ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    updateTime();
    setInterval(updateTime, 1000);
    generateTimeOptions();

    const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const today = new Date();
    selectedDay = days[today.getDay()];

    renderDayFilters();
    showPage('home');

    const session = JSON.parse(localStorage.getItem('active_session'));
    if (session && session.email) {
        const userName  = session.name || "Instructor";
        const userEmail = session.email;
        const userPhoto = session.profilePic;

        // Sidebar: large name, small "Instructor" role label, then email
        const nameDispEl  = document.getElementById('user-display-name');
        const emailDispEl = document.getElementById('user-display-email');
        if (nameDispEl)  nameDispEl.textContent = userName;
        if (emailDispEl) emailDispEl.textContent = userEmail;

        // Profile photo or initials in the circle
        const photoEl = document.getElementById('user-display-photo');
        if (photoEl && userPhoto) photoEl.src = userPhoto;
    } else {
        window.location.href = "/";
        return;
    }

    // Load schedules from backend on startup
    await loadSchedules();
    renderDayFilters();

    lucide.createIcons();
});

// ── CLOCK ─────────────────────────────────────────────────────────────────────

// ── ENVIRONMENT DETECTION ────────────────────────────────────────────────────
// The buttons are injected via innerHTML so getElementById on DOMContentLoaded
// won't find them. Instead we check the environment HERE, at render time,
// directly inside the template string that builds the buttons.
function isLocalEnvironment() {
    const host = window.location.hostname;
    return host === '127.0.0.1' || host === 'localhost';
}

function updateTime() {
    const clockEl = document.getElementById('clock');
    const dateEl  = document.getElementById('date');
    const now     = new Date();
    if (clockEl) clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    if (dateEl)  dateEl.textContent  = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

// ── TIME OPTIONS (unchanged) ──────────────────────────────────────────────────

function generateTimeOptions() {
    const from = document.getElementById('modalTimeFrom');
    const to   = document.getElementById('modalTimeTo');
    if (!from || !to) return;
    let options = "";
    for (let i = 7; i <= 21; i++) {
        const hour = i > 12 ? i - 12 : i;
        const ampm = i >= 12 ? 'PM' : 'AM';
        const t1 = `${hour}:00 ${ampm}`;
        const t2 = `${hour}:30 ${ampm}`;
        options += `<option value="${t1}">${t1}</option><option value="${t2}">${t2}</option>`;
    }
    from.innerHTML = options;
    to.innerHTML   = options;
}

// ── NAVIGATION (unchanged) ────────────────────────────────────────────────────

let isProfileEditing = false;

function showPage(pageId, btn) {
    // Auto-close mobile nav menu when any page is selected
    const mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
        mobileMenu.classList.add('hidden');
    }
    const contentArea = document.getElementById('content-area');
    const profilePage = document.getElementById('profilePage');

    const session = JSON.parse(localStorage.getItem('active_session'));
    if (session && session.profilePic) {
        const sidebarPhoto = document.getElementById('user-display-photo');
        if (sidebarPhoto) sidebarPhoto.src = session.profilePic;
    }

    if (contentArea) contentArea.classList.add('hidden');
    if (profilePage) profilePage.classList.add('hidden');

    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('sidebar-active'));
    if (btn) btn.classList.add('sidebar-active');

    searchVal   = "";
    currentType = pageId;

    if (pageId === 'profile') {
        if (profilePage) profilePage.classList.remove('hidden');
        loadProfileData();
        setTimeout(() => { lucide.createIcons(); }, 100);
    } else {
        if (contentArea) contentArea.classList.remove('hidden');
        if (pageId === 'home')         renderDashboard();
        else if (pageId === 'classes') renderFolderPage('classes');
        else if (pageId === 'history') renderHistoryPage();
    }

    lucide.createIcons();
}

// ── ADD: loadProfileData ──────────────────────────────────────────────────────

async function loadProfileData() {
    const session = JSON.parse(localStorage.getItem('active_session'));
    if (session) {
        const nameEl    = document.getElementById('prof-name');
        const fullNmEl  = document.getElementById('modal-user-full-name');
        const emailEl   = document.getElementById('prof-email');
        const numberEl  = document.getElementById('prof-number');
        const photoEl   = document.getElementById('modal-user-photo');
        if (nameEl)   nameEl.value       = session.name   || "";
        if (fullNmEl) fullNmEl.innerText  = session.name   || "";
        if (emailEl)  emailEl.value       = session.email  || "";
        if (numberEl) numberEl.value      = session.number || "";
        if (photoEl && session.profilePic) photoEl.src = session.profilePic;
    }

    // Load mail config + grace periods from DB
    try {
        const res = await authFetch('/api/mail_config');
        const cfg = await res.json();
        const gmailEl   = document.getElementById('mail-gmail');
        const appPassEl = document.getElementById('mail-app-pass');
        const presentEl = document.getElementById('time-present');
        const lateEl    = document.getElementById('time-late');
        if (gmailEl)   gmailEl.value   = cfg.gmail         || "";
        if (appPassEl) appPassEl.value = cfg.app_pass       || "";
        if (presentEl) presentEl.value = cfg.present_grace  ?? 15;
        if (lateEl)    lateEl.value    = cfg.late_grace     ?? 30;
        // Mirror to localStorage so camera session reads grace periods instantly
        localStorage.setItem('mail_config', JSON.stringify({
            gmail:        cfg.gmail        || "",
            appPass:      cfg.app_pass     || "",
            presentGrace: cfg.present_grace ?? 15,
            lateGrace:    cfg.late_grace   ?? 30,
        }));
    } catch {
        // Fallback to localStorage if offline
        const mailData  = JSON.parse(localStorage.getItem('mail_config') || '{}');
        const gmailEl   = document.getElementById('mail-gmail');
        const appPassEl = document.getElementById('mail-app-pass');
        const presentEl = document.getElementById('time-present');
        const lateEl    = document.getElementById('time-late');
        if (gmailEl)   gmailEl.value   = mailData.gmail        || "";
        if (appPassEl) appPassEl.value = mailData.appPass      || "";
        if (presentEl) presentEl.value = mailData.presentGrace || "15";
        if (lateEl)    lateEl.value    = mailData.lateGrace    || "30";
    }
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────

async function renderDashboard() {
    const content = document.getElementById('content-area');
    content.innerHTML = `
        <div class="mb-10">
            <h1 class="text-4xl font-black text-gray-900 mb-2 tracking-tighter">Dashboard</h1>
            <p class="text-gray-400 text-sm font-bold uppercase tracking-widest">Attendance Monitoring</p>
        </div>

        <!-- Search + Class Folder Filter row -->
        <div class="flex gap-3 mb-10">
            <div class="relative flex-1">
                <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>
                <input id="dashSearch" type="text"
                    placeholder="Search by subject, section, or date..."
                    oninput="filterDashboardActivity()"
                    class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none ring-1 ring-gray-100 focus:ring-red-200 transition">
            </div>
            <div class="relative">
                <i data-lucide="folder" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300 pointer-events-none"></i>
                <select id="dashFolderFilter" onchange="filterDashboardActivity()"
                    class="appearance-none bg-gray-50 border-none rounded-2xl py-4 pl-11 pr-10 text-sm font-bold outline-none ring-1 ring-gray-100 focus:ring-red-200 transition text-gray-500 cursor-pointer min-w-[200px]">
                    <option value="">All Class Folders</option>
                </select>
                <i data-lucide="chevron-down" class="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300 pointer-events-none"></i>
            </div>
        </div>

        <div class="bg-white p-8 rounded-[3rem] border border-gray-100 shadow-sm mb-10 h-[450px]">
             <h3 class="text-lg font-black text-gray-800 mb-1 flex items-center"><i data-lucide="pie-chart" class="w-5 h-5 mr-2 text-[#D32F2F]"></i> Absence Rate by Class</h3>
             <p class="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-4">Average absences per session &amp; overall percentage</p>
             <div class="h-[330px] w-full"><canvas id="absentChart"></canvas></div>
        </div>

        <div class="bg-white p-8 rounded-[3rem] border border-gray-100 shadow-sm">
            <div class="flex items-center justify-between mb-6">
                <h3 class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Recent Activity</h3>
                <span id="dashResultCount" class="text-[10px] font-black text-gray-300 uppercase tracking-wider"></span>
            </div>
            <div id="recentActivityList" class="space-y-4">
                <p class="text-center text-gray-300 font-bold py-4">Loading...</p>
            </div>
        </div>`;
    lucide.createIcons();

    // Load absence chart
    try {
        const res  = await authFetch('/api/absences');
        const data = await res.json();
        initChart(data);
    } catch {
        initChart([]);
    }

    // Load recent activity
    try {
        const res     = await authFetch('/api/recent');
        const records = await res.json();

        // Store globally for filtering
        window._allRecentRecords = records;

        // Populate folder filter dropdown with distinct classes from records
        const folderSel = document.getElementById('dashFolderFilter');
        if (folderSel && records.length) {
            const seen = new Map();  // class_code → label
            records.forEach(r => {
                if (!seen.has(r.class_code)) {
                    seen.set(r.class_code, `${r.subject} — ${r.section}`);
                }
            });
            seen.forEach((label, code) => {
                const opt = document.createElement('option');
                opt.value       = code;
                opt.textContent = label;
                folderSel.appendChild(opt);
            });
        }

        // Initial render
        renderRecentActivityList(records);
        lucide.createIcons();

    } catch {
        document.getElementById('recentActivityList').innerHTML =
            '<p class="text-center text-gray-300 font-bold py-4">Could not load recent activity.</p>';
    }
}

// ── DASHBOARD FILTER ──────────────────────────────────────────────────────────

function filterDashboardActivity() {
    const query  = (document.getElementById('dashSearch')?.value   || '').trim().toLowerCase();
    const folder = (document.getElementById('dashFolderFilter')?.value || '');
    const all    = window._allRecentRecords || [];

    const filtered = all.filter(r => {
        // Class folder filter
        if (folder && r.class_code !== folder) return false;
        // Text search across subject, section, date
        if (!query) return true;
        const subject = (r.subject  || '').toLowerCase();
        const section = (r.section  || '').toLowerCase();
        const date    = (r.date     || '').toLowerCase();
        const code    = (r.class_code || '').toLowerCase();
        return subject.includes(query) || section.includes(query) ||
               date.includes(query)    || code.includes(query);
    });

    renderRecentActivityList(filtered, query || folder ? all.length : null);
}

function renderRecentActivityList(records, totalCount = null) {
    const list    = document.getElementById('recentActivityList');
    const countEl = document.getElementById('dashResultCount');
    if (!list) return;

    // Update result count badge
    if (countEl) {
        countEl.textContent = totalCount !== null
            ? `${records.length} of ${totalCount} results`
            : records.length > 0 ? `${records.length} records` : '';
    }

    if (records.length === 0) {
        const isFiltered = totalCount !== null;
        list.innerHTML = isFiltered
            ? `<div class="text-center py-10">
                   <p class="text-gray-300 font-bold text-sm">No matching records found.</p>
                   <p class="text-gray-200 text-[10px] mt-1 font-bold">Try a different search or folder.</p>
               </div>`
            : '<p class="text-center text-gray-300 font-bold py-4">No recent history.</p>';
        return;
    }

    list.innerHTML = records.map(r => {
        const dateObj  = new Date(r.date + 'T00:00:00');
        const dateStr  = dateObj.toLocaleDateString('en-US', { weekday:'short', day:'2-digit', month:'short', year:'numeric' });
        const timeRaw  = (r.time || '').substring(0, 8);
        const dispTime = timeRaw
            ? new Date('1970-01-01T' + timeRaw).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', second:'2-digit' })
            : '';
        const filename = `${dateStr} ${dispTime}_Report.pdf`;

        return `
        <div class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl cursor-pointer hover:bg-red-50 transition group"
             onclick="goToHistoryByClassDate('${r.class_code}', '${r.date}')">
            <div class="flex items-center space-x-4">
                <div class="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-[#D32F2F] shadow-sm group-hover:bg-[#D32F2F] group-hover:text-white transition">
                    <i data-lucide="file-text" class="w-4 h-4"></i>
                </div>
                <div>
                    <p class="text-sm font-black text-gray-900">${filename}</p>
                    <!-- Class folder badge -->
                    <div class="flex items-center gap-2 mt-0.5">
                        <span class="inline-flex items-center gap-1 bg-red-50 text-[#D32F2F] text-[9px] font-black px-2 py-0.5 rounded-lg uppercase tracking-wide">
                            <i data-lucide="folder" class="w-2.5 h-2.5"></i>
                            ${r.subject}
                        </span>
                        <span class="text-[9px] text-gray-400 font-bold uppercase">${r.section}</span>
                    </div>
                </div>
            </div>
            <p class="text-[9px] text-gray-400 font-bold">${dispTime}</p>
        </div>`;
    }).join('');

    lucide.createIcons();
}

// Chart — uses real absence data from backend (Doughnut style)
function initChart(data = []) {
    const ctx = document.getElementById('absentChart');
    if (!ctx) return;

    if (window._absentChartInstance) {
        window._absentChartInstance.destroy();
    }

    // Color by severity
    const getColor = pct => pct >= 50 ? '#D32F2F' : pct >= 25 ? '#E65100' : '#F59E0B';

    // Plugin: draws centered text inside the doughnut hole
    const centerLabelPlugin = {
        id: 'centerLabel',
        afterDraw(chart) {
            if (chart.config.type !== 'doughnut') return;
            const { ctx: c, chartArea: { top, left, width, height } } = chart;
            const cx = left + width / 2;
            const cy = top  + height / 2;
            c.save();

            const vals = chart.data.datasets[0]?.data || [];
            const hasData = vals.length > 1 || (vals.length === 1 && vals[0] !== 1);

            if (hasData) {
                const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
                c.font = 'bold 26px Inter, sans-serif';
                c.fillStyle = '#1a1a1a';
                c.textAlign = 'center';
                c.textBaseline = 'middle';
                c.fillText(avg + '%', cx, cy - 10);
                c.font = '700 9px Inter, sans-serif';
                c.fillStyle = '#9CA3AF';
                c.letterSpacing = '1.5px';
                c.fillText('AVG ABSENCE', cx, cy + 13);
            } else {
                c.font = '600 12px Inter, sans-serif';
                c.fillStyle = '#D1D5DB';
                c.textAlign = 'center';
                c.textBaseline = 'middle';
                c.fillText('No data yet', cx, cy);
            }
            c.restore();
        }
    };

    if (!data.length) {
        window._absentChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['No Data'],
                datasets: [{ data: [1], backgroundColor: ['#F3F4F6'], borderWidth: 0 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                cutout: '72%',
                plugins: { legend: { display: false }, tooltip: { enabled: false } }
            },
            plugins: [centerLabelPlugin]
        });
        return;
    }

    const labels  = data.map(d => d.name);
    const pctVals = data.map(d => d.pct_absent);
    const avgVals = data.map(d => d.avg_absent);
    const totVals = data.map(d => d.total_absent);
    const sesVals = data.map(d => d.total_sessions);
    const colors  = pctVals.map(getColor);

    window._absentChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: pctVals,
                backgroundColor: colors,
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 10,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 18,
                        font: { size: 10, weight: 'bold', family: 'Inter' },
                        color: '#6B7280',
                    }
                },
                tooltip: {
                    backgroundColor: '#111827',
                    titleColor: '#F9FAFB',
                    bodyColor: '#D1D5DB',
                    padding: 14,
                    cornerRadius: 12,
                    callbacks: {
                        title: items => items[0].label,
                        label: item => {
                            const i = item.dataIndex;
                            return [
                                `  Absence Rate : ${pctVals[i]}%`,
                                `  Avg / Session: ${avgVals[i]} students`,
                                `  Total Absences: ${totVals[i]}`,
                                `  Sessions       : ${sesVals[i]}`
                            ];
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                duration: 900,
                easing: 'easeInOutQuart'
            }
        },
        plugins: [centerLabelPlugin]
    });
}

// ── CLASSES (FOLDERS) ─────────────────────────────────────────────────────────

async function renderFolderPage(type) {
    currentType = type;

    // Load classes from backend
    try {
        const res = await authFetch('/api/classes');
        classFolders = await res.json();
    } catch {
        classFolders = [];
    }

    const filtered = classFolders.filter(f =>
        (f.subject + f.section + f.course_code).toLowerCase().includes(searchVal.toLowerCase())
    );

    document.getElementById('content-area').innerHTML = `
        <div class="flex justify-between items-center mb-10">
            <h1 class="text-3xl font-black text-gray-900 tracking-tighter uppercase">${type}</h1>
            <button onclick="openFolderModal()" class="bg-[#D32F2F] text-white px-6 py-3 rounded-xl text-xs font-bold shadow-lg shadow-red-100">+ Create Folder</button>
        </div>
        <div class="relative mb-10">
            <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>
            <input type="text" oninput="searchVal = this.value; renderFolderPage('${type}')" value="${searchVal}" placeholder="Search..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            ${filtered.map((f, i) => `
                <div onclick="openFolderView('${f.id}')" class="bg-white p-6 rounded-[2rem] border border-gray-100 shadow-sm hover:shadow-xl cursor-pointer group">
                    <div class="flex justify-between mb-4">
                        <div class="w-12 h-12 bg-red-50 rounded-2xl flex items-center justify-center text-[#D32F2F] group-hover:bg-[#D32F2F] group-hover:text-white transition">
                            <i data-lucide="folder"></i>
                        </div>
                        <div class="flex space-x-1" onclick="event.stopPropagation()">
                            <button onclick="editFolder('${f.id}')" class="p-2 text-gray-300 hover:text-blue-500"><i data-lucide="edit-3" class="w-4 h-4"></i></button>
                            <button onclick="confirmAction('deleteFolder', '${f.id}')" class="p-2 text-gray-300 hover:text-red-500"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                        </div>
                    </div>
                    <h3 class="font-black text-gray-900 text-lg">${f.subject}</h3>
                    <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">${f.section} • ${f.course_code}</p>
                </div>`).join('')}
        </div>`;
    lucide.createIcons();
}

// ── HISTORY ───────────────────────────────────────────────────────────────────

// History state
let historySelectedClass   = null;
let historySelectedSession = null;
let historyClassSessions   = [];

async function renderHistoryPage() {
    currentType = 'history';

    try {
        const res = await authFetch('/api/classes');
        classFolders = await res.json();
    } catch { classFolders = []; }

    const filtered = classFolders.filter(f =>
        (f.subject + f.section).toLowerCase().includes(searchVal.toLowerCase())
    );

    document.getElementById('content-area').innerHTML = `
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-4xl font-black text-gray-900 tracking-tighter uppercase">History</h1>
        </div>
        <div class="relative mb-6">
            <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>
            <input type="text" oninput="searchVal=this.value; renderHistoryPage()" value="${searchVal}"
                placeholder="Search classes..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">
        </div>
        <div class="flex gap-6 h-[calc(100vh-280px)] min-h-[400px]">

            <!-- Column 1: Class Folders -->
            <div class="w-60 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">
                <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-3">Class Folders</p>
                ${filtered.length === 0
                    ? '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No classes yet</p>'
                    : filtered.map(f => `
                        <div onclick="historySelectClass('${f.id}')"
                             class="p-4 rounded-2xl cursor-pointer transition border ${historySelectedClass === '${f.id}' ? 'bg-red-50 border-[#D32F2F]' : 'bg-white border-gray-100 hover:border-red-200'}">
                            <div class="flex items-center space-x-3">
                                <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${historySelectedClass === '${f.id}' ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-[#D32F2F]'}">
                                    <i data-lucide="folder" class="w-4 h-4"></i>
                                </div>
                                <div class="min-w-0">
                                    <p class="font-black text-gray-900 text-sm truncate">${f.subject}</p>
                                    <p class="text-[9px] text-gray-400 font-bold uppercase truncate">${f.section}</p>
                                </div>
                            </div>
                        </div>`).join('')}
            </div>

            <!-- Column 2: Attendance Files -->
            <div class="w-60 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">
                <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-3">Attendance Files</p>
                <div id="historyFilesList">
                    <p class="text-[10px] text-gray-300 font-bold text-center py-8">Select a class folder</p>
                </div>
            </div>

            <!-- Column 3: Detail panel -->
            <div class="flex-1 overflow-y-auto">
                <div id="historyDetailPanel" class="h-full bg-gray-50/50 border-2 border-dashed border-gray-200 rounded-[2.5rem] p-8 flex flex-col">
                    <div class="flex-1 flex items-center justify-center text-gray-300 font-bold text-xs uppercase">
                        Select an attendance file
                    </div>
                </div>
            </div>
        </div>`;
    lucide.createIcons();

    if (historySelectedClass) {
        await historyLoadFiles(historySelectedClass);
        if (historySelectedSession) {
            await historyLoadDetail(
                historySelectedSession.class_code,
                historySelectedSession.date,
                historySelectedSession.session_time
            );
        }
    }
}

async function historySelectClass(class_code) {
    historySelectedClass   = class_code;
    historySelectedSession = null;
    await renderHistoryPage();
}

async function historyLoadFiles(class_code) {
    const listEl = document.getElementById('historyFilesList');
    if (!listEl) return;
    listEl.innerHTML = '<p class="text-[9px] text-gray-400 text-center py-4">Loading...</p>';

    try {
        const res = await authFetch(`/api/sessions/${class_code}`);
        historyClassSessions = await res.json();
    } catch { historyClassSessions = []; }

    if (historyClassSessions.length === 0) {
        listEl.innerHTML = '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No records yet</p>';
        return;
    }

    listEl.innerHTML = historyClassSessions.map(s => {
        const isActive = historySelectedSession &&
                         historySelectedSession.date === s.date &&
                         historySelectedSession.session_time === s.session_time;

        // Parse date safely: PostgreSQL returns "YYYY-MM-DD" string
        const [yr, mo, dy] = (s.date || '').split('-');
        const shortDate = (mo && dy && yr) ? `${mo}-${dy}-${String(yr).slice(-2)}` : s.date;

        // Parse session_time: "HH:MM:SS" → "HH-MM"
        const timeSlug = s.session_time ? s.session_time.substring(0, 5).replace(':', '-') : '';
        const fileLabel = `Log_${shortDate}${timeSlug ? '_' + timeSlug : ''}`;

        // Display time in 12-hour format for subtitle
        const dispTime = s.session_time
            ? new Date('1970-01-01T' + s.session_time).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })
            : '';
        return `
            <div onclick="historySelectSession('${s.class_code}','${s.date}','${s.session_time || ''}')"
                 class="p-4 rounded-2xl cursor-pointer transition border ${isActive ? 'bg-red-50 border-[#D32F2F]' : 'bg-white border-gray-100 hover:border-red-200'}">
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-[#D32F2F]'}">
                        <i data-lucide="file-text" class="w-4 h-4"></i>
                    </div>
                    <div class="min-w-0">
                        <p class="font-black text-gray-900 text-xs truncate">${fileLabel}</p>
                        <p class="text-[9px] text-gray-400 font-bold">${dispTime} · P:${s.present} L:${s.late} A:${s.absent}</p>
                    </div>
                </div>
            </div>`;
    }).join('');
    lucide.createIcons();
}

async function historySelectSession(class_code, date, session_time) {
    historySelectedSession = { class_code, date, session_time };
    await historyLoadFiles(class_code);
    await historyLoadDetail(class_code, date, session_time);
}

async function historyLoadDetail(class_code, date, session_time) {
    const panel = document.getElementById('historyDetailPanel');
    if (!panel) return;
    panel.innerHTML = '<p class="text-[10px] text-gray-400 text-center py-8">Loading...</p>';

    try {
        const sp      = session_time ? `?session_time=${encodeURIComponent(session_time)}` : '';
        const res     = await authFetch(`/api/attendance/${class_code}/${date}${sp}`);
        const records = await res.json();
        const present = records.filter(r => r.status === 'Present');
        const late    = records.filter(r => r.status === 'Late');
        const absent  = records.filter(r => r.status === 'Absent');
        const cls     = classFolders.find(f => f.id === class_code) || {};
        // Parse date safely — PostgreSQL returns "YYYY-MM-DD" plain string
        const [dyr, dmo, ddy] = (date || '').split('-');
        const dispDate = (dyr && dmo && ddy)
            ? new Date(Number(dyr), Number(dmo)-1, Number(ddy)).toLocaleDateString('en-US',
                { weekday:'long', year:'numeric', month:'long', day:'numeric' })
            : date;

        const renderRows = (list, color, label) => list.length === 0
            ? '<p class="text-[10px] text-gray-300 font-bold py-2 pl-2">None</p>'
            : list.map(r => `
                <div class="flex items-center justify-between p-3 bg-white rounded-2xl border border-gray-100 mb-2">
                    <div>
                        <p class="text-sm font-black text-gray-900">${r.name}</p>
                        <p class="text-[9px] text-gray-400 font-bold">${r.sr_code || ''}</p>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] font-black ${color} uppercase">${label}</span>
                        <p class="text-[9px] text-gray-400">${r.timestamp ? formatDisplayTime(r.timestamp) : '—'}</p>
                    </div>
                </div>`).join('');

        panel.innerHTML = `
            <div class="flex justify-between items-start mb-6">
                <div>
                    <h3 class="font-black text-gray-900 text-lg">${cls.subject || class_code}</h3>
                    <p class="text-[10px] text-gray-400 font-bold uppercase">${cls.section || ''} · ${dispDate}</p>
                </div>
                <button onclick="viewAndPrintPDF('${class_code}','${date}','${session_time || ''}')"
                    class="flex items-center space-x-2 px-5 py-3 bg-[#D32F2F] text-white rounded-2xl font-bold text-xs hover:bg-[#B71C1C] transition shadow-lg">
                    <i data-lucide="printer" class="w-4 h-4"></i> <span>View &amp; Print</span>
                </button>
            </div>
            <div class="grid grid-cols-3 gap-4 mb-6">
                <div class="bg-green-50 rounded-2xl p-4 text-center">
                    <p class="text-2xl font-black text-green-600">${present.length}</p>
                    <p class="text-[9px] font-black text-green-400 uppercase">Present</p>
                </div>
                <div class="bg-yellow-50 rounded-2xl p-4 text-center">
                    <p class="text-2xl font-black text-yellow-600">${late.length}</p>
                    <p class="text-[9px] font-black text-yellow-400 uppercase">Late</p>
                </div>
                <div class="bg-red-50 rounded-2xl p-4 text-center">
                    <p class="text-2xl font-black text-red-600">${absent.length}</p>
                    <p class="text-[9px] font-black text-red-400 uppercase">Absent</p>
                </div>
            </div>
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Present (${present.length})</p>
            ${renderRows(present,'text-green-500','Present')}
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Late (${late.length})</p>
            ${renderRows(late,'text-yellow-500','Late')}
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Absent (${absent.length})</p>
            ${renderRows(absent,'text-red-500','Absent')}`;
        lucide.createIcons();
    } catch(e) {
        panel.innerHTML = '<p class="text-center text-gray-300 font-bold py-8 text-xs">Could not load records.</p>';
    }
}

function formatDisplayTime(ts) {
    if (!ts) return '—';
    try {
        const s = String(ts).trim();
        // PostgreSQL returns "YYYY-MM-DD HH:MM:SS" — extract the time part
        let timePart = '';
        if (s.includes(' ')) {
            timePart = s.split(' ')[1];          // "HH:MM:SS"
        } else if (s.includes('T')) {
            timePart = s.split('T')[1].substring(0, 8);
        } else {
            timePart = s.substring(0, 8);
        }
        if (!timePart) return '—';
        const d = new Date('1970-01-01T' + timePart);
        if (isNaN(d.getTime())) return timePart.substring(0, 5);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch { return String(ts).substring(11, 19) || String(ts); }
}

async function viewAndPrintPDF(class_code, date, session_time) {
    const cls = classFolders.find(f => f.id === class_code) || {};
    const sp  = session_time ? `?session_time=${encodeURIComponent(session_time)}` : '';

    try {
        const res     = await authFetch(`/api/attendance/${class_code}/${date}${sp}`);
        const records = await res.json();

        // ── Schedule info ────────────────────────────────────────────────────
        const sched   = schedules.find(s =>
            s.subject && cls.subject &&
            s.subject.trim().toLowerCase() === cls.subject.trim().toLowerCase());
        const timeVal = sched ? sched.time : '';
        const roomVal = sched ? sched.room : '';

        // ── Date (safe parse) ────────────────────────────────────────────────
        const [pyr, pmo, pdy] = (date || '').split('-');
        const dispDate = (pyr && pmo && pdy)
            ? new Date(Number(pyr), Number(pmo)-1, Number(pdy))
                .toLocaleDateString('en-US', { month:'numeric', day:'numeric', year:'numeric' })
            : date;

        // ── Faculty name ─────────────────────────────────────────────────────
        const session = JSON.parse(localStorage.getItem('active_session') || '{}');
        const faculty = (session.email || '').split('@')[0]
                          .replace(/[._]/g,' ').replace(/\b\w/g, l => l.toUpperCase());

        /// ── fixing part absent showing  ─────────────────────────────────

        // ── University format: ONLY Present and Late students in the roster ──
        // Absent students are NOT included — the dean monitors only those who
        // physically attended. The roster is renumbered sequentially starting
        // from 1 based on who actually attended.

        // Layout: rows 1–30 in the LEFT column, rows 31–60 in the RIGHT column.
        // The roster always has a minimum of 30 blank rows (one full left column).


        const attended     = records.filter(r => r.status !== 'Absent');
        const ROWS_PER_COL = 30;
        const totalRows    = Math.max(attended.length, ROWS_PER_COL);

        const paddedTotal  = totalRows <= ROWS_PER_COL
            ? ROWS_PER_COL
            : Math.ceil(totalRows / ROWS_PER_COL) * ROWS_PER_COL;


        const statusColor = s =>
            s === 'Present' ? 'green' : '#E65100';   // Present=green, Late=orange


        // Build rows: slot i = left col (1–30), slot i+30 = right col (31–60)

        const rosterRows = Array.from({ length: ROWS_PER_COL }).map((_, i) => {
            const sL   = attended[i];
            const sR   = attended[i + ROWS_PER_COL];

            const numL = i + 1;
            const numR = i + ROWS_PER_COL + 1;

        // Show Present/Late status in signature column; empty if no student in slot

            const sigL = sL
                ? `<span style="font-weight:bold;color:${statusColor(sL.status)};">${sL.status}</span>`
                : '';
            const sigR = sR
                ? `<span style="font-weight:bold;color:${statusColor(sR.status)};">${sR.status}</span>`
                : '';

            return `
            <tr>
                <td style="border:1px solid black;padding:3px 8px;height:25px;font-size:11px;font-family:'Times New Roman',serif;">
                    ${numL}. ${sL ? sL.name : ''}
                </td>
                <td style="border:1px solid black;text-align:center;font-size:11px;padding:3px;">
                    ${sigL}
                </td>
                <td style="border:1px solid black;padding:3px 8px;height:25px;font-size:11px;font-family:'Times New Roman',serif;">
                    ${numR}.${sR ? ' ' + sR.name : ''}
                </td>
                <td style="border:1px solid black;text-align:center;font-size:11px;padding:3px;">
                    ${sigR}
                </td>
            </tr>`;
        }).join('');

        // ── Short date for title bar ─────────────────────────────────────────
        const [yr, mo, dy] = (date || '').split('-');
        const shortDate = (mo && dy && yr) ? `${mo}-${dy}-${String(yr).slice(-2)}` : date;

        // ── Full HTML matching BatStateU-REC-ATT-11 Rev.01 exactly ───────────
        const html = `
            <div style="font-family:'Times New Roman',Times,serif;color:black;background:white;
                        width:100%;max-width:820px;margin:0 auto;padding:0;">

                <!-- Header: Logo + Reference block -->
                <table style="width:100%;border-collapse:collapse;font-size:10px;table-layout:fixed;">
                    <tr>
                        <td style="border:1px solid black;width:14%;text-align:center;padding:6px;">
                            <img src="bsu_logo.png" alt="BSU"
                                 style="height:48px;width:auto;display:block;margin:0 auto;">
                        </td>
                        <td style="border:1px solid black;width:29%;padding:5px 8px;">
                            Reference No.: <b>BatStateU-REC-ATT-11</b>
                        </td>
                        <td style="border:1px solid black;width:32%;padding:5px 8px;">
                            Effectivity Date: <b>May 18, 2022</b>
                        </td>
                        <td style="border:1px solid black;width:25%;padding:5px 8px;">
                            Revision No.: <b>01</b>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="4"
                            style="border:1px solid black;border-top:none;padding:10px 8px;
                                   text-align:center;font-size:14px;font-weight:bold;
                                   text-transform:uppercase;letter-spacing:1px;">
                            Student Class Attendance
                        </td>
                    </tr>
                </table>

                <!-- Info block -->
                <table style="width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed;">
                    <tr>
                        <td style="border:1px solid black;border-top:none;padding:6px 10px;">
                            Course Code and Title:&nbsp;&nbsp;<b>${cls.subject || ''}</b>&nbsp;(${cls.section || ''})
                        </td>
                    </tr>
                    <tr>
                        <td style="border:1px solid black;border-top:none;padding:6px 10px;">
                            Assigned Faculty:&nbsp;&nbsp;<b>${faculty}</b>
                        </td>
                    </tr>
                </table>
                <table style="width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed;">
                    <tr>
                        <td style="border:1px solid black;border-top:none;width:25%;padding:6px 10px;">
                            Date:&nbsp;<b>${dispDate}</b>
                        </td>
                        <td style="border:1px solid black;border-top:none;width:30%;padding:6px 10px;">
                            Time:&nbsp;<b>${timeVal}</b>
                        </td>
                        <td style="border:1px solid black;border-top:none;width:45%;padding:6px 10px;">
                            Room/Venue:&nbsp;<b>${roomVal}</b>
                        </td>
                    </tr>
                </table>

                <!-- Gray shade divider — matches BSU reference format -->
                <table style="width:100%;border-collapse:collapse;table-layout:fixed;">
                    <tr>
                        <td colspan="4"
                            style="border:1px solid black;border-top:none;
                                   background-color:#d9d9d9;
                                   -webkit-print-color-adjust:exact;
                                   print-color-adjust:exact;
                                   height:10px;padding:0;font-size:1px;line-height:1px;">&nbsp;</td>
                    </tr>
                </table>

                <!-- Two-column attendance roster — fixed 30 rows per column -->
                <table style="width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed;">
                    <thead>
                        <tr style="text-align:center;font-weight:bold;">
                            <td style="border:1px solid black;border-top:none;width:35%;padding:5px;">NAME</td>
                            <td style="border:1px solid black;border-top:none;width:15%;padding:5px;">SIGNATURE</td>
                            <td style="border:1px solid black;border-top:none;width:35%;padding:5px;">NAME</td>
                            <td style="border:1px solid black;border-top:none;width:15%;padding:5px;">SIGNATURE</td>
                        </tr>
                    </thead>
                    <tbody>
                        ${rosterRows}
                    </tbody>
                </table>
            </div>`;

        document.getElementById('printArea').innerHTML = html;

        // ── Mobile: zoom printArea content to fit screen width ───────────────
        requestAnimationFrame(() => {
            const printArea = document.getElementById('printArea');
            const inner = printArea?.querySelector('div');
            if (!inner) return;
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                // Reset any previous transform
                inner.style.transformOrigin = 'top left';
                inner.style.transform = 'none';
                inner.style.margin = '0';
                inner.style.padding = '16px';
                // Scale to fit: inner is typically 800px wide (BSU format)
                const targetW = 800;
                const availW  = printArea.clientWidth - 32;
                const scale   = Math.min(1, availW / targetW);
                inner.style.transform = `scale(${scale})`;
                inner.style.transformOrigin = 'top left';
                inner.style.width = targetW + 'px';
                inner.style.marginBottom = `-${Math.round(targetW * (1 - scale))}px`;
                printArea.style.padding = '0';
                printArea.style.overflow = 'auto';
            } else {
                inner.style.transform = '';
                inner.style.width = '';
                inner.style.transformOrigin = '';
                printArea.style.padding = '';
            }
        });

        // ── Print button — clean isolated window, auto-triggers print dialog ──
        window.printSheet = () => {
            const win = window.open('', '_blank', 'width=950,height=750');
            win.document.write(`<!DOCTYPE html><html><head>
                <meta charset="UTF-8">
                <style>
                    * { box-sizing:border-box; margin:0; padding:0; }
                    body { background:white; font-family:'Times New Roman',Times,serif; padding:16px; }
                    table { border-collapse:collapse; width:100%; }
                    @media print {
                        body { padding:0; margin:0; }
                        * { -webkit-print-color-adjust:exact !important;
                            print-color-adjust:exact !important; }
                    }
                </style>
                </head><body>${html}</body></html>`);
            win.document.close();
            win.focus();
            setTimeout(() => { win.print(); }, 400);
        };

        // ── Download PDF — uses Flask backend (reportlab) for reliable PDF ───
        // html2pdf/html2canvas produces blank PDFs due to canvas rendering bugs.
        // The backend generates a proper PDF using reportlab and streams it back.
        const dlBtn = document.getElementById('downloadBtn');
        if (dlBtn) {
            dlBtn.onclick = async () => {
                const origHTML = dlBtn.innerHTML;
                dlBtn.innerHTML = '<span>Downloading...</span>';
                dlBtn.disabled  = true;

                try {
                    const sp  = session_time ? `?session_time=${encodeURIComponent(session_time)}` : '';
                    const res = await authFetch(`/api/download_pdf/${class_code}/${date}${sp}`);

                    if (!res.ok) throw new Error(`Server error ${res.status}`);

                    const blob = await res.blob();
                    const url  = URL.createObjectURL(blob);
                    const a    = document.createElement('a');
                    a.href     = url;
                    a.download = `Attendance_${cls.subject || class_code}_${shortDate}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } catch (err) {
                    console.error('Download failed:', err);
                    alert('PDF download failed: ' + err.message);
                } finally {
                    dlBtn.innerHTML = origHTML;
                    dlBtn.disabled  = false;
                    if (window.lucide) lucide.createIcons();
                }
            };
        }

        // ── Update viewer title ──────────────────────────────────────────────
        document.getElementById('docTitle').innerText =
            `Attendance Sheet — ${cls.subject || class_code} | ${shortDate}`;
        document.getElementById('docViewer').classList.remove('hidden');

    } catch(e) {
        alert('Could not load record: ' + e.message);
    }
}

function goToHistoryByClassDate(class_code, date) {
    historySelectedClass = class_code;
    showPage('history');
}



// ── FOLDER VIEW (inside a class) ──────────────────────────────────────────────

async function openFolderView(class_code) {
    currentOpenedFolder = class_code;
    currentStatusFilter  = 'All';   // reset filter on folder open
    studentSearchVal     = '';      // reset student search on folder open
    const cls = classFolders.find(f => f.id === class_code) || {};

    // Load students FIRST then render camera button based on count
    let students = [];
    try {
        const res = await authFetch(`/api/students/${class_code}`);
        students  = await res.json();
    } catch {}

    renderFolderView(cls, class_code, students);
}

function renderFolderView(cls, class_code, students) {
    const hasStudents = students.length > 0;

    // Apply status filter + student search
    const filtered = students.filter(s => {
        const statusOk = currentStatusFilter === 'All' || (s.status || 'Enrolled') === currentStatusFilter;
        const q = studentSearchVal.trim().toLowerCase();
        const searchOk = !q ||
            s.name.toLowerCase().includes(q) ||
            (s.sr_code || '').toLowerCase().includes(q);
        return statusOk && searchOk;
    });

    document.getElementById('content-area').innerHTML = `
        <div class="flex justify-between items-start mb-8">
            <button onclick="showPage('classes')" class="text-gray-400 hover:text-[#D32F2F] font-bold text-xs uppercase flex items-center transition">
                <i data-lucide="arrow-left" class="w-4 h-4 mr-2"></i> Back
            </button>
            <div class="flex space-x-3">
                ${isLocalEnvironment()
                    ? `<button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-[10px] font-black uppercase hover:bg-gray-200 transition">Registration</button>`
                    : `<button disabled title="Registration is only available on the local classroom PC." class="bg-gray-100 text-gray-300 px-8 py-4 rounded-2xl text-[10px] font-black uppercase cursor-not-allowed opacity-40 flex items-center space-x-2"><span>Registration</span></button>`}
                ${isLocalEnvironment()
                    ? (hasStudents
                        ? `<button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 hover:bg-gray-800 transition"><i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span></button>`
                        : `<button disabled title="Register at least one student before scanning." class="bg-gray-200 text-gray-400 px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 cursor-not-allowed opacity-60"><i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span></button>`)
                    : `<button disabled title="Camera is only available on the local classroom PC." class="bg-gray-200 text-gray-300 px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 cursor-not-allowed opacity-40"><i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span></button>`}
            </div>
        </div>
        <h1 class="text-4xl font-black text-gray-900 tracking-tighter uppercase">${cls.subject || class_code}</h1>
        <p class="text-gray-400 font-bold text-sm uppercase tracking-widest mt-1">${cls.section || ''} • ${cls.course_code || ''}</p>
        ${!isLocalEnvironment() ? `
        <div class="mt-4 flex items-start space-x-3 bg-amber-50 border border-amber-200 rounded-2xl px-5 py-3">
            <svg class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 110 20A10 10 0 0112 2z"/></svg>
            <div>
                <p class="text-[11px] font-black text-amber-700 uppercase tracking-widest">Online View Only</p>
                <p class="text-[10px] text-amber-600 mt-0.5">Registration and Camera are only available on the local classroom PC at 127.0.0.1:5000. Student records and attendance history are visible here.</p>
            </div>
        </div>` : ''}

        <!-- Status Filters -->
        <div class="flex gap-2 mt-6 mb-3">
            ${['All','Enrolled','Unenrolled','Dropped'].map(f => `
                <button onclick="applyStudentFilter('${f}')"
                    class="px-4 py-2 text-[10px] font-black border rounded-xl transition ${f === currentStatusFilter ? 'bg-[#D32F2F] text-white border-[#D32F2F]' : 'bg-white text-gray-400 border-gray-200 hover:border-red-300'}">
                    ${f.toUpperCase()}
                </button>`).join('')}
        </div>

        <!-- Student Search -->
        <div class="relative mb-4">
            <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>
            <input type="text"
                   oninput="studentSearchVal = this.value; applyStudentSearch();"
                   value="${studentSearchVal.replace(/"/g, '&quot;')}"
                   placeholder="Search student by name or SR code..."
                   class="w-full bg-gray-50 border-none rounded-2xl py-3 pl-12 pr-4 text-sm font-bold outline-none ring-1 ring-gray-100 focus:ring-red-200 transition">
        </div>

        <div class="bg-white p-6 rounded-[2rem] border border-gray-100 shadow-sm">
            <h3 class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4">Class List</h3>
            <div id="studentListArea" class="space-y-4">
                ${filtered.length === 0 && students.length === 0 ? `
                    <div class="text-center py-20 border-2 border-dashed border-gray-100 rounded-[2rem]">
                        <p class="text-gray-300 font-bold uppercase text-[10px]">No students yet.</p>
                        <p class="text-gray-300 text-[9px] mt-1">Click <b>Registration</b> to add students.</p>
                    </div>` :
                filtered.length === 0 ? `
                    <p class="text-center text-gray-300 font-bold py-4 text-xs">No students under this filter.</p>` :
                filtered.map((s, idx) => `
                    <div class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                        <div class="flex items-center space-x-4">
                            <div class="w-10 h-10 bg-white rounded-xl flex items-center justify-center ${(s.status||'Enrolled') === 'Enrolled' ? 'text-green-500' : 'text-gray-300'} shadow-sm">
                                <i data-lucide="user" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <p class="text-sm font-black ${(s.status||'Enrolled') !== 'Enrolled' ? 'text-gray-400 line-through' : 'text-gray-900'}">${s.name}</p>
                                <p class="text-[9px] text-gray-400 font-bold uppercase">${s.sr_code || ''} • <span class="${(s.status||'Enrolled') === 'Enrolled' ? 'text-green-500' : 'text-red-400'}">${s.status || 'Enrolled'}</span></p>
                            </div>
                        </div>
                        <div class="flex items-center space-x-3">
                            <select onchange="updateStudentStatus(${s.id}, this.value)"
                                class="text-[10px] font-black uppercase bg-white border border-gray-100 rounded-lg p-2 focus:outline-none focus:ring-1 focus:ring-red-200">
                                <option value="Enrolled"   ${(s.status||'Enrolled') === 'Enrolled'   ? 'selected' : ''}>Enrolled</option>
                                <option value="Unenrolled" ${(s.status||'Enrolled') === 'Unenrolled' ? 'selected' : ''}>Unenrolled</option>
                                <option value="Dropped"    ${(s.status||'Enrolled') === 'Dropped'    ? 'selected' : ''}>Dropped</option>
                            </select>
                            <button onclick="sendAttendanceEmail(${s.id}, '${encodeURIComponent(s.name)}', '${encodeURIComponent(s.email||'')}', '${encodeURIComponent(currentOpenedFolder)}')"
                                class="p-2 bg-white text-gray-500 hover:text-[#D32F2F] rounded-lg border border-gray-100 shadow-sm transition flex items-center justify-center"
                                title="Email student">
                                <i data-lucide="mail" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>`).join('')}
            </div>
        </div>`;

    // Cache students for filter re-renders
    window._cachedStudents = students;
    lucide.createIcons();
}

function applyStudentFilter(filter) {
    currentStatusFilter = filter;
    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};
    renderFolderView(cls, currentOpenedFolder, window._cachedStudents || []);
}

function applyStudentSearch() {
    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};
    renderFolderView(cls, currentOpenedFolder, window._cachedStudents || []);
}

async function updateStudentStatus(studentId, newStatus) {
    try {
        await authFetch(`/api/edit_student/${studentId}`, {
            method: 'POST',
            body: new URLSearchParams({ status: newStatus })
        });
        // Patch local cache instantly — no re-fetch needed
        if (window._cachedStudents) {
            const s = window._cachedStudents.find(s => s.id === studentId);
            if (s) s.status = newStatus;
        }
        const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};
        renderFolderView(cls, currentOpenedFolder, window._cachedStudents || []);
    } catch(e) {
        console.error('Failed to update status:', e);
        showToast('Failed to update student status.', 'error');
    }
}

async function sendAttendanceEmail(studentId, encodedName, encodedEmail, encodedClassCode) {
    const studentName  = decodeURIComponent(encodedName);
    const studentEmail = decodeURIComponent(encodedEmail);
    const classCode    = decodeURIComponent(encodedClassCode);

    if (!studentEmail || !studentEmail.includes('@')) {
        showToast('No valid email address for this student.', 'error');
        return;
    }

    // ── Instructor info ───────────────────────────────────────────────────────
    const session         = JSON.parse(localStorage.getItem('active_session') || '{}');
    const instructorEmail = session.email || '';
    const instructorName  = instructorEmail.split('@')[0]
        .replace(/[._]/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());

    // ── Class info ────────────────────────────────────────────────────────────
    const cls         = classFolders.find(f => f.id === classCode) || {};
    const subjectName = cls.subject || classCode;

    showToast('Fetching attendance data…', 'success');

    // ── Tally attendance across all sessions ──────────────────────────────────
    let present = 0, late = 0, absent = 0, totalSessions = 0;
    try {
        const sessRes  = await authFetch(`/api/sessions/${classCode}`);
        const sessions = await sessRes.json();
        totalSessions  = sessions.length;

        for (const sess of sessions) {
            const sp   = sess.session_time
                ? `?session_time=${encodeURIComponent(sess.session_time)}` : '';
            const aRes = await authFetch(`/api/attendance/${classCode}/${sess.date}${sp}`);
            const recs = await aRes.json();
            const mine = recs.find(r =>
                r.name.trim().toLowerCase() === studentName.trim().toLowerCase()
            );
            if (mine) {
                if      (mine.status === 'Present') present++;
                else if (mine.status === 'Late')    late++;
                else                                absent++;
            } else {
                absent++;   // session exists but student not recorded
            }
        }
    } catch(e) {
        showToast('Could not fetch attendance data.', 'error');
        return;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    const ordinal = n => {
        const s = ['th','st','nd','rd'], v = n % 100;
        return n + (s[(v-20)%10] || s[v] || s[0]);
    };
    const todayStr = new Date().toLocaleDateString('en-US', {
        month: 'long', day: 'numeric', year: 'numeric'
    });

    // ── fixing part of emailing  ────────────────────────────────────────────────────────

    
    const emailSubject =
        `Attendance Update – ${subjectName}, as of the ${ordinal(totalSessions)} Day of the Semester`;

        // ── HTML email body (bold + colored, matches image 1 format) ─────────────
    const htmlBody = `
<div style="font-family:Arial,sans-serif;font-size:15px;color:#222;max-width:620px;line-height:1.7;">
    <p>Hi <b>${studentName},</b></p>

    <p>This is an update regarding your attendance in <b>${subjectName}</b>, handled by
    <b>${instructorName}</b>. As of <b>${todayStr}</b> — the
    <b>${ordinal(totalSessions)} day</b> of this semester — here is your attendance record:</p>

    <ul style="list-style:disc;padding-left:24px;margin:12px 0;">
        <li><b style="color:green;">Presents</b> : <b>${present}</b></li>
        <li><b style="color:#b8860b;">Lates</b>&nbsp;&nbsp;&nbsp;: <b>${late}</b></li>
        <li><b style="color:red;">Absences</b> : <b>${absent}</b></li>
    </ul>

    <p>Please review these details and inform me if you believe there are discrepancies.
    Maintaining consistent attendance is important for keeping up with the course requirements,
    so make sure you continue to monitor your status.</p>

    <p>If you have questions or need clarification, feel free to reach out.</p>

    <p><b>Best regards,</b><br>${instructorName}<br>
    <span style="color:#888;font-size:13px;">${instructorEmail}</span></p>
</div>`;

    // Plain-text fallback
    const plainBody =

`Hi ${studentName},

This is an update regarding your attendance in ${subjectName}, handled by ${instructorName}. As of ${todayStr} — the ${ordinal(totalSessions)} day of this semester — here is your attendance record:

  • Presents  : ${present}
  • Lates     : ${late}
  • Absences  : ${absent}

Please review these details and inform me if you believe there are discrepancies. Maintaining consistent attendance is important for keeping up with the course requirements, so make sure you continue to monitor your status.

If you have questions or need clarification, feel free to reach out.

Best regards,
${instructorName}`;

    // ── Try backend auto-send first ───────────────────────────────────────────
    try {
        const sendRes = await authFetch('/api/send_email', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to:      studentEmail,
                subject: emailSubject,
                html:    htmlBody,
                plain:   plainBody
            })
        });
        const sendData = await sendRes.json();

        if (sendRes.ok) {
            showToast(`Email sent to ${studentName} successfully!`, 'success');
            return;
        }

        // SMTP not configured — fall back to Gmail compose
        if (sendRes.status === 503) {
            console.warn('SMTP not configured, falling back to Gmail compose.');
        } else {
            showToast(`Send failed: ${sendData.error}`, 'error');
            return;
        }
    } catch(e) {
        console.warn('Backend send failed, falling back to Gmail compose:', e);
    }


    // ── Fallback: open Gmail compose pre-filled ───────────────────────────────

    const gmailUrl = 'https://mail.google.com/mail/?view=cm&fs=1'
        + '&to='   + encodeURIComponent(studentEmail)
        + '&su='   + encodeURIComponent(emailSubject)
        + '&body=' + encodeURIComponent(plainBody);

    window.open(gmailUrl, '_blank');
}


// ── SCHEDULE ──────────────────────────────────────────────────────────────────

async function loadSchedules() {
    try {
        const res = await authFetch('/api/schedules');
        schedules = await res.json();
    } catch {
        schedules = [];
    }
}

function renderDayFilters() {
    const days      = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
    const container = document.getElementById('day-filters');
    if (!container) return;

    container.innerHTML = days.map(d => `
        <button onclick="selectedDay='${d}'; renderDayFilters()"
            style="touch-action:manipulation;-webkit-tap-highlight-color:transparent;"
            class="w-full py-2 text-[9px] font-black border rounded-xl transition cursor-pointer select-none ${d === selectedDay ? 'bg-[#D32F2F] text-white border-[#D32F2F]' : 'bg-white text-gray-400 border-gray-200 active:bg-red-50'}">${d}</button>
    `).join('');

    const filtered = schedules.filter(s => s.day === selectedDay);
    document.getElementById('schedule-list').innerHTML = filtered.length ? filtered.map(s => `
        <div class="bg-white p-5 rounded-3xl border border-gray-50 shadow-sm relative group hover:border-red-50 transition-all">
            <div class="flex justify-between items-start mb-1">
                <h4 class="font-bold text-gray-900 text-sm">${s.subject}</h4>
                <div class="flex space-x-1 opacity-0 group-hover:opacity-100 transition">
                    <button onclick="editSchedule(${s.id})" class="text-gray-400 hover:text-blue-500"><i data-lucide="edit-3" class="w-3 h-3"></i></button>
                    <button onclick="confirmAction('deleteSubject', ${s.id})" class="text-gray-400 hover:text-red-500"><i data-lucide="trash-2" class="w-3 h-3"></i></button>
                </div>
            </div>
            <p class="text-[9px] text-gray-400 font-bold uppercase tracking-widest">RM ${s.room} • <span class="text-[#D32F2F]">${s.time}</span></p>
        </div>`).join('') : '<p class="text-center text-[10px] text-gray-300 py-10 font-bold">Free Schedule</p>';
    lucide.createIcons();
}

async function saveSubject() {
    const payload = {
        class_code:  currentOpenedFolder || null,
        subject:     document.getElementById('modalSubName').value,
        day:         document.getElementById('modalDaySelect').value,
        room:        document.getElementById('modalRoom').value,
        time:        document.getElementById('modalTimeFrom').value + ' - ' + document.getElementById('modalTimeTo').value,
        old_subject: _editingSchedOldSubject || '',
    };
    if (editSchedId > -1) {
        await authFetch(`/api/schedules/${editSchedId}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } else {
        await authFetch('/api/schedules', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }
    _editingSchedOldSubject = '';
    selectedDay = payload.day;
    await loadSchedules();
    renderDayFilters();
    closeTaskModal();
}

function editSchedule(id) {
    const s = schedules.find(item => item.id === id);
    if (!s) return;
    editSchedId = s.id;
    _editingSchedOldSubject = s.subject;
    document.getElementById('modalSubName').value   = s.subject;
    document.getElementById('modalRoom').value      = s.room;
    document.getElementById('taskModalTitle').textContent = 'Edit Schedule';
    const daySelect = document.getElementById('modalDaySelect');
    Array.from(daySelect.options).forEach(opt => { opt.selected = opt.value === s.day; });
    const timeParts = (s.time || '').split(' - ');
    if (timeParts.length === 2) {
        Array.from(document.getElementById('modalTimeFrom').options).forEach(opt => { opt.selected = opt.value === timeParts[0].trim(); });
        Array.from(document.getElementById('modalTimeTo').options).forEach(opt =>   { opt.selected = opt.value === timeParts[1].trim(); });
    }
    document.getElementById('taskModal').classList.remove('hidden');
}

// ── FOLDER MODAL (Create/Edit Class) ─────────────────────────────────────────

async function saveFolderModal() {
    // Subject comes from the hidden field populated by autoFillClassModal
    // Falls back to select value if no autofill happened
    const subjectNameEl = document.getElementById('modalSubjectName');
    const subject = (subjectNameEl && subjectNameEl.value)
                    ? subjectNameEl.value
                    : document.getElementById('modalSubject').options[
                        document.getElementById('modalSubject').selectedIndex
                      ]?.dataset?.subject
                      || document.getElementById('modalSubject').value;
    const section = document.getElementById('modalSection').value;
    const year    = document.getElementById('modalYear').value;

    // class id includes instructor email prefix to ensure uniqueness across instructors
    const session    = JSON.parse(localStorage.getItem('active_session') || '{}');
    const prefix     = (session.email || 'INS').split('@')[0].toUpperCase().substring(0, 6);
    const class_code = `${prefix}-${subject}-${section}-${year}`.replace(/\s+/g, '-').toUpperCase();

    if (editIdx > -1) {
        // Edit existing class
        const existing = classFolders[editIdx];
        await fetch(`/api/edit_class/${existing.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_code: year, subject: subject, section: section })
        });
    } else {
        // Create new class
        await authFetch('/api/create_class', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: class_code, course_code: year, subject: subject, section: section })
        });
    }

    editIdx = -1;
    showPage('classes');
    closeClassModal();
}

function editFolder(class_code) {
    const f = classFolders.find(f => f.id === class_code);
    if (!f) return;
    editIdx = classFolders.indexOf(f);
    document.getElementById('modalSubject').value = f.subject;
    document.getElementById('modalSection').value = f.section;
    document.getElementById('modalYear').value    = f.course_code;
    document.getElementById('classModal').classList.remove('hidden');
}

// ── STUDENT REGISTRATION ──────────────────────────────────────────────────────

async function submitStudentForm(formEl) {
    const formData = new FormData(formEl);
    if (!formData.get('class_code')) formData.set('class_code', currentOpenedFolder);
    const name=( formData.get('name')||'').trim(), sr=(formData.get('sr_code')||'').trim(),
          phone=(formData.get('number')||'').trim(), email=(formData.get('email')||'').trim(),
          photo=formData.get('photo'), sig=formData.get('signature');
    const errors=[];
    if(!name) errors.push('Full name is required.');
    if(!sr)   errors.push('SR Code is required.');
    if(!email||!email.includes('@')) errors.push('A valid email address is required.');
    const digits=phone.replace(/[\s\-]/g,'');
    if(!phone) errors.push('Contact number is required.');
    else if(!/^0\d{10}$/.test(digits)) errors.push('Contact number must be 11 digits starting with 0 (e.g. 09994408409).');
    if(!photo||photo.size===0) errors.push('Student photo (ID picture) is required for face recognition.');
    else if(!['image/jpeg','image/jpg','image/png'].includes(photo.type)) errors.push('Photo must be JPG or PNG.');
    if(!sig||sig.size===0) errors.push('E-Signature image is required.');
    else if(!['image/jpeg','image/jpg','image/png'].includes(sig.type)) errors.push('Signature must be JPG or PNG.');
    if(errors.length>0){showRegError(errors);return;}
    try {
        const session=JSON.parse(localStorage.getItem('active_session')||'{}');
        const res=await fetch('/api/add_student',{method:'POST',body:formData,headers:{'X-Instructor-Email':session.email||''}});
        const data=await res.json();
        if(!res.ok){showRegError([data.error||'Failed to save student.']);return;}
        closeRegModal(); openFolderView(currentOpenedFolder);
    } catch(e){showRegError(['Server error: '+e.message]);}
}
function showRegError(errors){
    const old=document.getElementById('regErrorBox'); if(old) old.remove();
    const box=document.createElement('div'); box.id='regErrorBox';
    box.style.cssText='background:#FFF5F5;border:1px solid #FCA5A5;border-radius:12px;padding:12px 16px;margin-bottom:16px;font-size:12px;color:#B91C1C;';
    box.innerHTML=`<p style="font-weight:800;margin:0 0 6px">Please fix the following:</p><ul style="margin:0;padding-left:16px;">${errors.map(e=>`<li style="margin-bottom:3px">${e}</li>`).join('')}</ul>`;
    const form=document.getElementById('studentRegForm');
    if(form){const first=form.querySelector('input,select');if(first)form.insertBefore(box,first);else form.prepend(box);box.scrollIntoView({behavior:'smooth',block:'center'});}
}

// ── CAMERA ───────────────────────────────────────────────────────────────────
// Attendance windows (minutes after camera opens):
//   0 – PRESENT_WINDOW  → Present
//   PRESENT_WINDOW – LATE_WINDOW → Late
//   > LATE_WINDOW OR never scanned → Absent

// Grace periods read dynamically from localStorage (synced from DB on profile load)
function getPresentWindow() {
    return parseInt((JSON.parse(localStorage.getItem('mail_config') || '{}')).presentGrace) || 15;
}
function getLateWindow() {
    return parseInt((JSON.parse(localStorage.getItem('mail_config') || '{}')).lateGrace) || 30;
}

let _pollInterval    = null;
let _cameraOpenTime  = null;   // unix ms when camera opened
let _dismissTimer    = null;   // auto-close at class end
let _scannedStudents = {};     // { normalizedName: { displayName, status, time } }
let _customSchedule  = null;   // set when instructor picks make-up schedule

// Normalize name: "Kelvin_Lloyd_Africa" → "Kelvin Lloyd Africa"
function normalizeName(n) { return n.replace(/_/g, ' ').trim(); }

function getStatusForScanTime(firstSeenUnix) {
    if (!_cameraOpenTime) return 'Present';
    const mins = (firstSeenUnix * 1000 - _cameraOpenTime) / 60000;
    if (mins <= getPresentWindow()) return 'Present';
    if (mins <= getLateWindow())    return 'Late';
    return 'Absent';
}

// ── SCHEDULE CHECK MODAL ─────────────────────────────────────────────────────

function openCamera() {
    if (!currentOpenedFolder) return;

    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};

    // Find the schedule linked to this class subject
    const classSchedule = schedules.find(s =>
        s.subject && cls.subject &&
        s.subject.trim().toLowerCase() === cls.subject.trim().toLowerCase()
    );

    if (!classSchedule) {
        // No schedule set — go straight to make-up modal
        showMakeupScheduleModal(cls, null, () => startCameraSession(cls, _customSchedule));
        return;
    }

    // Check if today's day matches the schedule day
    const days      = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
    const todayDay  = days[new Date().getDay()];
    const schedDay  = classSchedule.day;

    // Check if current time is within schedule window (+30 min buffer)
    const now        = new Date();
    const timeParts  = (classSchedule.time || '').split(' - ');
    let withinTime   = false;
    if (timeParts.length === 2) {
        const start = parseTimeStr(timeParts[0]);
        const end   = parseTimeStr(timeParts[1]);
        if (start && end) {
            const buffer = 30 * 60000;
            withinTime   = now >= new Date(start.getTime() - buffer) && now <= new Date(end.getTime() + buffer);
        }
    }

    const dayMatch  = todayDay === schedDay;
    const onSchedule = dayMatch && withinTime;

    if (onSchedule) {
        // All good — open directly
        _customSchedule = null;
        startCameraSession(cls, classSchedule);
    } else {
        // Wrong day or time — show warning
        showScheduleWarningModal(cls, classSchedule, todayDay);
    }
}

function showScheduleWarningModal(cls, classSchedule, todayDay) {
    // Remove existing modal if any
    const existing = document.getElementById('scheduleWarningModal');
    if (existing) existing.remove();

    window._warningCls      = cls;
    window._warningSchedule = classSchedule;

    const modal = document.createElement('div');
    modal.id = 'scheduleWarningModal';
    modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-md z-[300] flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-[2rem] w-full max-w-md p-8 shadow-2xl">
            <div class="flex items-center space-x-3 mb-4">
                <div class="w-12 h-12 bg-red-100 rounded-2xl flex items-center justify-center text-[#D32F2F]">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                    </svg>
                </div>
                <div>
                    <h2 class="text-xl font-black text-gray-900">Wrong Schedule!</h2>
                    <p class="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Schedule mismatch detected</p>
                </div>
            </div>
            <div class="bg-red-50 rounded-2xl p-4 mb-6 text-sm">
                <p class="font-black text-[#D32F2F] mb-1">${cls.subject || ''} — ${cls.section || ''}</p>
                <p class="text-gray-600 text-xs">Scheduled: <b>${classSchedule.day}</b> | <b>${classSchedule.time}</b> | Room <b>${classSchedule.room || 'N/A'}</b></p>
                <p class="text-gray-600 text-xs mt-1">Today is: <b>${todayDay}</b> | Current time: <b>${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</b></p>
            </div>
            <p class="text-sm text-gray-500 mb-6">This class is not currently scheduled. Do you want to set a <b>make-up / customized schedule</b> and continue, or cancel?</p>
            <div class="flex space-x-3">
                <button onclick="document.getElementById('scheduleWarningModal').remove()"
                    class="flex-1 py-4 text-gray-400 font-bold rounded-xl border border-gray-100 hover:bg-gray-50 transition">
                    Cancel
                </button>
                <button onclick="_onMakeupConfirmed()"
                    class="flex-1 py-3 bg-[#D32F2F] text-white font-bold rounded-xl shadow-lg hover:bg-[#B71C1C] transition text-xs leading-tight">
                    Set Make-Up<br>Schedule
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);
}

function _onMakeupConfirmed() {
    const existing = document.getElementById('scheduleWarningModal');
    if (existing) existing.remove();
    const cls      = window._warningCls      || {};
    const schedule = window._warningSchedule || null;
    showMakeupScheduleModal(cls, schedule, () => startCameraSession(cls, _customSchedule));
}



function showMakeupScheduleModal(cls, originalSchedule, onConfirm) {
    const existing = document.getElementById('makeupModal');
    if (existing) existing.remove();

    // Today's day — fixed, not selectable
    const days    = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
    const todayDay = days[new Date().getDay()];



    // Build time options
    let timeOpts = '';
    for (let i = 7; i <= 21; i++) {
        const h  = i > 12 ? i - 12 : i;
        const ap = i >= 12 ? 'PM' : 'AM';
        timeOpts += `<option value="${h}:00 ${ap}">${h}:00 ${ap}</option>`;
        timeOpts += `<option value="${h}:30 ${ap}">${h}:30 ${ap}</option>`;
    }

    const modal = document.createElement('div');
    modal.id =      'makeupModal';
    modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-md z-[300] flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-[2rem] w-full max-w-md p-8 shadow-2xl">
            <h2 class="text-xl font-black text-[#D32F2F] mb-1">Make-Up / Custom Schedule</h2>
            <p class="text-xs text-gray-400 font-bold mb-6 uppercase tracking-wider">${cls.subject || ''} — ${cls.section || ''}</p>
            <div class="space-y-4">
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 block">Day</label>
                    <!-- Day is locked to today — cannot be changed -->
                    <div class="reg-input bg-gray-100 text-gray-700 font-black cursor-not-allowed"
                         style="pointer-events:none;">${todayDay} &nbsp;<span class="text-[9px] text-gray-400 font-normal">(Today — auto-set)</span>
                    </div>

                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 block">Room</label>
                    <input id="mkRoom" type="text" placeholder="Room (e.g. VMB 401)"
                        value="${originalSchedule ? originalSchedule.room || '' : ''}" class="reg-input">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 block">Start Time</label>
                        <select id="mkFrom" class="reg-input">${timeOpts}</select>
                    </div>
                    <div>
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 block">End Time</label>
                        <select id="mkTo" class="reg-input">${timeOpts}</select>
                    </div>
                </div>
            </div>
            <div class="flex space-x-3 mt-8">
                <button onclick="document.getElementById('makeupModal').remove()"
                    class="flex-1 py-4 text-gray-400 font-bold rounded-xl border border-gray-100 hover:bg-gray-50 transition">
                    Cancel
                </button>
                <button onclick="confirmMakeupSchedule('${todayDay}')"
                    class="flex-1 py-4 bg-[#D32F2F] text-white font-bold rounded-xl shadow-lg hover:bg-[#B71C1C] transition">
                    Start Scanning
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);

    // Store callback for when confirmed
    window._makeupOnConfirm = onConfirm;
}

function confirmMakeupSchedule(day) {
    const room = document.getElementById('mkRoom').value;
    const from = document.getElementById('mkFrom').value;
    const to   = document.getElementById('mkTo').value;

    _customSchedule = { day, room, time: `${from} - ${to}`, isMakeup: true };

    document.getElementById('makeupModal').remove();

    if (window._makeupOnConfirm) {
        window._makeupOnConfirm();
        window._makeupOnConfirm = null;
    }
}

// ── CORE CAMERA SESSION ───────────────────────────────────────────────────────

// ── CAMERA SOURCE HELPERS ────────────────────────────────────────────────────

// Cache of rooms loaded from API: [{id, room_name, rtsp_url}, ...]
let _cachedRooms = [];

async function loadCameraRooms() {
    try {
        const res   = await authFetch('/api/rooms');
        const rooms = await res.json();
        _cachedRooms = rooms;

        const roomSel  = document.getElementById('rtspRoomSelect');
        const rtspInput = document.getElementById('rtspUrlInput');
        if (!roomSel) return;

        if (rooms.length === 0) {
            // No rooms configured by admin → fall back to manual RTSP input
            roomSel.classList.add('hidden');
            if (document.getElementById('cameraSourceSelect')?.value === 'rtsp') {
                rtspInput?.classList.remove('hidden');
            }
            roomSel.innerHTML = '<option value="">No rooms configured</option>';
        } else {
            // Populate room dropdown with friendly names
            roomSel.innerHTML = rooms.map(r =>
                `<option value="${r.id}">📡 ${r.room_name}</option>`
            ).join('');
            // Show room dropdown if RTSP is already selected
            if (document.getElementById('cameraSourceSelect')?.value === 'rtsp') {
                roomSel.classList.remove('hidden');
                rtspInput?.classList.add('hidden');
            }
        }
    } catch {
        // Network error — silently fall back to manual input
        _cachedRooms = [];
    }
}

function getSelectedCameraSource() {
    const sel = document.getElementById('cameraSourceSelect');
    if (!sel) return '0';
    const val = sel.value;

    if (val === 'rtsp') {
        // Try room dropdown first
        const roomSel = document.getElementById('rtspRoomSelect');
        const roomId  = roomSel ? parseInt(roomSel.value) : NaN;
        if (!isNaN(roomId) && _cachedRooms.length > 0) {
            const room = _cachedRooms.find(r => r.id === roomId);
            if (room) return room.rtsp_url;
        }
        // Fall back to manual text input
        const url = (document.getElementById('rtspUrlInput')?.value || '').trim();
        return url || 'rtsp://admin:Sentinel_04@192.168.137.166:554/Streaming/Channels/101';
    }
    return val; // "0" or "1"
}

// Show/hide the correct RTSP control when source dropdown changes
document.addEventListener('change', function(e) {
    if (e.target && e.target.id === 'cameraSourceSelect') {
        const isRtsp   = e.target.value === 'rtsp';
        const roomSel  = document.getElementById('rtspRoomSelect');
        const rtspInput = document.getElementById('rtspUrlInput');

        if (isRtsp) {
            if (_cachedRooms.length > 0) {
                roomSel?.classList.remove('hidden');
                rtspInput?.classList.add('hidden');
            } else {
                roomSel?.classList.add('hidden');
                rtspInput?.classList.remove('hidden');
            }
        } else {
            roomSel?.classList.add('hidden');
            rtspInput?.classList.add('hidden');
        }
    }
});

async function refreshCameraFeed() {
    const dummyFeed   = document.getElementById('dummyFeed');
    const loadingEl   = document.getElementById('cameraLoading');
    if (!dummyFeed) return;

    // Show a brief spinner
    dummyFeed.classList.add('hidden');
    loadingEl.classList.remove('hidden');
    loadingEl.innerHTML = `
        <div class="w-16 h-16 border-4 border-t-[#D32F2F] border-gray-800 rounded-full animate-spin mb-4"></div>
        <h3 class="text-white font-bold text-base mb-1">Restarting Camera...</h3>
        <p class="text-gray-400 text-xs">Please wait a moment.</p>`;

    try {
        // Stop existing camera on backend then restart with selected source
        await authFetch('/api/stop_camera', { method: 'POST' });
        _camera_started_flag = false;
    } catch {}

    const source = getSelectedCameraSource();
    // Get current class info so session is preserved on refresh
    const _refreshCls = classFolders.find(f => f.id === currentOpenedFolder) || {};
    try {
        await authFetch('/api/start_camera', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source,
                class_code: _refreshCls.id       || currentOpenedFolder || '',
                section:    _refreshCls.section   || '',
                subject:    _refreshCls.subject   || ''
            })
        });
    } catch (e) {
        loadingEl.innerHTML = `
            <div class="flex flex-col items-center justify-center text-center px-8">
                <h3 class="text-white font-bold text-lg mb-2">Camera Failed to Start</h3>
                <p class="text-gray-400 text-xs">Check camera source and try again.</p>
            </div>`;
        return;
    }

    // Reload the video feed image with a cache-busting timestamp
    setTimeout(() => {
        loadingEl.classList.add('hidden');
        dummyFeed.classList.remove('hidden');
        dummyFeed.innerHTML = '';
        const img = document.createElement('img');
        img.style.cssText = 'width:100%; height:100%; object-fit:cover;';
        img.src = `/video_feed?t=${Date.now()}`;
        img.onerror = () => {
            dummyFeed.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-center p-8">
                    <h3 class="text-white font-bold text-lg mb-2">No Video Feed</h3>
                    <p class="text-gray-400 text-xs">Could not connect to camera stream.</p>
                </div>`;
        };
        dummyFeed.appendChild(img);
    }, 1500);
}

let _camera_started_flag = false;

async function startCameraSession(cls, activeSchedule) {
    _scannedStudents     = {};
    _cameraOpenTime      = Date.now();
    _camera_started_flag = false;

    document.getElementById('recognizedList').innerHTML = '';
    document.getElementById('cameraModal').classList.remove('hidden');
    document.getElementById('cameraLoading').classList.remove('hidden');
    document.getElementById('cameraLoading').innerHTML = `
        <div class="w-20 h-20 border-4 border-t-[#D32F2F] border-gray-800 rounded-full animate-spin mb-6"></div>
        <h3 class="text-white font-bold text-lg mb-2">Initializing Camera...</h3>`;
    document.getElementById('dummyFeed').classList.add('hidden');
    updateDetectionHeader();

    // Load room names from admin config into the RTSP dropdown
    await loadCameraRooms();

    // Get selected camera source from dropdown
    const source = getSelectedCameraSource();

    // Start camera on backend with class session info for cloud sync
    try {
        await authFetch('/api/start_camera', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source,
                class_code: cls.id      || currentOpenedFolder || '',
                section:    cls.section || '',
                subject:    cls.subject || ''
            })
        });
        _camera_started_flag = true;
    } catch (e) {
        document.getElementById('cameraLoading').innerHTML = `
            <div class="flex flex-col items-center justify-center text-center px-8">
                <h3 class="text-white font-bold text-lg mb-2">Camera Failed to Start</h3>
                <p class="text-gray-400 text-xs">Check that your camera is connected and not in use.</p>
                <button onclick="refreshCameraFeed()"
                    class="mt-4 px-5 py-2 bg-[#D32F2F] text-white rounded-xl font-bold text-xs hover:bg-[#B71C1C] transition">
                    Try Again
                </button>
            </div>`;
        return;
    }

    setTimeout(() => {
        document.getElementById('cameraLoading').classList.add('hidden');
        const dummyFeed = document.getElementById('dummyFeed');
        dummyFeed.classList.remove('hidden');
        dummyFeed.innerHTML = '';

        const img = document.createElement('img');
        img.style.cssText = 'width:100%; height:100%; object-fit:cover;';
        img.src = `/video_feed?t=${Date.now()}`;
        img.onerror = () => {
            dummyFeed.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-center p-8">
                    <h3 class="text-white font-bold text-lg mb-2">No Video Feed</h3>
                    <p class="text-gray-400 text-xs">Could not connect to camera stream.</p>
                    <button onclick="refreshCameraFeed()"
                        class="mt-4 px-5 py-2 bg-[#D32F2F] text-white rounded-xl font-bold text-xs hover:bg-[#B71C1C] transition">
                        Retry
                    </button>
                </div>`;
        };
        dummyFeed.appendChild(img);

        // Poll scan log every 2 seconds
        _pollInterval = setInterval(async () => {
            try {
                const res     = await authFetch('/api/scan_log');
                const scanLog = await res.json();

                Object.entries(scanLog).forEach(([rawName, firstSeenUnix]) => {
                    // Normalize: "Kelvin_Lloyd_Africa" → "Kelvin Lloyd Africa"
                    const displayName = normalizeName(rawName);
                    const status      = getStatusForScanTime(firstSeenUnix);
                    const time        = new Date(firstSeenUnix * 1000)
                                          .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    // Use displayName as key so duplicates are avoided
                    _scannedStudents[displayName] = { displayName, status, time, rawName };
                });

                renderAttendancePanel();
                updateDetectionHeader();
            } catch (err) {
                console.warn('[Poll] scan_log error:', err);
            }
        }, 2000);

        // Auto-dismiss at class end time
        if (activeSchedule && activeSchedule.time) {
            const parts = activeSchedule.time.split(' - ');
            if (parts.length === 2) {
                const endTime = parseTimeStr(parts[1].trim());
                if (endTime) {
                    const msUntilEnd = endTime.getTime() - Date.now();
                    if (msUntilEnd > 0) {
                        _dismissTimer = setTimeout(() => closeCamera(true), msUntilEnd);
                    }
                }
            }
        }
    }, 1500);
}

function parseTimeStr(timeStr) {
    try {
        const [time, ampm] = timeStr.trim().split(' ');
        let [h, m] = time.split(':').map(Number);
        if (ampm === 'PM' && h !== 12) h += 12;
        if (ampm === 'AM' && h === 12) h = 0;
        const d = new Date();
        d.setHours(h, m, 0, 0);
        return d;
    } catch { return null; }
}

function renderAttendancePanel() {
    const list = document.getElementById('recognizedList');
    if (!list) return;
    const entries = Object.values(_scannedStudents);
    if (entries.length === 0) {
        list.innerHTML = '<p class="text-[10px] text-gray-400 text-center py-4">No faces detected yet...</p>';
        return;
    }
    const order = { Present: 0, Late: 1, Absent: 2 };
    entries.sort((a, b) => order[a.status] - order[b.status]);
    list.innerHTML = entries.map(e => {
        const color = e.status === 'Present' ? 'text-green-500'
                    : e.status === 'Late'    ? 'text-yellow-500' : 'text-red-500';
        const bg    = e.status === 'Present' ? 'bg-green-50'
                    : e.status === 'Late'    ? 'bg-yellow-50'   : 'bg-red-50';
        return `
            <div class="flex justify-between items-center ${bg} px-3 py-3 rounded-xl mb-2">
                <div>
                    <p class="text-sm font-black text-gray-900">${e.displayName}</p>
                    <p class="text-[9px] font-bold text-gray-400">${e.time}</p>
                </div>
                <span class="text-[10px] font-black ${color} uppercase">${e.status}</span>
            </div>`;
    }).join('');
}

function updateDetectionHeader() {
    const vals    = Object.values(_scannedStudents);
    const present = vals.filter(e => e.status === 'Present').length;
    const late    = vals.filter(e => e.status === 'Late').length;
    const el      = document.querySelector('#cameraModal .flex.gap-2.mt-2');
    if (!el) return;
    el.innerHTML = `
        <span class="bg-green-100 text-green-600 text-[9px] font-black px-2 py-1 rounded">PRESENT: ${present}</span>
        <span class="bg-yellow-100 text-yellow-600 text-[9px] font-black px-2 py-1 rounded">LATE: ${late}</span>`;
}

async function closeCamera(autoDismiss = false) {
    if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
    if (_dismissTimer) { clearTimeout(_dismissTimer);  _dismissTimer = null; }

    if (autoDismiss) {
        // Auto-dismiss: save immediately without asking
        await _doSaveAndClose();
        showToast('Class dismissed! Attendance saved automatically.', 'success');
        return;
    }

    // Show confirmation dialog before saving
    const modal    = document.getElementById('customConfirm');
    const descEl   = document.getElementById('confirmDesc');
    const confirmBtn = document.getElementById('confirmBtn');

    // Count how many students were scanned
    const present = recognizer_present_count || 0;
    descEl.innerText = `Save attendance and close the camera?`;

    modal.classList.remove('hidden');
    confirmBtn.onclick = async () => {
        modal.classList.add('hidden');
        await _doSaveAndClose();
        showToast('Attendance saved successfully!', 'success');
    };

    // Update confirm button label
    document.getElementById('confirmBtn').textContent = 'Save & Close';

    // Override the No/Cancel button to close camera WITHOUT saving
    const noBtn = document.querySelector('#customConfirm .flex button:first-child');
    if (noBtn) {
        const origOnclick = noBtn.getAttribute('onclick');
        noBtn.onclick = async () => {
            modal.classList.add('hidden');
            document.getElementById('cameraModal').classList.add('hidden');
            if (noBtn) noBtn.setAttribute('onclick', origOnclick || 'closeConfirm()');
            document.getElementById('confirmBtn').textContent = 'Yes';
            // Stop the camera on the backend so it is fully released
            try { await authFetch('/api/stop_camera', { method: 'POST' }); } catch {}
            _cameraOpenTime  = null;
            _customSchedule  = null;
            _scannedStudents = {};
            showToast('Camera closed. Attendance was NOT saved.', 'error');
        };
    }
}

async function _doSaveAndClose() {
    await saveAttendanceFromCamera();
    document.getElementById('cameraModal').classList.add('hidden');
    _cameraOpenTime  = null;
    _customSchedule  = null;
    _scannedStudents = {};
}

// keep a rough count for the confirm message
let recognizer_present_count = 0;

async function saveAttendanceFromCamera() {
    if (!currentOpenedFolder) return;
    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};

    // Capture session time NOW before any async calls that might clear _cameraOpenTime
    const sessionTime = _cameraOpenTime
        ? new Date(_cameraOpenTime).toTimeString().substring(0, 8)
        : new Date().toTimeString().substring(0, 8);

    try {
        // Stop camera and get final scan log from backend
        const stopRes  = await authFetch('/api/stop_camera', { method: 'POST' });
        const stopData = await stopRes.json();
        const scanLog  = stopData.scan_log || {};   // { rawName: unix_timestamp }

        // Get all registered students
        const allRes  = await authFetch(`/api/students/${currentOpenedFolder}`);
        const allStud = await allRes.json();

        const records = allStud.map(s => {
            // Try matching by normalized name (handles underscore vs space)
            const normalizedStudentName = s.name.trim();
            // Find matching key in scanLog (scanLog keys may have underscores)
            const matchKey = Object.keys(scanLog).find(k =>
                normalizeName(k).toLowerCase() === normalizedStudentName.toLowerCase()
            );

            if (matchKey) {
                const firstSeenUnix = scanLog[matchKey];
                const status        = getStatusForScanTime(firstSeenUnix);
                // Build full timestamp string: "YYYY-MM-DD HH:MM:SS"
                const scannedAt     = new Date(firstSeenUnix * 1000);
                const timestamp     = scannedAt.toTimeString().substring(0, 8);
                return { name: s.name, sr_code: s.sr_code || '', status, timestamp };
            }
            // Not scanned → Absent
            return { name: s.name, sr_code: s.sr_code || '', status: 'Absent', timestamp: '' };
        });

        // Use custom schedule info if makeup class
        const activeSchedule = _customSchedule || schedules.find(s =>
            s.subject && cls.subject &&
            s.subject.trim().toLowerCase() === cls.subject.trim().toLowerCase()
        );

        const saveRes = await authFetch('/api/save_attendance', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                class_code:   currentOpenedFolder,
                section:      cls.section  || '',
                subject:      cls.subject  || '',
                room:         activeSchedule ? activeSchedule.room || '' : '',
                session_time: sessionTime,
                records
            })
        });

        if (!saveRes.ok) {
            const err = await saveRes.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${saveRes.status}`);
        }

        // Update present count for confirm dialog
        recognizer_present_count = records.filter(r => r.status !== 'Absent').length;

    } catch (e) {
        console.error('Save attendance failed:', e);
        showToast('Failed to save attendance.', 'error');
    }
}

function showToast(msg, type = 'success') {
    let toast = document.getElementById('attendanceToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'attendanceToast';
        toast.style.cssText = `position:fixed;bottom:30px;left:50%;transform:translateX(-50%);
            padding:14px 28px;border-radius:12px;font-weight:700;font-size:13px;
            z-index:9999;transition:opacity 0.4s;box-shadow:0 8px 24px rgba(0,0,0,0.15);`;
        document.body.appendChild(toast);
    }
    toast.textContent    = msg;
    toast.style.background = type === 'success' ? '#1B5E20' : '#B71C1C';
    toast.style.color      = 'white';
    toast.style.opacity    = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 3500);
}


// ── CONFIRM DIALOG (unchanged logic, updated backend calls) ───────────────────

async function confirmAction(action, id) {
    // For deleteSubject: check usage FIRST before showing any modal
    if (action === 'deleteSubject') {
        try {
            const uRes = await authFetch(`/api/schedules/${id}/check_usage`);
            const used = await uRes.json();
            if (used.length > 0) {
                // Schedule is in use — show blocking "in use" modal, no delete option
                showScheduleInUseModal();
                return;
            }
        } catch {}
        // Not in use — show normal confirm modal
        const modal = document.getElementById('customConfirm');
        modal.classList.remove('hidden');
        document.getElementById('confirmDesc').innerText = "Proceed with this action?";
        document.getElementById('confirmBtn').onclick = async () => {
            await authFetch(`/api/schedules/${id}`, { method: 'DELETE' });
            await loadSchedules(); renderDayFilters();
            closeConfirm();
        };
        return;
    }

    const modal = document.getElementById('customConfirm');
    modal.classList.remove('hidden');
    document.getElementById('confirmDesc').innerText = "Proceed with this action?";

    document.getElementById('confirmBtn').onclick = async () => {
        if (action === 'deleteFolder') {
            await fetch(`/api/delete_class/${id}`, { method: 'DELETE' });
            showPage('classes');
        } else if (action === 'logout') {
            localStorage.removeItem('active_session');
            window.location.href = "/";
        }
        closeConfirm();
    };
}

function showScheduleInUseModal() {
    const ex = document.getElementById('scheduleInUseModal'); if (ex) ex.remove();
    const modal = document.createElement('div');
    modal.id = 'scheduleInUseModal';
    modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-md z-[300] flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-[2rem] w-full max-w-xs p-8 text-center shadow-2xl">
            <h3 class="font-black text-xl mb-2">The schedule is in use.</h3>
            <p class="text-gray-400 text-sm mb-8">This schedule is currently linked to a class folder and cannot be deleted.</p>
            <button onclick="document.getElementById('scheduleInUseModal').remove()"
                class="w-full py-3 bg-gray-100 text-gray-600 font-bold rounded-xl hover:bg-gray-200 transition">
                Cancel
            </button>
        </div>`;
    document.body.appendChild(modal);
}


function closeConfirm() {
    document.getElementById('customConfirm').classList.add('hidden');
    // Reset confirm button text to default
    const btn = document.getElementById('confirmBtn');
    if (btn) btn.textContent = 'Yes';
}

// ── MODAL HELPERS (unchanged) ─────────────────────────────────────────────────

function openRegModal() {
    // Auto-fill the hidden class_code from the currently open folder
    document.getElementById('reg-class-code').value = currentOpenedFolder;
    // Reset the form fields so old data doesn't show
    document.getElementById('studentRegForm').reset();
    document.getElementById('reg-class-code').value = currentOpenedFolder;
    document.getElementById('regModal').classList.remove('hidden');
}
function closeRegModal()   { document.getElementById('regModal').classList.add('hidden'); }
function closeClassModal() { document.getElementById('classModal').classList.add('hidden'); }
function closeTaskModal()  { editSchedId = -1; document.getElementById('taskModal').classList.add('hidden'); }
function openTaskModal()   { editSchedId = -1; document.getElementById('taskModal').classList.remove('hidden'); }
function openFolderModal() {
    editIdx = -1;
    populateSubjectSuggestions();   // fill the schedule dropdown before showing
    document.getElementById('modalSection').value = '';
    document.getElementById('modalYear').value    = '';
    document.getElementById('classModal').classList.remove('hidden');
}

// ── SIDEBAR TOGGLE (unchanged) ────────────────────────────────────────────────


// ── SUBJECT SUGGESTIONS (from schedules → class folder modal) ─────────────────
function populateSubjectSuggestions() {
    const subjectSelect = document.getElementById('modalSubject');
    if (!subjectSelect) return;

    subjectSelect.innerHTML = '<option value="">Select Suggested Sched</option>';

    schedules.forEach(sched => {
        const option       = document.createElement('option');
        option.value       = sched.id || sched.subject;   // use id for lookup
        option.dataset.subject = sched.subject;
        option.dataset.day     = sched.day || '';
        option.dataset.time    = sched.time || '';
        option.dataset.room    = sched.room || '';
        option.textContent = `${sched.subject} (${sched.day || ''} | ${sched.time || ''})`;
        subjectSelect.appendChild(option);
    });
}

function autoFillClassModal(selectedValue) {
    if (!selectedValue) return;
    const select   = document.getElementById('modalSubject');
    const selected = select.querySelector(`option[value="${selectedValue}"]`);
    if (!selected) return;
    // Store subject name separately so saveFolderModal can read it
    document.getElementById('modalSubjectName').value = selected.dataset.subject || selectedValue;
    console.log("Auto-filled from schedule:", selected.dataset.subject);
}

function toggleMiniSidebar() {
    const sidebar = document.getElementById('navSidebar');
    const labels  = document.querySelectorAll('.nav-label');
    const chevron = document.querySelector('[data-lucide="chevron-left"], [data-lucide="chevron-right"]');

    sidebar.classList.toggle('w-64');
    sidebar.classList.toggle('w-20');
    labels.forEach(label => label.classList.toggle('hidden'));

    if (chevron) {
        chevron.setAttribute('data-lucide',
            sidebar.classList.contains('w-20') ? 'chevron-right' : 'chevron-left');
    }
    lucide.createIcons();
}

async function saveProfileChanges() {
    const nameEl    = document.getElementById('prof-name');
    const numberEl  = document.getElementById('prof-number');
    const photoEl   = document.getElementById('modal-user-photo');
    const updatedName   = nameEl   ? nameEl.value.trim()   : '';
    const updatedNumber = numberEl ? numberEl.value.trim() : '';
    const currentPhoto  = photoEl  ? photoEl.src           : '';

    // Save name + number to DB so PDF uses the real name
    try {
        await authFetch('/api/profile', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ name: updatedName, number: updatedNumber })
        });
    } catch { /* non-blocking */ }

    // Update localStorage session + sidebar display
    const session = JSON.parse(localStorage.getItem('active_session'));
    if (session) {
        session.name       = updatedName;
        session.number     = updatedNumber;
        session.profilePic = currentPhoto;
        localStorage.setItem('active_session', JSON.stringify(session));
        const nameDispEl  = document.getElementById('user-display-name');
        const photoDispEl = document.getElementById('user-display-photo');
        const fullNmDisp  = document.getElementById('modal-user-full-name');
        if (nameDispEl)  nameDispEl.textContent  = updatedName;
        if (photoDispEl && currentPhoto) photoDispEl.src = currentPhoto;
        if (fullNmDisp)  fullNmDisp.textContent  = updatedName;
    }

    // Save mail config + grace periods to DB
    const gmail        = document.getElementById('mail-gmail')?.value    || '';
    const appPass      = document.getElementById('mail-app-pass')?.value || '';
    const presentGrace = parseInt(document.getElementById('time-present')?.value || '15');
    const lateGrace    = parseInt(document.getElementById('time-late')?.value    || '30');

    try {
        await authFetch('/api/mail_config', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ gmail, app_pass: appPass, present_grace: presentGrace, late_grace: lateGrace })
        });
    } catch { /* non-blocking */ }

    // Mirror to localStorage so camera session reads grace periods immediately
    localStorage.setItem('mail_config', JSON.stringify({ gmail, appPass, presentGrace, lateGrace }));
    showSaveModal();
}

function showSaveModal() {
    const modal   = document.getElementById('saveModal');
    const content = document.getElementById('modalContent');
    if (!modal) return;
    modal.classList.remove('hidden');
    setTimeout(() => {
        content.classList.remove('scale-90', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }, 10);
    lucide.createIcons();
}

function closeSaveModal() {
    const modal   = document.getElementById('saveModal');
    const content = document.getElementById('modalContent');
    if (!modal) return;
    content.classList.remove('scale-100', 'opacity-100');
    content.classList.add('scale-90', 'opacity-0');
    setTimeout(() => { modal.classList.add('hidden'); }, 300);
}

function toggleProfileEdit() {
    const editBtn = document.getElementById('profileEditBtn');
    isProfileEditing = !isProfileEditing;
    if (isProfileEditing) {
        editBtn.innerHTML = '<i data-lucide="check" class="w-4 h-4"></i><span>Save Changes</span>';
        editBtn.classList.remove('bg-gray-900');
        editBtn.classList.add('bg-green-600');
    } else {
        saveProfileChanges();
        editBtn.innerHTML = '<i data-lucide="edit-3" class="w-4 h-4"></i><span>Edit Profile</span>';
        editBtn.classList.remove('bg-green-600');
        editBtn.classList.add('bg-gray-900');
    }
    updateProfileFieldsState();
    lucide.createIcons();
}

function updateProfileFieldsState() {
    document.querySelectorAll('.prof-field').forEach(f => f.readOnly = !isProfileEditing);
    document.querySelectorAll('.mail-field').forEach(f => f.readOnly = !isProfileEditing);
    const picOverlay = document.getElementById('profilePicOverlay');
    if (picOverlay) {
        isProfileEditing
            ? picOverlay.classList.remove('hidden')
            : picOverlay.classList.add('hidden');
    }
}

function previewProfilePic(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            const photoEl = document.getElementById('modal-user-photo');
            if (photoEl) photoEl.src = e.target.result;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function saveToStorage() {
    localStorage.setItem('attendace_sched_v3',   JSON.stringify(schedules));
    localStorage.setItem('attendace_classes_v3',  JSON.stringify(classFolders));
    localStorage.setItem('attendace_history_v3',  JSON.stringify(historyFolders));
    localStorage.setItem('attendace_logs_v3',     JSON.stringify(attendanceLogs));
}

// ── DOCUMENT VIEWER (unchanged — now uses real PDF) ───────────────────────────

async function openRealDoc(class_code, date) {
    // Load the session detail and show it in the docViewer panel
    const cls = classFolders.find(f => f.id === class_code) || {};

    try {
        const res     = await authFetch(`/api/attendance/${class_code}/${date}`);
        const records = await res.json();

        // Find matching schedule for header info
        const sched = schedules.find(s =>
            s.subject && cls.subject &&
            s.subject.toLowerCase() === cls.subject.toLowerCase()
        );

        let schedHeaderHtml = '';
        if (sched) {
            schedHeaderHtml = `
                <div class="mb-6 p-4 bg-gray-50 rounded-xl text-xs border border-gray-100">
                    <p class="font-black text-[#D32F2F] uppercase mb-1">Class Schedule Details</p>
                    <div class="grid grid-cols-2 gap-2 text-gray-700 font-bold">
                        <div><span class="text-gray-400">SUBJECT:</span> ${cls.subject || ''}</div>
                        <div><span class="text-gray-400">SECTION:</span> ${cls.section || ''}</div>
                        <div><span class="text-gray-400">ROOM:</span> ${sched.room || 'N/A'}</div>
                        <div><span class="text-gray-400">DAY:</span> ${sched.day || 'N/A'}</div>
                        <div class="col-span-2"><span class="text-gray-400">TIME:</span> ${sched.time || 'N/A'}</div>
                    </div>
                </div>`;
        }

        document.getElementById('docTitle').innerText = `Report: ${date}`;
        document.getElementById('printArea').innerHTML = `
            <div class="max-w-2xl mx-auto bg-white shadow-sm border p-12 min-h-[800px]">
                <h1 class="text-center font-bold text-xl mb-6 underline">ATTENDANCE LOG REPORT</h1>
                ${schedHeaderHtml}
                <table class="w-full text-left text-xs">
                    <thead class="border-b-2 border-black">
                        <tr>
                            <th class="py-2">STUDENT NAME</th>
                            <th class="py-2">TIME IN</th>
                            <th class="py-2">STATUS</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${records.map(s => `
                        <tr>
                            <td class="py-3 font-bold">${s.name}</td>
                            <td class="py-3">${s.timestamp ? s.timestamp.substring(11,16) : '—'}</td>
                            <td class="py-3 font-bold text-xs uppercase
                                ${s.status === 'Present' ? 'text-green-500' :
                                  s.status === 'Late'    ? 'text-yellow-500' : 'text-red-500'}">
                                ${s.status}
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            </div>`;

        document.getElementById('docViewer').classList.remove('hidden');
    } catch(e) {
        alert('Could not load attendance record: ' + e.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const isCloud = window.location.hostname.includes('onrender.com');

    if (isCloud) {
        // Select the buttons you want to disable
        const registerBtn = document.getElementById('register-btn');
        const cameraBtn = document.getElementById('camera-btn');

        // Apply "Grey Look" and Disable
        if (registerBtn) {
            registerBtn.disabled = true;
            registerBtn.style.opacity = "0.5";
            registerBtn.style.cursor = "not-allowed";
            registerBtn.title = "Registration is handled at the Local Station for Biometric Privacy.";
        }

        if (cameraBtn) {
            cameraBtn.disabled = true;
            cameraBtn.style.opacity = "0.5";
            cameraBtn.style.cursor = "not-allowed";
            cameraBtn.title = "Camera access requires a Local Edge connection.";
        }
    }
});


// ════════════════════════════════════════════════════════════════════════════════
// NOTIFICATION SYSTEM
// ════════════════════════════════════════════════════════════════════════════════

const NOTIF_ICONS = {
    approved:          { icon: 'shield-check',  color: 'text-green-500',  bg: 'bg-green-50'  },
    class_created:     { icon: 'folder-plus',   color: 'text-blue-500',   bg: 'bg-blue-50'   },
    attendance_saved:  { icon: 'clipboard-check',color: 'text-[#D32F2F]', bg: 'bg-red-50'    },
    email_sent:        { icon: 'mail-check',    color: 'text-purple-500', bg: 'bg-purple-50' },
    student_registered:{ icon: 'user-plus',     color: 'text-orange-500', bg: 'bg-orange-50' },
    general:           { icon: 'bell',          color: 'text-gray-400',   bg: 'bg-gray-50'   },
};

let _notifPanelOpen   = false;
let _notifPollTimer   = null;
let _lastUnreadCount  = 0;

// ── Public: called by the bell button ────────────────────────────────────────
function toggleNotifPanel() {
    _notifPanelOpen = !_notifPanelOpen;
    const panel = document.getElementById('notifPanel');
    if (!panel) return;
    panel.classList.toggle('hidden', !_notifPanelOpen);
    if (_notifPanelOpen) {
        loadNotifications();
    }
}

// ── Close panel when clicking outside ────────────────────────────────────────
document.addEventListener('click', e => {
    const wrapper = document.getElementById('notifWrapper');
    if (wrapper && !wrapper.contains(e.target) && _notifPanelOpen) {
        _notifPanelOpen = false;
        document.getElementById('notifPanel')?.classList.add('hidden');
    }
});

// ── Fetch notifications from API ─────────────────────────────────────────────
async function loadNotifications() {
    const list = document.getElementById('notifList');
    if (!list) return;

    try {
        const res  = await authFetch('/api/notifications');
        const data = await res.json();
        const { notifications = [], unread = 0 } = data;

        updateBadge(unread);
        renderNotifList(notifications);

    } catch {
        list.innerHTML = `<p class="text-center text-gray-300 text-xs font-bold py-6">Could not load notifications.</p>`;
    }
}

// ── Render the list of notification items ────────────────────────────────────
function renderNotifList(notifications) {
    const list = document.getElementById('notifList');
    if (!list) return;

    if (!notifications.length) {
        list.innerHTML = `
            <div class="flex flex-col items-center justify-center py-8 text-gray-300">
                <svg class="w-10 h-10 mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                </svg>
                <p class="text-xs font-bold">No notifications yet</p>
            </div>`;
        return;
    }

    list.innerHTML = notifications.map(n => {
        const meta    = NOTIF_ICONS[n.type] || NOTIF_ICONS.general;
        const ts      = _fmtNotifTime(n.created_at);
        const unread  = !n.is_read;

        return `
        <div onclick="markNotifRead(${n.id}, this)"
             class="flex items-start gap-3 px-4 py-3 cursor-pointer transition
                    ${unread ? 'bg-red-50/40 hover:bg-red-50' : 'hover:bg-gray-50'}">
            <!-- Icon -->
            <div class="w-9 h-9 rounded-xl ${meta.bg} flex items-center justify-center flex-shrink-0 mt-0.5">
                <i data-lucide="${meta.icon}" class="w-4 h-4 ${meta.color}"></i>
            </div>
            <!-- Text -->
            <div class="flex-1 min-w-0">
                <p class="text-xs font-black text-gray-800 leading-snug
                          ${unread ? '' : 'font-bold text-gray-500'}">
                    ${n.title}
                </p>
                <p class="text-[10px] text-gray-400 mt-0.5 leading-snug line-clamp-2">
                    ${n.body}
                </p>
                <p class="text-[9px] text-gray-300 font-bold mt-1 uppercase tracking-wide">
                    ${ts}
                </p>
            </div>
            <!-- Unread dot -->
            ${unread ? `<div class="w-2 h-2 bg-[#D32F2F] rounded-full mt-1 flex-shrink-0"></div>` : ''}
        </div>`;
    }).join('');

    lucide.createIcons();
}

// ── Mark a single notification as read ───────────────────────────────────────
async function markNotifRead(id, el) {
    try {
        await authFetch('/api/notifications/mark_read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: [id] })
        });
        // Visually update the row immediately
        if (el) {
            el.classList.remove('bg-red-50/40', 'hover:bg-red-50');
            el.classList.add('hover:bg-gray-50');
            el.querySelector('.bg-\\[\\#D32F2F\\]')?.remove();
        }
        // Decrement badge
        const badge = document.getElementById('notifBadge');
        if (badge) {
            const current = parseInt(badge.textContent) || 0;
            updateBadge(Math.max(0, current - 1));
        }
    } catch { /* silent */ }
}

// ── Mark ALL as read ──────────────────────────────────────────────────────────
async function markAllNotifRead() {
    try {
        await authFetch('/api/notifications/mark_read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        updateBadge(0);
        await loadNotifications();
    } catch { /* silent */ }
}

// ── Update the red badge number ───────────────────────────────────────────────
function updateBadge(count) {
    const badge = document.getElementById('notifBadge');
    if (!badge) return;
    _lastUnreadCount = count;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('hidden');
        // Pulse the bell icon when new unread arrives
        const bell = document.getElementById('notifBell');
        if (bell) {
            bell.classList.add('animate-bounce');
            setTimeout(() => bell.classList.remove('animate-bounce'), 1000);
        }
    } else {
        badge.classList.add('hidden');
    }
}

// ── Format ISO timestamp to relative / absolute ───────────────────────────────
function _fmtNotifTime(iso) {
    if (!iso) return '';
    const d    = new Date(iso);
    const now  = new Date();
    const diff = Math.floor((now - d) / 1000);   // seconds ago

    if (diff < 60)          return 'Just now';
    if (diff < 3600)        return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400)       return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 86400 * 7)   return `${Math.floor(diff / 86400)}d ago`;

    return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

// ── Poll every 30 seconds for new notifications ───────────────────────────────
async function pollNotifications() {
    try {
        const res  = await authFetch('/api/notifications');
        const data = await res.json();
        const { unread = 0 } = data;
        // Only update badge if count changed (avoids animation flicker)
        if (unread !== _lastUnreadCount) {
            updateBadge(unread);
            // If panel is open, re-render immediately
            if (_notifPanelOpen) renderNotifList(data.notifications || []);
        }
    } catch { /* silent — no internet / session expired */ }
}

// ── SMTP Test Connection ──────────────────────────────────────────────────────
async function testSmtpConnection() {
    const btn    = document.getElementById('testSmtpBtn');
    const banner = document.getElementById('smtpTestResult');
    if (!btn || !banner) return;

    // Must be in edit mode to test (credentials must be saved first)
    if (btn.disabled) return;

    // Show loading state
    btn.disabled   = true;
    btn.innerHTML  = `<svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path></svg>
        Testing...`;
    banner.className = 'hidden';

    try {
        const res  = await authFetch('/api/test_smtp', { method: 'POST' });
        const data = await res.json();

        if (data.ok) {
            banner.className   = 'mt-3 p-4 rounded-xl text-xs font-bold leading-relaxed bg-green-50 text-green-700 border border-green-200';
            banner.textContent = data.message;
        } else {
            banner.className   = 'mt-3 p-4 rounded-xl text-xs font-bold leading-relaxed whitespace-pre-line bg-red-50 text-red-700 border border-red-200';
            banner.textContent = data.error;
        }
    } catch {
        banner.className   = 'mt-3 p-4 rounded-xl text-xs font-bold leading-relaxed bg-red-50 text-red-700 border border-red-200';
        banner.textContent = 'Could not reach the server. Check your connection.';
    } finally {
        btn.disabled  = false;
        btn.innerHTML = `<i data-lucide="plug-zap" class="w-4 h-4"></i> Test Connection`;
        lucide.createIcons();
    }
}


// ── NOTIFICATION POLLING ──────────────────────────────────────────────────────
function startNotifPolling() {
    // Initial load of badge count on page load
    pollNotifications();
    // Then poll every 30 seconds
    if (_notifPollTimer) clearInterval(_notifPollTimer);
    _notifPollTimer = setInterval(pollNotifications, 30_000);
}

// Auto-start polling once page loads
document.addEventListener('DOMContentLoaded', () => {
    // Slight delay to let auth token load first
    setTimeout(startNotifPolling, 1500);
});