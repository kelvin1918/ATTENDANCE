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
let editIdx         = -1;
let editSchedId     = -1;
let selectedHistoryIdx  = 0;
let showAllHistoryFiles = false;
let currentOpenedFolder = "";   // stores class_code of the open folder

// ── ON LOAD ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    updateTime();
    setInterval(updateTime, 1000);
    generateTimeOptions();

    // Check session — same logic as before, session still stored in localStorage
    const session = JSON.parse(localStorage.getItem('active_session'));
    if (session && session.email) {
        document.getElementById('user-display-email').textContent = session.email;
        document.getElementById('user-initials').textContent =
            session.email.substring(0, 2).toUpperCase();
    } else {
        window.location.href = "login.html";
        return;
    }

    // Load schedules from backend on startup
    await loadSchedules();
    renderDayFilters();
    showPage('home');
});

// ── CLOCK ─────────────────────────────────────────────────────────────────────

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

function showPage(page, btn = null) {
    if (btn) {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('sidebar-active'));
        btn.classList.add('sidebar-active');
    }
    searchVal   = "";
    currentType = page;
    if (page === 'home')    renderDashboard();
    else if (page === 'history') renderHistoryPage();
    else if (page === 'classes') renderFolderPage('classes');
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────

async function renderDashboard() {
    const content = document.getElementById('content-area');
    content.innerHTML = `
        <div class="mb-10">
            <h1 class="text-4xl font-black text-gray-900 mb-2 tracking-tighter">Dashboard</h1>
            <p class="text-gray-400 text-sm font-bold uppercase tracking-widest">Attendance Monitoring</p>
        </div>
        <div class="relative mb-10">
            <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>
            <input type="text" placeholder="Search everything..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none ring-1 ring-gray-100 focus:ring-red-200 transition">
        </div>
        <div class="bg-white p-8 rounded-[3rem] border border-gray-100 shadow-sm mb-10 h-[450px]">
             <h3 class="text-lg font-black text-gray-800 mb-6 flex items-center"><i data-lucide="bar-chart-3" class="w-5 h-5 mr-2 text-[#D32F2F]"></i> Analytics</h3>
             <div class="h-[320px] w-full"><canvas id="absentChart"></canvas></div>
        </div>
        <div class="bg-white p-8 rounded-[3rem] border border-gray-100 shadow-sm">
            <h3 class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-6">Recent Activity</h3>
            <div id="recentActivityList" class="space-y-4">
                <p class="text-center text-gray-300 font-bold py-4">Loading...</p>
            </div>
        </div>`;
    lucide.createIcons();

    // Load absence chart data from backend
    try {
        const res  = await authFetch('/api/absences');
        const data = await res.json();
        initChart(data);
    } catch {
        initChart([]);
    }

    // Load recent activity from backend
    try {
        const res     = await authFetch('/api/recent');
        const records = await res.json();
        const list    = document.getElementById('recentActivityList');

        if (records.length === 0) {
            list.innerHTML = '<p class="text-center text-gray-300 font-bold py-4">No recent history.</p>';
        } else {
            list.innerHTML = records.map(r => `
                <div class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl cursor-pointer hover:bg-red-50 transition"
                     onclick="goToHistoryByClassDate('${r.class_code}', '${r.date}')">
                    <div class="flex items-center space-x-4">
                        <div class="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-[#D32F2F] shadow-sm">
                            <i data-lucide="file-text" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <p class="text-sm font-black text-gray-900">${r.date}_Report.pdf</p>
                            <p class="text-[9px] text-gray-400 font-bold uppercase">${r.section} | ${r.subject}</p>
                        </div>
                    </div>
                    <p class="text-[9px] text-gray-400 font-bold">${r.time ? r.time.substring(0,5) : ''}</p>
                </div>`).join('');
            lucide.createIcons();
        }
    } catch {
        document.getElementById('recentActivityList').innerHTML =
            '<p class="text-center text-gray-300 font-bold py-4">Could not load recent activity.</p>';
    }
}

// Chart — uses real absence data from backend
function initChart(data = []) {
    const ctx = document.getElementById('absentChart');
    if (!ctx) return;
    const labels = data.map(d => d.name);
    const values = data.map(d => d.count);
    // Fallback dummy data if no absences yet
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['No absences yet'],
            datasets: [{ label: 'Absences', data: values.length ? values : [0], backgroundColor: '#D32F2F', borderRadius: 8 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { ticks: { font: { size: 9, weight: 'bold' } } } },
            plugins: { legend: { display: false } }
        }
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

async function renderHistoryPage() {
    currentType = 'history';

    try {
        const res = await authFetch('/api/sessions');
        historyFolders = await res.json();
    } catch {
        historyFolders = [];
    }

    const filtered    = historyFolders.filter(f =>
        (f.section + f.subject + f.date).toLowerCase().includes(searchVal.toLowerCase())
    );
    const activeData  = filtered[selectedHistoryIdx] || null;
    let dynamicTitle  = "Select a session";
    if (showAllHistoryFiles) dynamicTitle = "ALL SESSIONS";
    else if (activeData) dynamicTitle = `${activeData.section} — ${activeData.date}`;

    document.getElementById('content-area').innerHTML = `
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-4xl font-black text-gray-900 tracking-tighter uppercase">History</h1>
            <div class="flex space-x-2">
                <button onclick="showAllHistoryFiles = true; renderHistoryPage()" class="bg-gray-100 text-gray-600 px-6 py-3 rounded-xl text-[10px] font-black uppercase hover:bg-black hover:text-white transition">Show All Files</button>
            </div>
        </div>
        <div class="relative mb-8">
            <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>
            <input type="text" oninput="searchVal = this.value; renderHistoryPage()" value="${searchVal}" placeholder="Search archives..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">
        </div>
        <div class="flex gap-10 h-[calc(100%-250px)]">
            <div class="w-1/3 space-y-4 overflow-y-auto pr-4 border-r border-gray-50">
                ${filtered.map((f, i) => `
                    <div onclick="selectedHistoryIdx = ${i}; showAllHistoryFiles = false; renderHistoryPage()"
                         class="p-6 rounded-[2rem] cursor-pointer transition flex items-center justify-between ${!showAllHistoryFiles && i === selectedHistoryIdx ? 'bg-red-50 border-2 border-red-100' : 'bg-white hover:bg-gray-50'}">
                        <div class="flex items-center space-x-4 min-w-0">
                            <div class="w-10 h-10 rounded-xl flex items-center justify-center ${!showAllHistoryFiles && i === selectedHistoryIdx ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-gray-400'}">
                                <i data-lucide="folder-archive" class="w-5 h-5"></i>
                            </div>
                            <div class="min-w-0">
                                <h4 class="font-black text-gray-900 truncate">${f.section}</h4>
                                <p class="text-[9px] font-bold text-gray-400 uppercase">${f.subject} | ${f.date}</p>
                            </div>
                        </div>
                    </div>`).join('')}
            </div>
            <div class="flex-1 bg-gray-50/50 border-2 border-dashed border-gray-200 rounded-[3rem] p-8 overflow-y-auto flex flex-col">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="font-black text-[12px] text-gray-400 uppercase tracking-widest">${dynamicTitle}</h3>
                    ${activeData ? `
                    <button onclick="downloadPDF('${activeData.class_code}', '${activeData.date}')"
                            class="flex items-center space-x-2 px-4 py-2 bg-red-50 text-[#D32F2F] rounded-xl font-bold text-xs hover:bg-red-100 transition">
                        <i data-lucide="download" class="w-4 h-4"></i> <span>Download PDF</span>
                    </button>` : ''}
                </div>
                ${activeData ? `
                <div id="sessionDetail">
                    <p class="text-center text-gray-300 font-bold py-4 text-xs">Loading records...</p>
                </div>` : `
                <div class="flex-1 flex items-center justify-center text-gray-300 font-bold text-xs uppercase">
                    Select a session on the left
                </div>`}
            </div>
        </div>`;
    lucide.createIcons();

    if (activeData) loadSessionDetail(activeData.class_code, activeData.date);
}

async function loadSessionDetail(class_code, date) {
    try {
        const res     = await authFetch(`/api/attendance/${class_code}/${date}`);
        const records = await res.json();
        const present = records.filter(r => r.status === 'Present');
        const late    = records.filter(r => r.status === 'Late');
        const absent  = records.filter(r => r.status === 'Absent');

        const renderRows = (list, color, label) => list.map(r => `
            <div class="flex items-center justify-between p-4 bg-white rounded-2xl border border-gray-100 mb-2">
                <div>
                    <p class="text-sm font-black text-gray-900">${r.name}</p>
                    <p class="text-[9px] text-gray-400 font-bold">${r.sr_code || ''}</p>
                </div>
                <div class="text-right">
                    <span class="text-[10px] font-black ${color} uppercase">${label}</span>
                    <p class="text-[9px] text-gray-400">${r.timestamp ? r.timestamp.substring(11,16) : '—'}</p>
                </div>
            </div>`).join('');

        document.getElementById('sessionDetail').innerHTML = `
            <p class="text-[10px] font-black text-gray-400 uppercase mb-3">Present (${present.length})</p>
            ${renderRows(present, 'text-green-500', 'Present')}
            <p class="text-[10px] font-black text-gray-400 uppercase mb-3 mt-4">Late (${late.length})</p>
            ${renderRows(late, 'text-yellow-500', 'Late')}
            <p class="text-[10px] font-black text-gray-400 uppercase mb-3 mt-4">Absent (${absent.length})</p>
            ${renderRows(absent, 'text-red-500', 'Absent')}`;
    } catch {
        document.getElementById('sessionDetail').innerHTML =
            '<p class="text-center text-gray-300 font-bold py-4 text-xs">Could not load records.</p>';
    }
}

function downloadPDF(class_code, date) {
    window.open(`/api/download_pdf/${class_code}/${date}`, '_blank');
}

function goToHistoryByClassDate(class_code, date) {
    showPage('history');
}

// ── FOLDER VIEW (inside a class) ──────────────────────────────────────────────

async function openFolderView(class_code) {
    currentOpenedFolder = class_code;

    // Get class info from already-loaded classFolders
    const cls = classFolders.find(f => f.id === class_code) || {};

    document.getElementById('content-area').innerHTML = `
        <div class="flex justify-between items-start mb-8">
            <button onclick="showPage('classes')" class="text-gray-400 hover:text-[#D32F2F] font-bold text-xs uppercase flex items-center transition">
                <i data-lucide="arrow-left" class="w-4 h-4 mr-2"></i> Back
            </button>
            <div class="flex space-x-3">
                <button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-[10px] font-black uppercase">Registration</button>
                <button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2">
                    <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>
                </button>
            </div>
        </div>
        <h1 class="text-4xl font-black text-gray-900 tracking-tighter uppercase">${cls.subject || class_code}</h1>
        <p class="text-gray-400 font-bold text-sm uppercase tracking-widest mt-1">${cls.section || ''} • ${cls.course_code || ''}</p>
        <div id="studentListArea" class="mt-10">
            <p class="text-center text-gray-300 font-bold py-4 text-xs">Loading students...</p>
        </div>`;
    lucide.createIcons();

    // Load students from backend
    try {
        const res      = await authFetch(`/api/students/${class_code}`);
        const students = await res.json();
        const area     = document.getElementById('studentListArea');
        if (students.length === 0) {
            area.innerHTML = `<div class="mt-10 text-center py-20 border-2 border-dashed border-gray-100 rounded-[3rem] text-gray-300 font-bold uppercase text-[10px]">No students yet. Click Registration to add.</div>`;
        } else {
            area.innerHTML = `
                <div class="space-y-3">
                    ${students.map(s => `
                        <div class="flex items-center justify-between p-5 bg-white rounded-2xl border border-gray-100">
                            <div class="flex items-center space-x-4">
                                <div class="w-10 h-10 bg-red-50 rounded-full flex items-center justify-center text-[#D32F2F] font-black text-xs">
                                    ${s.name.substring(0,2).toUpperCase()}
                                </div>
                                <div>
                                    <p class="font-black text-gray-900 text-sm">${s.name}</p>
                                    <p class="text-[9px] text-gray-400 font-bold uppercase">${s.sr_code || ''} • ${s.email || ''}</p>
                                </div>
                            </div>
                        </div>`).join('')}
                </div>`;
        }
    } catch {
        document.getElementById('studentListArea').innerHTML =
            '<p class="text-center text-gray-300 font-bold py-4 text-xs">Could not load students.</p>';
    }
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
        <button onclick="selectedDay='${d}'; renderDayFilters()" class="flex-1 py-3 text-[10px] font-black border rounded-xl transition ${d === selectedDay ? 'bg-[#D32F2F] text-white border-[#D32F2F]' : 'bg-white text-gray-400'}">${d}</button>
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
        class_code: currentOpenedFolder || null,
        subject:    document.getElementById('modalSubName').value,
        day:        document.getElementById('modalDaySelect').value,
        room:       document.getElementById('modalRoom').value,
        time:       document.getElementById('modalTimeFrom').value + ' - ' + document.getElementById('modalTimeTo').value,
    };

    if (editSchedId > -1) {
        await authFetch(`/api/schedules/${editSchedId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } else {
        await fetch('/api/schedules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }
    await loadSchedules();
    renderDayFilters();
    closeTaskModal();
}

function editSchedule(id) {
    const s = schedules.find(item => item.id === id);
    if (!s) return;
    editSchedId = s.id;
    document.getElementById('modalSubName').value  = s.subject;
    document.getElementById('modalDaySelect').value = s.day;
    document.getElementById('modalRoom').value     = s.room;
    document.getElementById('taskModal').classList.remove('hidden');
}

// ── FOLDER MODAL (Create/Edit Class) ─────────────────────────────────────────

async function saveFolderModal() {
    const subject = document.getElementById('modalSubject').value;
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
    // Ensure class_code is set (backup in case hidden field is empty)
    if (!formData.get('class_code')) {
        formData.set('class_code', currentOpenedFolder);
    }
    try {
        const session = JSON.parse(localStorage.getItem('active_session') || '{}');
        const res  = await fetch('/api/add_student', {
            method: 'POST',
            body: formData,
            headers: { 'X-Instructor-Email': session.email || '' }
        });
        const data = await res.json();
        if (!res.ok) {
            alert('Error: ' + (data.error || 'Failed to save student.'));
            return;
        }
        closeRegModal();
        openFolderView(currentOpenedFolder);  // reload student list
    } catch(e) {
        alert('Failed to save student: ' + e.message);
    }
}

// ── CAMERA ────────────────────────────────────────────────────────────────────
// Connects to Flask /video_feed (MJPEG stream from facerecog.py)
// Polls /api/present_students every 2 seconds for the recognition panel

let _pollInterval = null;

function openCamera() {
    document.getElementById('recognizedList').innerHTML = "";
    document.getElementById('cameraModal').classList.remove('hidden');
    document.getElementById('cameraLoading').classList.remove('hidden');
    document.getElementById('dummyFeed').classList.add('hidden');

    setTimeout(() => {
        document.getElementById('cameraLoading').classList.add('hidden');

        // Replace dummyFeed content with real MJPEG stream
        const dummyFeed = document.getElementById('dummyFeed');
        dummyFeed.classList.remove('hidden');
        dummyFeed.innerHTML = `<img src="/video_feed" style="width:100%; height:100%; object-fit:cover;">`;

        // Poll present students every 2 seconds
        _pollInterval = setInterval(async () => {
            try {
                const res      = await authFetch('/api/present_students');
                const students = await res.json();
                const list     = document.getElementById('recognizedList');
                list.innerHTML = students.map(name => `
                    <div class="flex justify-between border-b pb-4">
                        <div>
                            <p class="text-sm font-black">${name}</p>
                            <p class="text-[9px] font-bold text-gray-400">${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</p>
                        </div>
                        <span class="text-[10px] font-black text-green-500 uppercase">Present</span>
                    </div>`).join('');
            } catch {}
        }, 2000);
    }, 2000);
}

function closeCamera() {
    document.getElementById('cameraModal').classList.add('hidden');
    if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
}

// Save attendance from camera panel
async function saveAttendanceFromCamera() {
    if (!currentOpenedFolder) return;
    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};

    try {
        const res      = await authFetch('/api/present_students');
        const present  = await res.json();

        // Build all students list: present ones + mark rest as absent
        const allRes  = await authFetch(`/api/students/${currentOpenedFolder}`);
        const allStud = await allRes.json();

        const records = allStud.map(s => ({
            name:      s.name,
            sr_code:   s.sr_code || '',
            status:    present.includes(s.name) ? 'Present' : 'Absent',
            timestamp: present.includes(s.name) ? new Date().toTimeString().substring(0,8) : ''
        }));

        await authFetch('/api/save_attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                class_code: currentOpenedFolder,
                section:    cls.section || '',
                subject:    cls.subject || '',
                records:    records
            })
        });

        closeCamera();
        alert('Attendance saved!');
    } catch {
        alert('Failed to save attendance.');
    }
}

// ── CONFIRM DIALOG (unchanged logic, updated backend calls) ───────────────────

function confirmAction(action, id) {
    const modal = document.getElementById('customConfirm');
    modal.classList.remove('hidden');
    document.getElementById('confirmDesc').innerText = "Proceed with this action?";

    document.getElementById('confirmBtn').onclick = async () => {
        if (action === 'deleteFolder') {
            await fetch(`/api/delete_class/${id}`, { method: 'DELETE' });
            showPage('classes');
        } else if (action === 'deleteSubject') {
            await authFetch(`/api/schedules/${id}`, { method: 'DELETE' });
            await loadSchedules();
            renderDayFilters();
        } else if (action === 'logout') {
            localStorage.removeItem('active_session');
            window.location.href = "login.html";
        }
        closeConfirm();
    };
}

function closeConfirm() { document.getElementById('customConfirm').classList.add('hidden'); }

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
function openFolderModal() { editIdx = -1; document.getElementById('classModal').classList.remove('hidden'); }

// ── SIDEBAR TOGGLE (unchanged) ────────────────────────────────────────────────

function toggleMiniSidebar() {
    const sidebar = document.getElementById('navSidebar');
    const icon    = document.getElementById('toggleIcon');
    sidebar.classList.toggle('nav-collapsed');
    icon.setAttribute('data-lucide', sidebar.classList.contains('nav-collapsed') ? 'chevron-right' : 'chevron-left');
    lucide.createIcons();
}

// ── DOCUMENT VIEWER (unchanged — now uses real PDF) ───────────────────────────

function openRealDoc(class_code, date) {
    window.open(`/api/download_pdf/${class_code}/${date}`, '_blank');
}