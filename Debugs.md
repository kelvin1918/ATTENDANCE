Css/html/js are functional

API is functional

Database is now functional



they are now connected to each other



running python app.py is successful it redirects now to login



instructor account inserted (for temp) successful



clock and date is working in panel



dashboard is empty (normal)



class empty (normal)



history empty (normal)



===============================================================================================================================



debug log



add class is successful function 

&#x09;> submission is working

&#x09;> verified in database class table



register student is successful function

&#x09;> submission is **not working**

&#x09;> database verification - **no result**



add schedule is successful function

&#x09;> submission is **not working** (display in panel)

&#x09;> verified in database schedule table



=================================================================================================================================



To fix:



student submission

schedule display



\# remaining fully not functional





===============================================================================================================================



recent codes without debugs (to be conntinue)



script.js - issue - student submission not working



// =============================================================================

// script.js — CONNECTED TO FLASK BACKEND

// Structure is identical to your original.

// localStorage replaced with fetch() calls to app.py.

// HTML/CSS is untouched.

// =============================================================================



let schedules       = \[];

let classFolders    = \[];

let historyFolders  = \[];

let attendanceLogs  = {};

let selectedDay     = "MON";

let searchVal       = "";

let currentType     = 'home';

let editIdx         = -1;

let editSchedId     = -1;

let selectedHistoryIdx  = 0;

let showAllHistoryFiles = false;

let currentOpenedFolder = "";   // stores class\_code of the open folder



// ── ON LOAD ───────────────────────────────────────────────────────────────────



document.addEventListener('DOMContentLoaded', async () => {

&#x20;   updateTime();

&#x20;   setInterval(updateTime, 1000);

&#x20;   generateTimeOptions();



&#x20;   // Safe localStorage read — won't crash if browser blocks it

&#x20;   let session = null;

&#x20;   try {

&#x20;       session = JSON.parse(localStorage.getItem('active\_session'));

&#x20;   } catch(e) {

&#x20;       session = null;

&#x20;   }



&#x20;   if (session \&\& session.email) {

&#x20;       document.getElementById('user-display-email').textContent = session.email;

&#x20;       document.getElementById('user-initials').textContent =

&#x20;           session.email.substring(0, 2).toUpperCase();

&#x20;   } else {

&#x20;       window.location.href = "/login";

&#x20;       return;

&#x20;   }



&#x20;   await loadSchedules();

&#x20;   renderDayFilters();

&#x20;   showPage('home');

});



// ── CLOCK ─────────────────────────────────────────────────────────────────────



function updateTime() {

&#x20;   const clockEl = document.getElementById('clock');

&#x20;   const dateEl  = document.getElementById('date');

&#x20;   const now     = new Date();

&#x20;   if (clockEl) clockEl.textContent = now.toLocaleTimeString(\[], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

&#x20;   if (dateEl)  dateEl.textContent  = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

}



// ── TIME OPTIONS (unchanged) ──────────────────────────────────────────────────



function generateTimeOptions() {

&#x20;   const from = document.getElementById('modalTimeFrom');

&#x20;   const to   = document.getElementById('modalTimeTo');

&#x20;   if (!from || !to) return;

&#x20;   let options = "";

&#x20;   for (let i = 7; i <= 21; i++) {

&#x20;       const hour = i > 12 ? i - 12 : i;

&#x20;       const ampm = i >= 12 ? 'PM' : 'AM';

&#x20;       const t1 = `${hour}:00 ${ampm}`;

&#x20;       const t2 = `${hour}:30 ${ampm}`;

&#x20;       options += `<option value="${t1}">${t1}</option><option value="${t2}">${t2}</option>`;

&#x20;   }

&#x20;   from.innerHTML = options;

&#x20;   to.innerHTML   = options;

}



// ── NAVIGATION (unchanged) ────────────────────────────────────────────────────



function showPage(page, btn = null) {

&#x20;   if (btn) {

&#x20;       document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('sidebar-active'));

&#x20;       btn.classList.add('sidebar-active');

&#x20;   }

&#x20;   searchVal   = "";

&#x20;   currentType = page;

&#x20;   if (page === 'home')    renderDashboard();

&#x20;   else if (page === 'history') renderHistoryPage();

&#x20;   else if (page === 'classes') renderFolderPage('classes');

}



// ── DASHBOARD ─────────────────────────────────────────────────────────────────



async function renderDashboard() {

&#x20;   const content = document.getElementById('content-area');

&#x20;   content.innerHTML = `

&#x20;       <div class="mb-10">

&#x20;           <h1 class="text-4xl font-black text-gray-900 mb-2 tracking-tighter">Dashboard</h1>

&#x20;           <p class="text-gray-400 text-sm font-bold uppercase tracking-widest">Attendance Monitoring</p>

&#x20;       </div>

&#x20;       <div class="relative mb-10">

&#x20;           <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>

&#x20;           <input type="text" placeholder="Search everything..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none ring-1 ring-gray-100 focus:ring-red-200 transition">

&#x20;       </div>

&#x20;       <div class="bg-white p-8 rounded-\[3rem] border border-gray-100 shadow-sm mb-10 h-\[450px]">

&#x20;            <h3 class="text-lg font-black text-gray-800 mb-6 flex items-center"><i data-lucide="bar-chart-3" class="w-5 h-5 mr-2 text-\[#D32F2F]"></i> Analytics</h3>

&#x20;            <div class="h-\[320px] w-full"><canvas id="absentChart"></canvas></div>

&#x20;       </div>

&#x20;       <div class="bg-white p-8 rounded-\[3rem] border border-gray-100 shadow-sm">

&#x20;           <h3 class="text-\[10px] font-black text-gray-400 uppercase tracking-widest mb-6">Recent Activity</h3>

&#x20;           <div id="recentActivityList" class="space-y-4">

&#x20;               <p class="text-center text-gray-300 font-bold py-4">Loading...</p>

&#x20;           </div>

&#x20;       </div>`;

&#x20;   lucide.createIcons();



&#x20;   // Load absence chart data from backend

&#x20;   try {

&#x20;       const res  = await fetch('/api/absences');

&#x20;       const data = await res.json();

&#x20;       initChart(data);

&#x20;   } catch {

&#x20;       initChart(\[]);

&#x20;   }



&#x20;   // Load recent activity from backend

&#x20;   try {

&#x20;       const res     = await fetch('/api/recent');

&#x20;       const records = await res.json();

&#x20;       const list    = document.getElementById('recentActivityList');



&#x20;       if (records.length === 0) {

&#x20;           list.innerHTML = '<p class="text-center text-gray-300 font-bold py-4">No recent history.</p>';

&#x20;       } else {

&#x20;           list.innerHTML = records.map(r => `

&#x20;               <div class="flex items-center justify-between p-4 bg-gray-50 rounded-2xl cursor-pointer hover:bg-red-50 transition"

&#x20;                    onclick="goToHistoryByClassDate('${r.class\_code}', '${r.date}')">

&#x20;                   <div class="flex items-center space-x-4">

&#x20;                       <div class="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-\[#D32F2F] shadow-sm">

&#x20;                           <i data-lucide="file-text" class="w-4 h-4"></i>

&#x20;                       </div>

&#x20;                       <div>

&#x20;                           <p class="text-sm font-black text-gray-900">${r.date}\_Report.pdf</p>

&#x20;                           <p class="text-\[9px] text-gray-400 font-bold uppercase">${r.section} | ${r.subject}</p>

&#x20;                       </div>

&#x20;                   </div>

&#x20;                   <p class="text-\[9px] text-gray-400 font-bold">${r.time ? r.time.substring(0,5) : ''}</p>

&#x20;               </div>`).join('');

&#x20;           lucide.createIcons();

&#x20;       }

&#x20;   } catch {

&#x20;       document.getElementById('recentActivityList').innerHTML =

&#x20;           '<p class="text-center text-gray-300 font-bold py-4">Could not load recent activity.</p>';

&#x20;   }

}



// Chart — uses real absence data from backend

function initChart(data = \[]) {

&#x20;   const ctx = document.getElementById('absentChart');

&#x20;   if (!ctx) return;

&#x20;   const labels = data.map(d => d.name);

&#x20;   const values = data.map(d => d.count);

&#x20;   // Fallback dummy data if no absences yet

&#x20;   new Chart(ctx, {

&#x20;       type: 'bar',

&#x20;       data: {

&#x20;           labels: labels.length ? labels : \['No absences yet'],

&#x20;           datasets: \[{ label: 'Absences', data: values.length ? values : \[0], backgroundColor: '#D32F2F', borderRadius: 8 }]

&#x20;       },

&#x20;       options: {

&#x20;           responsive: true,

&#x20;           maintainAspectRatio: false,

&#x20;           scales: { x: { ticks: { font: { size: 9, weight: 'bold' } } } },

&#x20;           plugins: { legend: { display: false } }

&#x20;       }

&#x20;   });

}



// ── CLASSES (FOLDERS) ─────────────────────────────────────────────────────────



async function renderFolderPage(type) {

&#x20;   currentType = type;



&#x20;   // Load classes from backend

&#x20;   try {

&#x20;       const res = await fetch('/api/classes');

&#x20;       classFolders = await res.json();

&#x20;   } catch {

&#x20;       classFolders = \[];

&#x20;   }



&#x20;   const filtered = classFolders.filter(f =>

&#x20;       (f.subject + f.section + f.course\_code).toLowerCase().includes(searchVal.toLowerCase())

&#x20;   );



&#x20;   document.getElementById('content-area').innerHTML = `

&#x20;       <div class="flex justify-between items-center mb-10">

&#x20;           <h1 class="text-3xl font-black text-gray-900 tracking-tighter uppercase">${type}</h1>

&#x20;           <button onclick="openFolderModal()" class="bg-\[#D32F2F] text-white px-6 py-3 rounded-xl text-xs font-bold shadow-lg shadow-red-100">+ Create Folder</button>

&#x20;       </div>

&#x20;       <div class="relative mb-10">

&#x20;           <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>

&#x20;           <input type="text" oninput="searchVal = this.value; renderFolderPage('${type}')" value="${searchVal}" placeholder="Search..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">

&#x20;       </div>

&#x20;       <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

&#x20;           ${filtered.map((f, i) => `

&#x20;               <div onclick="openFolderView('${f.id}')" class="bg-white p-6 rounded-\[2rem] border border-gray-100 shadow-sm hover:shadow-xl cursor-pointer group">

&#x20;                   <div class="flex justify-between mb-4">

&#x20;                       <div class="w-12 h-12 bg-red-50 rounded-2xl flex items-center justify-center text-\[#D32F2F] group-hover:bg-\[#D32F2F] group-hover:text-white transition">

&#x20;                           <i data-lucide="folder"></i>

&#x20;                       </div>

&#x20;                       <div class="flex space-x-1" onclick="event.stopPropagation()">

&#x20;                           <button onclick="editFolder('${f.id}')" class="p-2 text-gray-300 hover:text-blue-500"><i data-lucide="edit-3" class="w-4 h-4"></i></button>

&#x20;                           <button onclick="confirmAction('deleteFolder', '${f.id}')" class="p-2 text-gray-300 hover:text-red-500"><i data-lucide="trash-2" class="w-4 h-4"></i></button>

&#x20;                       </div>

&#x20;                   </div>

&#x20;                   <h3 class="font-black text-gray-900 text-lg">${f.subject}</h3>

&#x20;                   <p class="text-\[10px] text-gray-500 font-bold uppercase tracking-widest">${f.section} • ${f.course\_code}</p>

&#x20;               </div>`).join('')}

&#x20;       </div>`;

&#x20;   lucide.createIcons();

}



// ── HISTORY ───────────────────────────────────────────────────────────────────



async function renderHistoryPage() {

&#x20;   currentType = 'history';



&#x20;   try {

&#x20;       const res = await fetch('/api/sessions');

&#x20;       historyFolders = await res.json();

&#x20;   } catch {

&#x20;       historyFolders = \[];

&#x20;   }



&#x20;   const filtered    = historyFolders.filter(f =>

&#x20;       (f.section + f.subject + f.date).toLowerCase().includes(searchVal.toLowerCase())

&#x20;   );

&#x20;   const activeData  = filtered\[selectedHistoryIdx] || null;

&#x20;   let dynamicTitle  = "Select a session";

&#x20;   if (showAllHistoryFiles) dynamicTitle = "ALL SESSIONS";

&#x20;   else if (activeData) dynamicTitle = `${activeData.section} — ${activeData.date}`;



&#x20;   document.getElementById('content-area').innerHTML = `

&#x20;       <div class="flex justify-between items-center mb-6">

&#x20;           <h1 class="text-4xl font-black text-gray-900 tracking-tighter uppercase">History</h1>

&#x20;           <div class="flex space-x-2">

&#x20;               <button onclick="showAllHistoryFiles = true; renderHistoryPage()" class="bg-gray-100 text-gray-600 px-6 py-3 rounded-xl text-\[10px] font-black uppercase hover:bg-black hover:text-white transition">Show All Files</button>

&#x20;           </div>

&#x20;       </div>

&#x20;       <div class="relative mb-8">

&#x20;           <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300"></i>

&#x20;           <input type="text" oninput="searchVal = this.value; renderHistoryPage()" value="${searchVal}" placeholder="Search archives..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">

&#x20;       </div>

&#x20;       <div class="flex gap-10 h-\[calc(100%-250px)]">

&#x20;           <div class="w-1/3 space-y-4 overflow-y-auto pr-4 border-r border-gray-50">

&#x20;               ${filtered.map((f, i) => `

&#x20;                   <div onclick="selectedHistoryIdx = ${i}; showAllHistoryFiles = false; renderHistoryPage()"

&#x20;                        class="p-6 rounded-\[2rem] cursor-pointer transition flex items-center justify-between ${!showAllHistoryFiles \&\& i === selectedHistoryIdx ? 'bg-red-50 border-2 border-red-100' : 'bg-white hover:bg-gray-50'}">

&#x20;                       <div class="flex items-center space-x-4 min-w-0">

&#x20;                           <div class="w-10 h-10 rounded-xl flex items-center justify-center ${!showAllHistoryFiles \&\& i === selectedHistoryIdx ? 'bg-\[#D32F2F] text-white' : 'bg-gray-100 text-gray-400'}">

&#x20;                               <i data-lucide="folder-archive" class="w-5 h-5"></i>

&#x20;                           </div>

&#x20;                           <div class="min-w-0">

&#x20;                               <h4 class="font-black text-gray-900 truncate">${f.section}</h4>

&#x20;                               <p class="text-\[9px] font-bold text-gray-400 uppercase">${f.subject} | ${f.date}</p>

&#x20;                           </div>

&#x20;                       </div>

&#x20;                   </div>`).join('')}

&#x20;           </div>

&#x20;           <div class="flex-1 bg-gray-50/50 border-2 border-dashed border-gray-200 rounded-\[3rem] p-8 overflow-y-auto flex flex-col">

&#x20;               <div class="flex justify-between items-center mb-6">

&#x20;                   <h3 class="font-black text-\[12px] text-gray-400 uppercase tracking-widest">${dynamicTitle}</h3>

&#x20;                   ${activeData ? `

&#x20;                   <button onclick="downloadPDF('${activeData.class\_code}', '${activeData.date}')"

&#x20;                           class="flex items-center space-x-2 px-4 py-2 bg-red-50 text-\[#D32F2F] rounded-xl font-bold text-xs hover:bg-red-100 transition">

&#x20;                       <i data-lucide="download" class="w-4 h-4"></i> <span>Download PDF</span>

&#x20;                   </button>` : ''}

&#x20;               </div>

&#x20;               ${activeData ? `

&#x20;               <div id="sessionDetail">

&#x20;                   <p class="text-center text-gray-300 font-bold py-4 text-xs">Loading records...</p>

&#x20;               </div>` : `

&#x20;               <div class="flex-1 flex items-center justify-center text-gray-300 font-bold text-xs uppercase">

&#x20;                   Select a session on the left

&#x20;               </div>`}

&#x20;           </div>

&#x20;       </div>`;

&#x20;   lucide.createIcons();



&#x20;   if (activeData) loadSessionDetail(activeData.class\_code, activeData.date);

}



async function loadSessionDetail(class\_code, date) {

&#x20;   try {

&#x20;       const res     = await fetch(`/api/attendance/${class\_code}/${date}`);

&#x20;       const records = await res.json();

&#x20;       const present = records.filter(r => r.status === 'Present');

&#x20;       const late    = records.filter(r => r.status === 'Late');

&#x20;       const absent  = records.filter(r => r.status === 'Absent');



&#x20;       const renderRows = (list, color, label) => list.map(r => `

&#x20;           <div class="flex items-center justify-between p-4 bg-white rounded-2xl border border-gray-100 mb-2">

&#x20;               <div>

&#x20;                   <p class="text-sm font-black text-gray-900">${r.name}</p>

&#x20;                   <p class="text-\[9px] text-gray-400 font-bold">${r.sr\_code || ''}</p>

&#x20;               </div>

&#x20;               <div class="text-right">

&#x20;                   <span class="text-\[10px] font-black ${color} uppercase">${label}</span>

&#x20;                   <p class="text-\[9px] text-gray-400">${r.timestamp ? r.timestamp.substring(11,16) : '—'}</p>

&#x20;               </div>

&#x20;           </div>`).join('');



&#x20;       document.getElementById('sessionDetail').innerHTML = `

&#x20;           <p class="text-\[10px] font-black text-gray-400 uppercase mb-3">Present (${present.length})</p>

&#x20;           ${renderRows(present, 'text-green-500', 'Present')}

&#x20;           <p class="text-\[10px] font-black text-gray-400 uppercase mb-3 mt-4">Late (${late.length})</p>

&#x20;           ${renderRows(late, 'text-yellow-500', 'Late')}

&#x20;           <p class="text-\[10px] font-black text-gray-400 uppercase mb-3 mt-4">Absent (${absent.length})</p>

&#x20;           ${renderRows(absent, 'text-red-500', 'Absent')}`;

&#x20;   } catch {

&#x20;       document.getElementById('sessionDetail').innerHTML =

&#x20;           '<p class="text-center text-gray-300 font-bold py-4 text-xs">Could not load records.</p>';

&#x20;   }

}



function downloadPDF(class\_code, date) {

&#x20;   window.open(`/api/download\_pdf/${class\_code}/${date}`, '\_blank');

}



function goToHistoryByClassDate(class\_code, date) {

&#x20;   showPage('history');

}



// ── FOLDER VIEW (inside a class) ──────────────────────────────────────────────



async function openFolderView(class\_code) {

&#x20;   currentOpenedFolder = class\_code;



&#x20;   // Get class info from already-loaded classFolders

&#x20;   const cls = classFolders.find(f => f.id === class\_code) || {};



&#x20;   document.getElementById('content-area').innerHTML = `

&#x20;       <div class="flex justify-between items-start mb-8">

&#x20;           <button onclick="showPage('classes')" class="text-gray-400 hover:text-\[#D32F2F] font-bold text-xs uppercase flex items-center transition">

&#x20;               <i data-lucide="arrow-left" class="w-4 h-4 mr-2"></i> Back

&#x20;           </button>

&#x20;           <div class="flex space-x-3">

&#x20;               <button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-\[10px] font-black uppercase">Registration</button>

&#x20;               <button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-\[10px] font-black uppercase flex items-center space-x-2">

&#x20;                   <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>

&#x20;               </button>

&#x20;           </div>

&#x20;       </div>

&#x20;       <h1 class="text-4xl font-black text-gray-900 tracking-tighter uppercase">${cls.subject || class\_code}</h1>

&#x20;       <p class="text-gray-400 font-bold text-sm uppercase tracking-widest mt-1">${cls.section || ''} • ${cls.course\_code || ''}</p>

&#x20;       <div id="studentListArea" class="mt-10">

&#x20;           <p class="text-center text-gray-300 font-bold py-4 text-xs">Loading students...</p>

&#x20;       </div>`;

&#x20;   lucide.createIcons();



&#x20;   // Load students from backend

&#x20;   try {

&#x20;       const res      = await fetch(`/api/students/${class\_code}`);

&#x20;       const students = await res.json();

&#x20;       const area     = document.getElementById('studentListArea');

&#x20;       if (students.length === 0) {

&#x20;           area.innerHTML = `<div class="mt-10 text-center py-20 border-2 border-dashed border-gray-100 rounded-\[3rem] text-gray-300 font-bold uppercase text-\[10px]">No students yet. Click Registration to add.</div>`;

&#x20;       } else {

&#x20;           area.innerHTML = `

&#x20;               <div class="space-y-3">

&#x20;                   ${students.map(s => `

&#x20;                       <div class="flex items-center justify-between p-5 bg-white rounded-2xl border border-gray-100">

&#x20;                           <div class="flex items-center space-x-4">

&#x20;                               <div class="w-10 h-10 bg-red-50 rounded-full flex items-center justify-center text-\[#D32F2F] font-black text-xs">

&#x20;                                   ${s.name.substring(0,2).toUpperCase()}

&#x20;                               </div>

&#x20;                               <div>

&#x20;                                   <p class="font-black text-gray-900 text-sm">${s.name}</p>

&#x20;                                   <p class="text-\[9px] text-gray-400 font-bold uppercase">${s.sr\_code || ''} • ${s.email || ''}</p>

&#x20;                               </div>

&#x20;                           </div>

&#x20;                       </div>`).join('')}

&#x20;               </div>`;

&#x20;       }

&#x20;   } catch {

&#x20;       document.getElementById('studentListArea').innerHTML =

&#x20;           '<p class="text-center text-gray-300 font-bold py-4 text-xs">Could not load students.</p>';

&#x20;   }

}



// ── SCHEDULE ──────────────────────────────────────────────────────────────────



async function loadSchedules() {

&#x20;   try {

&#x20;       const res = await fetch('/api/schedules');

&#x20;       schedules = await res.json();

&#x20;   } catch {

&#x20;       schedules = \[];

&#x20;   }

}



function renderDayFilters() {

&#x20;   const days      = \['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

&#x20;   const container = document.getElementById('day-filters');

&#x20;   if (!container) return;



&#x20;   container.innerHTML = days.map(d => `

&#x20;       <button onclick="selectedDay='${d}'; renderDayFilters()" class="flex-1 py-3 text-\[10px] font-black border rounded-xl transition ${d === selectedDay ? 'bg-\[#D32F2F] text-white border-\[#D32F2F]' : 'bg-white text-gray-400'}">${d}</button>

&#x20;   `).join('');



&#x20;   const filtered = schedules.filter(s => s.day === selectedDay);

&#x20;   document.getElementById('schedule-list').innerHTML = filtered.length ? filtered.map(s => `

&#x20;       <div class="bg-white p-5 rounded-3xl border border-gray-50 shadow-sm relative group hover:border-red-50 transition-all">

&#x20;           <div class="flex justify-between items-start mb-1">

&#x20;               <h4 class="font-bold text-gray-900 text-sm">${s.subject}</h4>

&#x20;               <div class="flex space-x-1 opacity-0 group-hover:opacity-100 transition">

&#x20;                   <button onclick="editSchedule(${s.id})" class="text-gray-400 hover:text-blue-500"><i data-lucide="edit-3" class="w-3 h-3"></i></button>

&#x20;                   <button onclick="confirmAction('deleteSubject', ${s.id})" class="text-gray-400 hover:text-red-500"><i data-lucide="trash-2" class="w-3 h-3"></i></button>

&#x20;               </div>

&#x20;           </div>

&#x20;           <p class="text-\[9px] text-gray-400 font-bold uppercase tracking-widest">RM ${s.room} • <span class="text-\[#D32F2F]">${s.time}</span></p>

&#x20;       </div>`).join('') : '<p class="text-center text-\[10px] text-gray-300 py-10 font-bold">Free Schedule</p>';

&#x20;   lucide.createIcons();

}



async function saveSubject() {

&#x20;   const payload = {

&#x20;       class\_code: currentOpenedFolder || null,

&#x20;       subject:    document.getElementById('modalSubName').value,

&#x20;       day:        document.getElementById('modalDaySelect').value,

&#x20;       room:       document.getElementById('modalRoom').value,

&#x20;       time:       document.getElementById('modalTimeFrom').value + ' - ' + document.getElementById('modalTimeTo').value,

&#x20;   };



&#x20;   if (editSchedId > -1) {

&#x20;       await fetch(`/api/schedules/${editSchedId}`, {

&#x20;           method: 'POST',

&#x20;           headers: { 'Content-Type': 'application/json' },

&#x20;           body: JSON.stringify(payload)

&#x20;       });

&#x20;   } else {

&#x20;       await fetch('/api/schedules', {

&#x20;           method: 'POST',

&#x20;           headers: { 'Content-Type': 'application/json' },

&#x20;           body: JSON.stringify(payload)

&#x20;       });

&#x20;   }

&#x20;   await loadSchedules();

&#x20;   renderDayFilters();

&#x20;   closeTaskModal();

}



function editSchedule(id) {

&#x20;   const s = schedules.find(item => item.id === id);

&#x20;   if (!s) return;

&#x20;   editSchedId = s.id;

&#x20;   document.getElementById('modalSubName').value  = s.subject;

&#x20;   document.getElementById('modalDaySelect').value = s.day;

&#x20;   document.getElementById('modalRoom').value     = s.room;

&#x20;   document.getElementById('taskModal').classList.remove('hidden');

}



// ── FOLDER MODAL (Create/Edit Class) ─────────────────────────────────────────



async function saveFolderModal() {

&#x20;   const subject = document.getElementById('modalSubject').value;

&#x20;   const section = document.getElementById('modalSection').value;

&#x20;   const year    = document.getElementById('modalYear').value;



&#x20;   // class id = "SUBJECT-SECTION-YEAR" format matching your schema

&#x20;   const class\_code = `${subject}-${section}-${year}`.replace(/\\s+/g, '-').toUpperCase();



&#x20;   if (editIdx > -1) {

&#x20;       // Edit existing class

&#x20;       const existing = classFolders\[editIdx];

&#x20;       await fetch(`/api/edit\_class/${existing.id}`, {

&#x20;           method: 'POST',

&#x20;           headers: { 'Content-Type': 'application/json' },

&#x20;           body: JSON.stringify({ course\_code: year, subject: subject, section: section })

&#x20;       });

&#x20;   } else {

&#x20;       // Create new class

&#x20;       await fetch('/api/create\_class', {

&#x20;           method: 'POST',

&#x20;           headers: { 'Content-Type': 'application/json' },

&#x20;           body: JSON.stringify({ id: class\_code, course\_code: year, subject: subject, section: section })

&#x20;       });

&#x20;   }



&#x20;   editIdx = -1;

&#x20;   showPage('classes');

&#x20;   closeClassModal();

}



function editFolder(class\_code) {

&#x20;   const f = classFolders.find(f => f.id === class\_code);

&#x20;   if (!f) return;

&#x20;   editIdx = classFolders.indexOf(f);

&#x20;   document.getElementById('modalSubject').value = f.subject;

&#x20;   document.getElementById('modalSection').value = f.section;

&#x20;   document.getElementById('modalYear').value    = f.course\_code;

&#x20;   document.getElementById('classModal').classList.remove('hidden');

}



// ── STUDENT REGISTRATION ──────────────────────────────────────────────────────



async function submitStudentForm(formEl) {

&#x20;   const formData = new FormData(formEl);

&#x20;   formData.append('class\_code', currentOpenedFolder);

&#x20;   try {

&#x20;       await fetch('/api/add\_student', { method: 'POST', body: formData });

&#x20;       closeRegModal();

&#x20;       openFolderView(currentOpenedFolder);

&#x20;   } catch {

&#x20;       alert('Failed to save student.');

&#x20;   }

}



// ── CAMERA ────────────────────────────────────────────────────────────────────

// Connects to Flask /video\_feed (MJPEG stream from facerecog.py)

// Polls /api/present\_students every 2 seconds for the recognition panel



let \_pollInterval = null;



function openCamera() {

&#x20;   document.getElementById('recognizedList').innerHTML = "";

&#x20;   document.getElementById('cameraModal').classList.remove('hidden');

&#x20;   document.getElementById('cameraLoading').classList.remove('hidden');

&#x20;   document.getElementById('dummyFeed').classList.add('hidden');



&#x20;   setTimeout(() => {

&#x20;       document.getElementById('cameraLoading').classList.add('hidden');



&#x20;       // Replace dummyFeed content with real MJPEG stream

&#x20;       const dummyFeed = document.getElementById('dummyFeed');

&#x20;       dummyFeed.classList.remove('hidden');

&#x20;       dummyFeed.innerHTML = `<img src="/video\_feed" style="width:100%; height:100%; object-fit:cover;">`;



&#x20;       // Poll present students every 2 seconds

&#x20;       \_pollInterval = setInterval(async () => {

&#x20;           try {

&#x20;               const res      = await fetch('/api/present\_students');

&#x20;               const students = await res.json();

&#x20;               const list     = document.getElementById('recognizedList');

&#x20;               list.innerHTML = students.map(name => `

&#x20;                   <div class="flex justify-between border-b pb-4">

&#x20;                       <div>

&#x20;                           <p class="text-sm font-black">${name}</p>

&#x20;                           <p class="text-\[9px] font-bold text-gray-400">${new Date().toLocaleTimeString(\[], {hour:'2-digit', minute:'2-digit'})}</p>

&#x20;                       </div>

&#x20;                       <span class="text-\[10px] font-black text-green-500 uppercase">Present</span>

&#x20;                   </div>`).join('');

&#x20;           } catch {}

&#x20;       }, 2000);

&#x20;   }, 2000);

}



function closeCamera() {

&#x20;   document.getElementById('cameraModal').classList.add('hidden');

&#x20;   if (\_pollInterval) { clearInterval(\_pollInterval); \_pollInterval = null; }

}



// Save attendance from camera panel

async function saveAttendanceFromCamera() {

&#x20;   if (!currentOpenedFolder) return;

&#x20;   const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};



&#x20;   try {

&#x20;       const res      = await fetch('/api/present\_students');

&#x20;       const present  = await res.json();



&#x20;       // Build all students list: present ones + mark rest as absent

&#x20;       const allRes  = await fetch(`/api/students/${currentOpenedFolder}`);

&#x20;       const allStud = await allRes.json();



&#x20;       const records = allStud.map(s => ({

&#x20;           name:      s.name,

&#x20;           sr\_code:   s.sr\_code || '',

&#x20;           status:    present.includes(s.name) ? 'Present' : 'Absent',

&#x20;           timestamp: present.includes(s.name) ? new Date().toTimeString().substring(0,8) : ''

&#x20;       }));



&#x20;       await fetch('/api/save\_attendance', {

&#x20;           method: 'POST',

&#x20;           headers: { 'Content-Type': 'application/json' },

&#x20;           body: JSON.stringify({

&#x20;               class\_code: currentOpenedFolder,

&#x20;               section:    cls.section || '',

&#x20;               subject:    cls.subject || '',

&#x20;               records:    records

&#x20;           })

&#x20;       });



&#x20;       closeCamera();

&#x20;       alert('Attendance saved!');

&#x20;   } catch {

&#x20;       alert('Failed to save attendance.');

&#x20;   }

}



// ── CONFIRM DIALOG (unchanged logic, updated backend calls) ───────────────────



function confirmAction(action, id) {

&#x20;   const modal = document.getElementById('customConfirm');

&#x20;   modal.classList.remove('hidden');

&#x20;   document.getElementById('confirmDesc').innerText = "Proceed with this action?";



&#x20;   document.getElementById('confirmBtn').onclick = async () => {

&#x20;       if (action === 'deleteFolder') {

&#x20;           await fetch(`/api/delete\_class/${id}`, { method: 'DELETE' });

&#x20;           showPage('classes');

&#x20;       } else if (action === 'deleteSubject') {

&#x20;           await fetch(`/api/schedules/${id}`, { method: 'DELETE' });

&#x20;           await loadSchedules();

&#x20;           renderDayFilters();

&#x20;       } else if (action === 'logout') {

&#x20;           localStorage.removeItem('active\_session');

&#x20;           window.location.href = "login.html";

&#x20;       }

&#x20;       closeConfirm();

&#x20;   };

}



function closeConfirm() { document.getElementById('customConfirm').classList.add('hidden'); }



// ── MODAL HELPERS (unchanged) ─────────────────────────────────────────────────



function openRegModal()    { document.getElementById('regModal').classList.remove('hidden'); }

function closeRegModal()   { document.getElementById('regModal').classList.add('hidden'); }

function closeClassModal() { document.getElementById('classModal').classList.add('hidden'); }

function closeTaskModal()  { editSchedId = -1; document.getElementById('taskModal').classList.add('hidden'); }

function openTaskModal()   { editSchedId = -1; document.getElementById('taskModal').classList.remove('hidden'); }

function openFolderModal() { editIdx = -1; document.getElementById('classModal').classList.remove('hidden'); }



// ── SIDEBAR TOGGLE (unchanged) ────────────────────────────────────────────────



function toggleMiniSidebar() {

&#x20;   const sidebar = document.getElementById('navSidebar');

&#x20;   const icon    = document.getElementById('toggleIcon');

&#x20;   sidebar.classList.toggle('nav-collapsed');

&#x20;   icon.setAttribute('data-lucide', sidebar.classList.contains('nav-collapsed') ? 'chevron-right' : 'chevron-left');

&#x20;   lucide.createIcons();

}



// ── DOCUMENT VIEWER (unchanged — now uses real PDF) ───────────────────────────



function openRealDoc(class\_code, date) {

&#x20;   window.open(`/api/download\_pdf/${class\_code}/${date}`, '\_blank');

}





=================================================================================================================================



index.html - issue - issue - student submission not working



<!DOCTYPE html>

<html lang="en">

<head>

&#x20;   <meta charset="UTF-8">

&#x20;   <meta name="viewport" content="width=device-width, initial-scale=1.0">

&#x20;   <title>Attendance Monitoring System</title>

&#x20;   <script src="https://cdn.tailwindcss.com"></script>

&#x20;   <script src="https://unpkg.com/lucide@0.321.0"></script>

&#x20;   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

&#x20;   <link rel="stylesheet" href="style.css">

</head>

<body class="flex h-screen overflow-hidden bg-\[#FDFDFD]">



&#x20;   <aside id="navSidebar" class="w-64 bg-white border-r border-gray-100 flex flex-col transition-all duration-300 relative">

&#x20;       

&#x20;       <button onclick="toggleMiniSidebar()" class="absolute -right-3 top-9 z-50 bg-white border border-gray-100 rounded-full p-1 shadow-sm hover:bg-red-50 text-\[#D32F2F]">

&#x20;           <i data-lucide="chevron-left" class="w-4 h-4" id="toggleIcon"></i>

&#x20;       </button>



&#x20;       <div class="p-8 mb-4">

&#x20;           <div class="flex items-center space-x-2 mb-10">

&#x20;               <div class="w-8 h-8 bg-\[#D32F2F] rounded-lg flex-shrink-0 flex items-center justify-center text-white shadow-md">

&#x20;                   <i data-lucide="shield-check" class="w-5 h-5"></i>

&#x20;               </div>

&#x20;               <h1 class="nav-label font-black text-xl tracking-tighter text-\[#D32F2F]">ATTENDANCE</h1>

&#x20;           </div>

&#x20;           

&#x20;           <nav class="space-y-1">

&#x20;               <button onclick="showPage('home', this)" class="nav-btn w-full flex items-center space-x-3 p-3 rounded-xl text-gray-500 hover:bg-red-50 hover:text-\[#D32F2F] transition sidebar-active">

&#x20;                   <i data-lucide="layout-dashboard" class="w-5 h-5 flex-shrink-0"></i> 

&#x20;                   <span class="nav-label font-bold text-sm">Dashboard</span> 

&#x20;               </button>



&#x20;               <button onclick="showPage('classes', this)" class="nav-btn w-full flex items-center space-x-3 p-3 rounded-xl text-gray-500 hover:bg-red-50 hover:text-\[#D32F2F] transition">

&#x20;                   <i data-lucide="layers" class="w-5 h-5 flex-shrink-0"></i> 

&#x20;                   <span class="nav-label font-bold text-sm">Classes</span> 

&#x20;               </button>



&#x20;               <button onclick="showPage('history', this)" class="nav-btn w-full flex items-center space-x-3 p-3 rounded-xl text-gray-500 hover:bg-red-50 hover:text-\[#D32F2F] transition">

&#x20;                   <i data-lucide="archive" class="w-5 h-5 flex-shrink-0"></i> 

&#x20;                   <span class="nav-label font-bold text-sm">History</span> 

&#x20;               </button>

&#x20;           </nav>

&#x20;       </div>

&#x20;       

&#x20;       <div class="mt-auto p-6 border-t border-gray-50 bg-gray-50/50">

&#x20;           <div class="flex items-center space-x-3 mb-6">

&#x20;               <div id="user-initials" class="w-10 h-10 flex-shrink-0 bg-\[#D32F2F] rounded-full flex items-center justify-center text-white font-bold text-xs shadow-lg">JP</div>

&#x20;               <div class="nav-label min-w-0">

&#x20;                   <p id="user-display-email" class="text-xs font-bold truncate"><a href="/cdn-cgi/l/email-protection" class="\_\_cf\_email\_\_" data-cfemail="2e445e6e49434f4742004d4143">\[email\&#160;protected]</a></p>

&#x20;                   <p class="text-\[9px] text-gray-400 truncate uppercase font-black tracking-widest">Instructor</p>

&#x20;               </div>

&#x20;           </div>

&#x20;           <button onclick="confirmAction('logout')" class="w-full flex items-center space-x-3 p-2 text-gray-400 hover:text-red-600 transition text-xs font-bold">

&#x20;               <i data-lucide="log-out" class="w-4 h-4 flex-shrink-0"></i> 

&#x20;               <span class="nav-label">Sign Out</span>

&#x20;           </button>

&#x20;       </div>

&#x20;   </aside>



&#x20;   <main class="flex-1 flex flex-col min-w-0 bg-white shadow-2xl overflow-y-auto">

&#x20;       <div id="content-area" class="p-12 h-full"></div>

&#x20;   </main>



&#x20;   <aside class="w-80 p-8 flex flex-col bg-\[#FDFDFD] border-l border-gray-50"> 

&#x20;       <div class="mb-10 text-right">

&#x20;           <h1 id="clock" class="text-4xl font-black text-\[#D32F2F] tracking-tighter">00:00:00 AM</h1>

&#x20;           <p id="date" class="text-gray-400 text-\[10px] uppercase font-bold tracking-widest mt-1">Loading...</p>

&#x20;       </div>

&#x20;       <div id="day-filters" class="flex flex-wrap gap-2 mb-6"></div>

&#x20;       <div class="flex-1 overflow-y-auto pr-2 scroll-hide">

&#x20;           <h3 class="font-black text-\[10px] uppercase tracking-\[0.2em] text-gray-400 mb-4">Daily Schedule</h3>

&#x20;           <div id="schedule-list" class="space-y-3"></div>

&#x20;       </div>

&#x20;       <button onclick="openTaskModal()" class="mt-8 w-full bg-\[#D32F2F] text-white font-bold py-4 rounded-2xl shadow-xl hover:bg-\[#B71C1C] transition flex items-center justify-center space-x-2">

&#x20;           <i data-lucide="plus-circle" class="w-5 h-5"></i> <span>Add Schedule</span>

&#x20;       </button>

&#x20;   </aside>



&#x20;   <div id="cameraModal" class="hidden fixed inset-0 bg-black/80 backdrop-blur-xl z-\[101] flex items-center justify-center p-4">

&#x20;       <div class="bg-white rounded-\[3rem] w-full max-w-\[95vw] overflow-hidden shadow-2xl flex flex-col h-\[90vh]">

&#x20;           <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-white">

&#x20;               <div class="flex items-center space-x-3">

&#x20;                   <div id="camStatusDot" class="w-3 h-3 bg-red-500 rounded-full"></div>

&#x20;                   <span id="camStatusText" class="text-\[10px] font-black uppercase tracking-widest text-gray-400">Live Scanning System</span>

&#x20;               </div>

&#x20;               <button onclick="closeCamera()" class="p-2 hover:bg-gray-50 rounded-full transition"><i data-lucide="x" class="text-gray-400"></i></button>

&#x20;           </div>

&#x20;           <div class="flex flex-1 overflow-hidden">

&#x20;               <div id="cameraMainArea" class="flex-\[4] bg-gray-900 flex flex-col items-center justify-center relative border-r border-gray-100">

&#x20;                   <div class="scan-line"></div>

&#x20;                   <div id="cameraLoading" class="flex flex-col items-center justify-center text-center">

&#x20;                       <div class="w-20 h-20 border-4 border-t-\[#D32F2F] border-gray-800 rounded-full animate-spin mb-6"></div>

&#x20;                       <h3 class="text-white font-bold text-lg mb-2">Initializing Camera...</h3>

&#x20;                   </div>

&#x20;                   <div id="dummyFeed" class="hidden w-full h-full bg-black relative">

&#x20;                       <div class="absolute inset-0 flex items-center justify-center"><i data-lucide="user" class="text-white/10 w-48 h-48"></i></div>

&#x20;                       <p class="absolute bottom-5 left-5 text-red-500 font-mono text-xs bg-black/50 p-2 italic">LIVE FEED :: SCANNING ACTIVE...</p>

&#x20;                   </div>

&#x20;               </div>

&#x20;               <div id="cameraSideArea" class="flex-1 bg-white p-8 flex flex-col overflow-y-auto">

&#x20;                   <div class="mb-6">

&#x20;                       <h2 class="text-2xl font-black text-gray-900">Detection</h2>

&#x20;                       <div class="flex gap-2 mt-2">

&#x20;                           <span id="presentCount" class="bg-green-100 text-green-600 text-\[9px] font-black px-2 py-1 rounded">PRESENT: 0</span>

&#x20;                       </div>

&#x20;                       <button onclick="saveAttendanceFromCamera()" class="mt-4 w-full bg-\[#D32F2F] text-white font-bold py-3 rounded-xl text-xs hover:bg-\[#B71C1C] transition">

&#x20;                           Save Attendance

&#x20;                       </button>

&#x20;                   </div>

&#x20;                   <p class="text-\[10px] font-bold text-gray-400 uppercase tracking-widest mb-4 border-b pb-2">Logs</p>

&#x20;                   <div id="recognizedList" class="space-y-4"></div>

&#x20;               </div>

&#x20;           </div>

&#x20;       </div>

&#x20;   </div>



&#x20;   <div id="regModal" class="hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-\[110] flex items-center justify-center p-4">

&#x20;       <form id="studentRegForm" onsubmit="event.preventDefault(); submitStudentForm(this)" class="bg-white rounded-\[2.5rem] w-full max-w-lg p-8 shadow-2xl max-h-\[90vh] overflow-y-auto" enctype="multipart/form-data">

&#x20;           <h2 class="text-2xl font-black text-\[#D32F2F] mb-6 tracking-tighter">Student Registration</h2>

&#x20;           <div class="grid grid-cols-2 gap-4">

&#x20;               <input type="text" placeholder="Class ID" class="reg-input col-span-2" required>

&#x20;               <input type="text" placeholder="Full Name" class="reg-input col-span-2" required>

&#x20;               <input type="text" placeholder="SR Code" class="reg-input" required>

&#x20;               <input type="number" placeholder="Age" class="reg-input" required> 

&#x20;               <input type="text" placeholder="Contact Number" class="reg-input col-span-2" required> 

&#x20;               <input type="text" placeholder="Address" class="reg-input col-span-2" required> 

&#x20;               <input type="email" placeholder="Email Address" class="reg-input col-span-2" required>

&#x20;               <div class="col-span-1">

&#x20;                   <p class="text-\[10px] font-bold text-gray-400 uppercase mb-2">Student Photo</p>

&#x20;                   <input type="file" class="text-\[10px] font-bold text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-\[10px] file:font-black file:bg-red-50 file:text-\[#D32F2F]">

&#x20;               </div>

&#x20;               <div class="col-span-1">

&#x20;                   <p class="text-\[10px] font-bold text-gray-400 uppercase mb-2">E-Signature</p>

&#x20;                   <input type="file" class="text-\[10px] font-bold text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-\[10px] file:font-black file:bg-gray-100 file:text-gray-600">

&#x20;               </div>

&#x20;           </div>

&#x20;           <div class="flex space-x-3 mt-8">

&#x20;               <button type="button" onclick="closeRegModal()" class="flex-1 py-4 text-gray-400 font-bold">Cancel</button>

&#x20;               <button type="submit" class="flex-1 py-4 bg-\[#D32F2F] text-white font-bold rounded-xl shadow-lg">Submit</button>

&#x20;           </div>

&#x20;       </form>

&#x20;   </div>



&#x20;   <div id="classModal" class="hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-\[150] flex items-center justify-center p-4">

&#x20;       <form onsubmit="event.preventDefault(); saveFolderModal()" class="bg-white rounded-\[2.5rem] w-full max-w-sm p-8 shadow-2xl">

&#x20;           <h2 id="folderModalTitle" class="text-2xl font-black text-\[#D32F2F] mb-6 tracking-tighter">Manage Folder</h2>

&#x20;           <div class="space-y-4">

&#x20;               <input type="text" id="modalSubject" placeholder="Subject Name" class="reg-input" required>

&#x20;               <input type="text" id="modalSection" placeholder="Section" class="reg-input" required>

&#x20;               <input type="text" id="modalYear" placeholder="Year Level" class="reg-input" required>

&#x20;           </div>

&#x20;           <div class="flex space-x-3 mt-8">

&#x20;               <button type="button" onclick="closeClassModal()" class="flex-1 py-4 text-gray-400 font-bold">Cancel</button>

&#x20;               <button type="submit" class="flex-1 py-4 bg-\[#D32F2F] text-white font-bold rounded-xl shadow-lg">Save</button>

&#x20;           </div>

&#x20;       </form>

&#x20;   </div>



&#x20;   <div id="taskModal" class="hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-\[150] flex items-center justify-center p-4">

&#x20;       <form onsubmit="event.preventDefault(); saveSubject()" class="bg-white rounded-\[2.5rem] w-full max-w-md p-8 shadow-2xl">

&#x20;           <h2 id="taskModalTitle" class="text-2xl font-black text-gray-900 mb-6 tracking-tighter">Schedule Entry</h2>

&#x20;           <div class="space-y-4">

&#x20;               <input type="text" id="modalSubName" placeholder="Subject Name" class="reg-input" required>

&#x20;               <div class="grid grid-cols-2 gap-4">

&#x20;                   <select id="modalDaySelect" class="reg-input">

&#x20;                       <option value="MON">Monday</option>

&#x20;                       <option value="TUE">Tuesday</option>

&#x20;                       <option value="WED">Wednesday</option>

&#x20;                       <option value="THU">Thursday</option>

&#x20;                       <option value="FRI">Friday</option>

&#x20;                       <option value="SAT">Saturday</option>

&#x20;                       <option value="SUN">Sunday</option>

&#x20;                   </select>

&#x20;                   <input type="text" id="modalRoom" placeholder="Room" class="reg-input">

&#x20;               </div>

&#x20;               <div class="grid grid-cols-2 gap-4">

&#x20;                   <select id="modalTimeFrom" class="reg-input"></select>

&#x20;                   <select id="modalTimeTo" class="reg-input"></select>

&#x20;               </div>

&#x20;           </div>

&#x20;           <div class="flex space-x-3 mt-8">

&#x20;               <button type="button" onclick="closeTaskModal()" class="flex-1 py-4 text-gray-400 font-bold">Cancel</button>

&#x20;               <button type="submit" class="flex-1 py-4 bg-\[#D32F2F] text-white font-bold rounded-xl shadow-lg">Confirm</button>

&#x20;           </div>

&#x20;       </form>

&#x20;   </div>



&#x20;   <div id="customConfirm" class="hidden fixed inset-0 bg-black/60 backdrop-blur-md z-\[200] flex items-center justify-center p-4">

&#x20;       <div class="bg-white p-8 rounded-\[2rem] w-full max-w-xs text-center shadow-2xl">

&#x20;           <h3 class="font-black text-xl mb-2">Are you sure?</h3>

&#x20;           <p id="confirmDesc" class="text-gray-400 text-sm mb-8">This action cannot be undone.</p>

&#x20;           <div class="flex space-x-3">

&#x20;               <button onclick="closeConfirm()" class="flex-1 py-3 text-gray-400 font-bold">No</button>

&#x20;               <button id="confirmBtn" class="flex-1 py-3 bg-red-600 text-white rounded-xl font-bold">Yes</button>

&#x20;           </div>

&#x20;       </div>

&#x20;   </div>



&#x20;   <div id="docViewer" class="hidden fixed inset-0 bg-black/90 backdrop-blur-xl z-\[300] flex items-center justify-center p-10">

&#x20;       <div class="bg-white w-full max-w-4xl h-full rounded-\[3rem] overflow-hidden flex flex-col print-container">

&#x20;           <div class="p-6 border-b flex justify-between items-center bg-white print-hide">

&#x20;               <h3 id="docTitle" class="font-black text-\[#D32F2F] uppercase tracking-tighter">Document View</h3>

&#x20;               <div class="flex items-center space-x-2">

&#x20;                   <button onclick="window.print()" class="flex items-center space-x-2 px-4 py-2 bg-red-50 text-\[#D32F2F] rounded-xl font-bold text-xs hover:bg-red-100 transition">

&#x20;                       <i data-lucide="printer" class="w-4 h-4"></i> <span>Print</span>

&#x20;                   </button>

&#x20;                   <button onclick="document.getElementById('docViewer').classList.add('hidden')" class="p-2 bg-gray-100 rounded-full hover:bg-gray-200 transition"><i data-lucide="x"></i></button>

&#x20;               </div>

&#x20;           </div>

&#x20;           <div id="printArea" class="flex-1 bg-gray-50 p-12 overflow-y-auto">

&#x20;               <div class="max-w-2xl mx-auto bg-white shadow-sm border p-12 min-h-\[800px]">

&#x20;                   <h1 class="text-center font-bold text-xl mb-10 underline">ATTENDANCE LOG REPORT</h1>

&#x20;                   <table class="w-full text-left text-xs">

&#x20;                       <thead class="border-b-2 border-black">

&#x20;                           <tr><th class="py-2">STUDENT NAME</th><th class="py-2">TIME IN</th><th class="py-2">STATUS</th></tr>

&#x20;                       </thead>

&#x20;                       <tbody id="dummyTable"></tbody>

&#x20;                   </table>

             
============================================================================================================================

Database (unique)

"""
database.py
============
PostgreSQL database layer for the Attendance Monitoring System.
Matches the updated schema:
    classes    — id (VARCHAR), course_code, subject, section
    students   — sr_code (UNIQUE), class_code (FK), sex added
    attendance — sr_code (FK to students), class_code (FK)
    schedules  — class_code (FK)

Requirements:
    pip install psycopg2-binary

Update DB_CONFIG below to match your PostgreSQL setup.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime


# ── CONNECTION CONFIG ─────────────────────────────────────────────────────────
# Change these to match your PostgreSQL / pgAdmin setup

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "attendance_db",   # create this in pgAdmin first
    "user":     "postgres",
    "password": "yourpassword",    # your pgAdmin password
}


# ── CONNECTION ────────────────────────────────────────────────────────────────

def get_db():
    """Returns a PostgreSQL connection."""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def get_cursor(conn):
    """
    Returns a DictCursor — rows behave like dicts: row["name"]
    Same feel as SQLite's row_factory = sqlite3.Row.
    """
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    """Creates all tables if they don't exist. Called once on app startup."""
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id           VARCHAR(50)  PRIMARY KEY,
            course_code  VARCHAR(20)  NOT NULL,
            subject      VARCHAR(50),
            section      VARCHAR(50),
            created      DATE DEFAULT CURRENT_DATE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name       VARCHAR(50)  NOT NULL,
            address    VARCHAR(100),
            number     VARCHAR(50),
            sr_code    VARCHAR(50),
            age        INTEGER,
            sex        VARCHAR(10),
            email      VARCHAR(100),
            photo      TEXT,
            signature  TEXT,
            UNIQUE (class_code, sr_code)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code     VARCHAR(50),
            name        VARCHAR(50)  NOT NULL,
            section     VARCHAR(50),
            subject     VARCHAR(50),
            status      VARCHAR(20)  NOT NULL,
            timestamp   TIMESTAMP(0) DEFAULT NOW(),
            date        DATE         NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
            time        VARCHAR(50),
            subject     VARCHAR(50),
            room        VARCHAR(50)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email    VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            status   VARCHAR(20) DEFAULT 'pending'
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] PostgreSQL tables ready.")


# ── CLASSES ───────────────────────────────────────────────────────────────────

def get_all_classes():
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes ORDER BY created DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_class(class_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes WHERE id = %s", (class_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row




def create_class(class_code, course_code, subject, section):
    """
    class_code  = teacher-defined unique ID  e.g. "CPET-3201-2026"
    course_code = e.g. "CPT-113"
    subject     = e.g. "Computer Programming"
    section     = e.g. "CPET-3201"
    created     = auto-set to today's date
    """
    conn    = get_db()
    cur     = get_cursor(conn)
    created = datetime.now().strftime("%Y-%m-%d")
    cur.execute(
        """INSERT INTO classes (id, course_code, subject, section, created)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (id) DO NOTHING""",
        (class_code, course_code, subject, section, created)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_class(class_code, course_code, subject, section):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE classes
           SET course_code=%s, subject=%s, section=%s
           WHERE id=%s""",
        (course_code, subject, section, class_code)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_class(class_code):
    """Deletes class + cascades to students, attendance, schedules."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM classes WHERE id = %s", (class_code,))
    conn.commit()
    cur.close(); conn.close()


# ── STUDENTS ──────────────────────────────────────────────────────────────────

def get_students(class_code):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "SELECT * FROM students WHERE class_code = %s ORDER BY name",
        (class_code,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_student(student_db_id):
    """Get one student by their auto-increment id."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM students WHERE id = %s", (student_db_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def get_student_by_srcode(sr_code):
    """Get one student by their SR code (unique student number)."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM students WHERE sr_code = %s", (sr_code,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def add_student(class_code, name, address, number,
                sr_code, age, sex, email, photo, signature):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """INSERT INTO students
           (class_code, name, address, number,
            sr_code, age, sex, email, photo, signature)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (class_code, name, address, number,
         sr_code, age, sex, email, photo, signature)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_student(student_db_id, name, address, number,
                 sr_code, age, sex, email):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE students
           SET name=%s, address=%s, number=%s,
               sr_code=%s, age=%s, sex=%s, email=%s
           WHERE id=%s""",
        (name, address, number, sr_code, age, sex, email, student_db_id)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_student(student_db_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM students WHERE id = %s", (student_db_id,))
    conn.commit()
    cur.close(); conn.close()


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

def save_attendance(class_code, section, subject, records, date=None):
    """
    records = list of dicts:
        [
            {"name": "JohnDoe", "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            ...
        ]
    Deletes existing records for this class+date before inserting
    so the teacher can re-save without duplicates.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cur  = get_cursor(conn)

    # Remove existing records for this session (allow re-save)
    cur.execute(
        "DELETE FROM attendance WHERE class_code = %s AND date = %s",
        (class_code, date)
    )

    for r in records:
        # Build full timestamp: combine date + scan time from camera
        # e.g. date="2026-03-16", timestamp="07:02:34" → "2026-03-16 07:02:34"
        scan_time      = r.get("timestamp", "")
        full_timestamp = f"{date} {scan_time}" if scan_time else None

        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject, status, timestamp, date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                class_code,
                r.get("sr_code", ""),
                r["name"],
                section,
                subject,
                r["status"],
                full_timestamp,   # "2026-03-16 07:02:34" — actual scan time
                date
            )
        )

    conn.commit()
    cur.close(); conn.close()


def get_attendance_session(class_code, date):
    """All attendance rows for one class on one date, sorted Present→Late→Absent."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT * FROM attendance
           WHERE class_code = %s AND date = %s
           ORDER BY
             CASE status
               WHEN 'Present' THEN 1
               WHEN 'Late'    THEN 2
               WHEN 'Absent'  THEN 3
             END,
             name""",
        (class_code, date)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_all_sessions():
    """One row per (class_code, date) — for the History page list."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               a.class_code,
               a.date,
               a.section,
               a.subject,
               COUNT(*)                                          AS total,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
               SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
           FROM attendance a
           GROUP BY a.class_code, a.date, a.section, a.subject
           ORDER BY a.date DESC"""
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_recent_activity(limit=10):
    """Most recent sessions for the dashboard Recent Activities list."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               class_code,
               date,
               section,
               subject,
               MIN(timestamp::text) AS time
           FROM attendance
           GROUP BY class_code, date, section, subject
           ORDER BY date DESC, time DESC
           LIMIT %s""",
        (limit,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_absence_counts():
    """Students with at least one absence — for the dashboard chart."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT name, COUNT(*) AS count
           FROM attendance
           WHERE status = 'Absent'
           GROUP BY name
           ORDER BY count DESC"""
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"name": r["name"], "count": r["count"]} for r in rows]


# ── SCHEDULES ─────────────────────────────────────────────────────────────────

def get_schedules(class_code=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if class_code:
        cur.execute(
            "SELECT * FROM schedules WHERE class_code = %s ORDER BY id",
            (class_code,)
        )
    else:
        cur.execute("SELECT * FROM schedules ORDER BY id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def add_schedule(class_code, time, subject, room):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "INSERT INTO schedules (class_code, time, subject, room) VALUES (%s,%s,%s,%s)",
        (class_code, time, subject, room)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_schedule(schedule_id, time, subject, room):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "UPDATE schedules SET time=%s, subject=%s, room=%s WHERE id=%s",
        (time, subject, room, schedule_id)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_schedule(schedule_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
    conn.commit()
    cur.close(); conn.close()


# ── INSTRUCTORS ───────────────────────────────────────────────────────────────

def get_all_instructors():
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT id, email, status FROM instructors ORDER BY id")
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def get_instructor_by_email(email):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM instructors WHERE email = %s", (email,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def register_instructor(email, password):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "INSERT INTO instructors (email, password, status) VALUES (%s, %s, %s)",
        (email, password, 'pending')
    )
    conn.commit(); cur.close(); conn.close()

def approve_instructor(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("UPDATE instructors SET status='approved' WHERE id=%s", (instructor_id,))
    conn.commit(); cur.close(); conn.close()

def delete_instructor(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("DELETE FROM instructors WHERE id=%s", (instructor_id,))
    conn.commit(); cur.close(); conn.close()


================================================================================================================================

API - app.py (unique issue)

"""
app.py
=======
Main Flask backend — updated to match new PostgreSQL schema.
Fields changed:
    student_id  →  sr_code
    class_id    →  class_code  (VARCHAR, not INTEGER)
    sex         →  added to students

Run:
    python app.py

Then open:
    http://localhost:5000
"""

import os
import shutil
from datetime import datetime
from flask import ( 
    Flask, request,
    jsonify, send_file, Response
)
from werkzeug.utils import secure_filename

import database as db
from pdf_generator import generate_attendance_pdf
from face_recognition_a import FaceRecognizer, load_known_faces

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

for folder in ["uploads/students", "uploads/signatures", "faces", "pdf"]:
    os.makedirs(folder, exist_ok=True)

# ── FACE RECOGNITION ──────────────────────────────────────────────────────────

known_enc, known_names = load_known_faces("faces")
recognizer = FaceRecognizer(known_enc, known_names)
_camera_started = False


def start_camera(source=0):
    global _camera_started
    if not _camera_started:
        recognizer.start(source)
        _camera_started = True


def reload_recognizer():
    global known_enc, known_names, recognizer, _camera_started
    known_enc, known_names = load_known_faces("faces")
    recognizer             = FaceRecognizer(known_enc, known_names)
    _camera_started        = False


# ── HELPERS ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return ("." in filename and
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)




# ── INIT ──────────────────────────────────────────────────────────────────────

db.init_db()


# ════════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — single page app, script.js handles all navigation
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_file("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204   # no content — silences browser favicon request


# ════════════════════════════════════════════════════════════════════════════════
# API — CLASSES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/create_class", methods=["POST"])
def api_create_class():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    required = ["id", "course_code", "subject", "section"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    db.create_class(
        class_code  = data["id"],
        course_code = data["course_code"],
        subject     = data["subject"],
        section     = data["section"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/edit_class/<class_code>", methods=["POST"])
def api_edit_class(class_code):
    data = request.json
    db.edit_class(
        class_code,
        course_code = data["course_code"],
        subject     = data["subject"],
        section     = data["section"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/delete_class/<class_code>", methods=["DELETE"])
def api_delete_class(class_code):
    db.delete_class(class_code)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/add_student", methods=["POST"])
def api_add_student():
    form       = request.form
    class_code = form.get("class_code", "").strip()
    name       = form.get("name", "").strip()

    if not class_code or not name:
        return jsonify({"error": "class_code and name required"}), 400

    # Save profile photo → uploads/students/ and faces/
    photo_path = ""
    if "photo" in request.files:
        f = request.files["photo"]
        if f and allowed_file(f.filename):
            ext        = os.path.splitext(secure_filename(f.filename))[1]
            safe_name  = secure_filename(name + ext)
            photo_path = os.path.join("uploads/students", safe_name)
            f.save(photo_path)
            # Copy to faces/ so recognizer can detect this student
            shutil.copy(photo_path, os.path.join("faces", safe_name))
            reload_recognizer()

    # Save signature
    sig_path = ""
    if "signature" in request.files:
        f = request.files["signature"]
        if f and allowed_file(f.filename):
            fname    = secure_filename(f.filename)
            sig_path = os.path.join("uploads/signatures", fname)
            f.save(sig_path)

    db.add_student(
        class_code = class_code,
        name       = name,
        address    = form.get("address", ""),
        number     = form.get("number", ""),
        sr_code    = form.get("sr_code", ""),
        age        = int(form.get("age") or 0),
        sex        = form.get("sex", ""),
        email      = form.get("email", ""),
        photo      = photo_path,
        signature  = sig_path,
    )
    return jsonify({"status": "ok"})


@app.route("/api/edit_student/<int:student_id>", methods=["POST"])
def api_edit_student(student_id):
    form = request.form
    db.edit_student(
        student_id,
        name    = form.get("name", ""),
        address = form.get("address", ""),
        number  = form.get("number", ""),
        sr_code = form.get("sr_code", ""),
        age     = int(form.get("age") or 0),
        sex     = form.get("sex", ""),
        email   = form.get("email", ""),
    )
    return jsonify({"status": "ok"})


@app.route("/api/delete_student/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    db.delete_student(student_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — CAMERA / ATTENDANCE
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/video_feed")
def video_feed():
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/present_students")
def api_present_students():
    return jsonify(recognizer.get_present_students())


@app.route("/api/save_attendance", methods=["POST"])
def api_save_attendance():
    """
    Body JSON:
    {
        "class_code": "CPET-3201-2026",
        "section":    "CPET-3201",
        "subject":    "CPT-113",
        "records": [
            {"name": "JohnDoe",   "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            {"name": "AnnaSmith", "sr_code": "2021-0002",
             "status": "Late",    "timestamp": "07:15:10"},
            {"name": "MarkLee",   "sr_code": "2021-0003",
             "status": "Absent",  "timestamp": ""}
        ]
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    db.save_attendance(
        class_code = data["class_code"],
        section    = data["section"],
        subject    = data["subject"],
        records    = data["records"],
    )
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})


@app.route("/api/reset_attendance", methods=["POST"])
def api_reset_attendance():
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/recent")
def api_recent():
    rows = db.get_recent_activity(limit=10)
    return jsonify([dict(r) for r in rows])


@app.route("/api/absences")
def api_absences():
    return jsonify(db.get_absence_counts())


# ════════════════════════════════════════════════════════════════════════════════
# API — SCHEDULES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/schedules", methods=["GET"])
def api_get_schedules():
    return jsonify([dict(r) for r in db.get_schedules()])


@app.route("/api/schedules", methods=["POST"])
def api_add_schedule():
    data = request.json
    db.add_schedule(
        class_code = data.get("class_code", ""),
        time       = data["time"],
        subject    = data["subject"],
        room       = data["room"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["POST"])
def api_edit_schedule(schedule_id):
    data = request.json
    db.edit_schedule(schedule_id, data["time"], data["subject"], data["room"])
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def api_delete_schedule(schedule_id):
    db.delete_schedule(schedule_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# PDF DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/download_pdf/<class_code>/<date>")
def api_download_pdf(class_code, date):
    cls     = db.get_class(class_code)
    records = db.get_attendance_session(class_code, date)

    if not cls:
        return jsonify({"error": "class not found"}), 404

    schedules = db.get_schedules(class_code)
    room      = schedules[0]["room"] if schedules else "TBA"

    filepath = generate_attendance_pdf(
        class_id = class_code,
        subject  = cls["subject"],
        section  = cls["section"],
        room     = room,
        date     = date,
        records  = records,
    )

    return send_file(
        filepath,
        as_attachment=True,
        download_name=os.path.basename(filepath),
        mimetype="application/pdf"
    )



# ════════════════════════════════════════════════════════════════════════════════
# API — CLASSES LIST (for script.js renderFolderPage)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/classes", methods=["GET"])
def api_get_classes():
    rows = db.get_all_classes()
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — SESSIONS LIST (for script.js renderHistoryPage)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/sessions", methods=["GET"])
def api_get_sessions():
    rows = db.get_all_sessions()
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — ATTENDANCE RECORDS FOR ONE SESSION
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/attendance/<class_code>/<date>", methods=["GET"])
def api_get_attendance(class_code, date):
    rows = db.get_attendance_session(class_code, date)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS LIST FOR A CLASS (for openFolderView)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/students/<class_code>", methods=["GET"])
def api_get_students(class_code):
    rows = db.get_students(class_code)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — LOGIN / REGISTER / ADMIN (for login.html + admin.html)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def api_login():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    user  = db.get_instructor_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["password"] != pwd:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["status"] == "pending":
        return jsonify({"error": "pending"}), 403
    return jsonify({"status": "ok", "email": user["email"]})


@app.route("/api/register", methods=["POST"])
def api_register():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    if not email or not pwd:
        return jsonify({"error": "Fill all fields."}), 400
    existing = db.get_instructor_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered."}), 409
    db.register_instructor(email, pwd)
    return jsonify({"status": "ok"})


@app.route("/api/instructors", methods=["GET"])
def api_get_instructors():
    rows = db.get_all_instructors()
    return jsonify([dict(r) for r in rows])


@app.route("/api/instructors/<int:instructor_id>/approve", methods=["POST"])
def api_approve_instructor(instructor_id):
    db.approve_instructor(instructor_id)
    return jsonify({"status": "ok"})


@app.route("/api/instructors/<int:instructor_id>", methods=["DELETE"])
def api_delete_instructor(instructor_id):
    db.delete_instructor(instructor_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# AUTH HTML PAGES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/login")
def login_page():
    return send_file("login.html")


@app.route("/admin")
def admin_page():
    return send_file("admin.html")

# ════════════════════════════════════════════════════════════════════════════════
# RUN
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)


==================================================================================================================

the current database has a logic error where when creating account, their id is not link to the other tables. As a result, even tho multiple accounts are created only same class or student they will see. In order to fix this, the a foreighn key to the other table should be added for the private and own database of each of the instructors. Heres the added database

The problem was that classes and schedules had no instructor_id. This meant Instructor 1 and Instructor 2 could both create a class called GED-321-CPET3201 and they would literally be the same record — same students, same attendance, same schedule. Your scenario requires them to be completely separate.

-- 1. Add instructor_id to classes
ALTER TABLE classes ADD COLUMN instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE;

-- 2. Add instructor_id to schedules  
ALTER TABLE schedules ADD COLUMN instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE;

-- 3. attendance already links through class_code → classes → instructor_id
--    so attendance is covered automatically once classes has instructor_id


AND THIS

ALTER TABLE classes   ADD COLUMN IF NOT EXISTS instructor_id INTEGER REFERENCES instructors(id);
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS instructor_id INTEGER REFERENCES instructors(id);
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS day VARCHAR(10);

================================================================================================================

# this is the current scrpt.js without the proper organization of database

// =============================================================================
// script.js — CONNECTED TO FLASK BACKEND
// Structure is identical to your original.
// localStorage replaced with fetch() calls to app.py.
// HTML/CSS is untouched.
// =============================================================================

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
        const res  = await fetch('/api/absences');
        const data = await res.json();
        initChart(data);
    } catch {
        initChart([]);
    }

    // Load recent activity from backend
    try {
        const res     = await fetch('/api/recent');
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
        const res = await fetch('/api/classes');
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
        const res = await fetch('/api/sessions');
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
        const res     = await fetch(`/api/attendance/${class_code}/${date}`);
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
        const res      = await fetch(`/api/students/${class_code}`);
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
        const res = await fetch('/api/schedules');
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
        await fetch(`/api/schedules/${editSchedId}`, {
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

    // class id = "SUBJECT-SECTION-YEAR" format matching your schema
    const class_code = `${subject}-${section}-${year}`.replace(/\s+/g, '-').toUpperCase();

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
        await fetch('/api/create_class', {
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
        const res  = await fetch('/api/add_student', { method: 'POST', body: formData });
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
                const res      = await fetch('/api/present_students');
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
        const res      = await fetch('/api/present_students');
        const present  = await res.json();

        // Build all students list: present ones + mark rest as absent
        const allRes  = await fetch(`/api/students/${currentOpenedFolder}`);
        const allStud = await allRes.json();

        const records = allStud.map(s => ({
            name:      s.name,
            sr_code:   s.sr_code || '',
            status:    present.includes(s.name) ? 'Present' : 'Absent',
            timestamp: present.includes(s.name) ? new Date().toTimeString().substring(0,8) : ''
        }));

        await fetch('/api/save_attendance', {
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
            await fetch(`/api/schedules/${id}`, { method: 'DELETE' });
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
--------------------------------------------------------------------------------- 
# fixing area


# added code after "HTML/CSS is untouched."

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
--------------------------------------------------------------------------------------

# The authFetch() wrapper in script.js automatically attaches the logged-in instructor's email to every request. Flask reads it and filters database queries by that instructor — so when Instructor 1 opens Classes, they only see their own folders, and Instructor 2 sees only theirs.

# cleared

 # every fetch are replaced into authFetch to the rest (dashboard, classes(folder), History, folder view, schedule) in after " // Load absence chart data from backend in dashboard part"

\\dashboard
--------------------------------------------
const res  = await fetch('/api/absences');
const res     = await fetch('/api/recent');
\\classes
-----------------------------------------------
const res = await fetch('/api/classes');
\\history
-------------------------------------------
const res = await fetch('/api/sessions');
const res     = await fetch(`/api/attendance/${class_code}/${date}`);

\\folder view
----------------------------------------------
 const res      = await fetch(`/api/students/${class_code}`);

\\schedule
----------------------------------------------
 const res = await fetch('/api/schedules');
 await fetch(`/api/schedules/${editSchedId}`, {

\\FOLDER MODAL
----------------------------------------------
// class id = "SUBJECT-SECTION-YEAR" format matching your schema
    const class_code = `${subject}-${section}-${year}`.replace(/\s+/g, '-').toUpperCase();

 await fetch('/api/create_class', {

\\STUDENT REGISTRATION
----------------------------------------------

const res  = await fetch('/api/add_student', { method: 'POST', body: formData });

\\Cam
----------------------------------------------
const res      = await fetch('/api/present_students');

const res      = await fetch('/api/present_students');


const res      = await fetch('/api/present_students');

await fetch('/api/save_attendance', {


\\CONFIRM DIALOG
----------------------------------------------

 await fetch(`/api/schedules/${id}`, { method: 'DELETE' });


# replaced

 # every fetch are replaced into authFetch in try catch function to  the rest (dashboard, classes(folder), History, folder view, schedule) in after " // Load absence chart data from backend in dashboard part"

 \\dashboard
--------------------------------------------

const res  = await authFetch('/api/absences');
const res     = await authFetch('/api/recent');

\\classes(folder)
----------------------------------------------
 const res = await authFetch('/api/classes');

\\history
-------------------------------------------
const res = await authFetch('/api/sessions');
 const res     = await authFetch(`/api/attendance/${class_code}/${date}`);

\\folder view
----------------------------------------------
 const res      = await authFetch(`/api/students/${class_code}`);

\\schedule
----------------------------------------------
 const res = await authFetch('/api/schedules');
 await authFetch(`/api/schedules/${editSchedId}`, {

\\FOLDER MODAL
----------------------------------------------
 // class id includes instructor email prefix to ensure uniqueness across instructors
    const session    = JSON.parse(localStorage.getItem('active_session') || '{}');
    const prefix     = (session.email || 'INS').split('@')[0].toUpperCase().substring(0, 6);
    const class_code = `${prefix}-${subject}-${section}-${year}`.replace(/\s+/g, '-').toUpperCase();

    await authFetch('/api/create_class', {

\\STUDENT REGISTRATION
----------------------------------------------

const session = JSON.parse(localStorage.getItem('active_session') || '{}');
        const res  = await fetch('/api/add_student', {
            method: 'POST',
            body: formData,
            headers: { 'X-Instructor-Email': session.email || '' }
        });

\\Cam
----------------------------------------------
 const res      = await authFetch('/api/present_students');

const res      = await authFetch('/api/present_students');

const allRes  = await authFetch(`/api/students/${currentOpenedFolder}`);

await authFetch('/api/save_attendance', {


\\CONFIRM DIALOG
----------------------------------------------
await authFetch(`/api/schedules/${id}`, { method: 'DELETE' });


=================================================================================================================================

# this is the current app.py without the proper organization of database

"""
app.py
=======
Main Flask backend — updated to match new PostgreSQL schema.
Fields changed:
    student_id  →  sr_code
    class_id    →  class_code  (VARCHAR, not INTEGER)
    sex         →  added to students

Run:
    python app.py

Then open:
    http://localhost:5000
"""

import os
import shutil
from datetime import datetime
from flask import (
    Flask, request,
    jsonify, send_file, Response
)
from werkzeug.utils import secure_filename

import database as db
from pdf_generator import generate_attendance_pdf
from face_recognition_a import FaceRecognizer, load_known_faces

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

for folder in ["uploads/students", "uploads/signatures", "faces", "pdf"]:
    os.makedirs(folder, exist_ok=True)

# ── FACE RECOGNITION ──────────────────────────────────────────────────────────

known_enc, known_names = load_known_faces("faces")
recognizer = FaceRecognizer(known_enc, known_names)
_camera_started = False


def start_camera(source=0):
    global _camera_started
    if not _camera_started:
        recognizer.start(source)
        _camera_started = True


def reload_recognizer():
    global known_enc, known_names, recognizer, _camera_started
    known_enc, known_names = load_known_faces("faces")
    recognizer             = FaceRecognizer(known_enc, known_names)
    _camera_started        = False


# ── HELPERS ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return ("." in filename and
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)




# ── INIT ──────────────────────────────────────────────────────────────────────

db.init_db()


# ════════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — single page app, script.js handles all navigation
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_file("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204   # no content — silences browser favicon request


# ════════════════════════════════════════════════════════════════════════════════
# API — CLASSES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/create_class", methods=["POST"])
def api_create_class():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    required = ["id", "course_code", "subject", "section"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    db.create_class(
        class_code  = data["id"],
        course_code = data["course_code"],
        subject     = data["subject"],
        section     = data["section"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/edit_class/<class_code>", methods=["POST"])
def api_edit_class(class_code):
    data = request.json
    db.edit_class(
        class_code,
        course_code = data["course_code"],
        subject     = data["subject"],
        section     = data["section"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/delete_class/<class_code>", methods=["DELETE"])
def api_delete_class(class_code):
    db.delete_class(class_code)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/add_student", methods=["POST"])
def api_add_student():
    form       = request.form
    class_code = form.get("class_code", "").strip()
    name       = form.get("name", "").strip()

    if not class_code or not name:
        return jsonify({"error": "class_code and name required"}), 400

    # Save profile photo → uploads/students/ and faces/
    photo_path = ""
    if "photo" in request.files:
        f = request.files["photo"]
        if f and f.filename and allowed_file(f.filename):
            ext        = os.path.splitext(secure_filename(f.filename))[1]
            safe_name  = secure_filename(name + ext)
            photo_path = os.path.join("uploads/students", safe_name)
            f.save(photo_path)
            # Copy to faces/ only if not already there (same student, multiple classes)
            face_path = os.path.join("faces", safe_name)
            if not os.path.exists(face_path):
                shutil.copy(photo_path, face_path)
                reload_recognizer()
        elif not (f.filename if f else None):
            # No new photo — reuse existing if student already enrolled elsewhere
            existing = db.get_student_by_srcode(form.get("sr_code", ""))
            if existing and existing["photo"]:
                photo_path = existing["photo"]

    # Save signature
    sig_path = ""
    if "signature" in request.files:
        f = request.files["signature"]
        if f and f.filename and allowed_file(f.filename):
            fname    = secure_filename(f.filename)
            sig_path = os.path.join("uploads/signatures", fname)
            f.save(sig_path)

    db.add_student(
        class_code = class_code,
        name       = name,
        address    = form.get("address", ""),
        number     = form.get("number", ""),
        sr_code    = form.get("sr_code", ""),
        age        = int(form.get("age") or 0),
        sex        = form.get("sex", ""),
        email      = form.get("email", ""),
        photo      = photo_path,
        signature  = sig_path,
    )
    return jsonify({"status": "ok"})


@app.route("/api/edit_student/<int:student_id>", methods=["POST"])
def api_edit_student(student_id):
    form = request.form
    db.edit_student(
        student_id,
        name    = form.get("name", ""),
        address = form.get("address", ""),
        number  = form.get("number", ""),
        sr_code = form.get("sr_code", ""),
        age     = int(form.get("age") or 0),
        sex     = form.get("sex", ""),
        email   = form.get("email", ""),
    )
    return jsonify({"status": "ok"})


@app.route("/api/delete_student/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    db.delete_student(student_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — CAMERA / ATTENDANCE
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/video_feed")
def video_feed():
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/present_students")
def api_present_students():
    return jsonify(recognizer.get_present_students())


@app.route("/api/save_attendance", methods=["POST"])
def api_save_attendance():
    """
    Body JSON:
    {
        "class_code": "CPET-3201-2026",
        "section":    "CPET-3201",
        "subject":    "CPT-113",
        "records": [
            {"name": "JohnDoe",   "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            {"name": "AnnaSmith", "sr_code": "2021-0002",
             "status": "Late",    "timestamp": "07:15:10"},
            {"name": "MarkLee",   "sr_code": "2021-0003",
             "status": "Absent",  "timestamp": ""}
        ]
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    db.save_attendance(
        class_code = data["class_code"],
        section    = data["section"],
        subject    = data["subject"],
        records    = data["records"],
    )
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})


@app.route("/api/reset_attendance", methods=["POST"])
def api_reset_attendance():
    recognizer.reset_attendance()
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# API — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/recent")
def api_recent():
    rows = db.get_recent_activity(limit=10)
    return jsonify([dict(r) for r in rows])


@app.route("/api/absences")
def api_absences():
    return jsonify(db.get_absence_counts())


# ════════════════════════════════════════════════════════════════════════════════
# API — SCHEDULES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/schedules", methods=["GET"])
def api_get_schedules():
    return jsonify([dict(r) for r in db.get_schedules()])


@app.route("/api/schedules", methods=["POST"])
def api_add_schedule():
    data = request.json
    db.add_schedule(
        class_code = data.get("class_code", ""),
        time       = data["time"],
        subject    = data["subject"],
        room       = data["room"],
    )
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["POST"])
def api_edit_schedule(schedule_id):
    data = request.json
    db.edit_schedule(schedule_id, data["time"], data["subject"], data["room"])
    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def api_delete_schedule(schedule_id):
    db.delete_schedule(schedule_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# PDF DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/download_pdf/<class_code>/<date>")
def api_download_pdf(class_code, date):
    cls     = db.get_class(class_code)
    records = db.get_attendance_session(class_code, date)

    if not cls:
        return jsonify({"error": "class not found"}), 404

    schedules = db.get_schedules(class_code)
    room      = schedules[0]["room"] if schedules else "TBA"

    filepath = generate_attendance_pdf(
        class_id = class_code,
        subject  = cls["subject"],
        section  = cls["section"],
        room     = room,
        date     = date,
        records  = records,
    )

    return send_file(
        filepath,
        as_attachment=True,
        download_name=os.path.basename(filepath),
        mimetype="application/pdf"
    )



# ════════════════════════════════════════════════════════════════════════════════
# API — CLASSES LIST (for script.js renderFolderPage)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/classes", methods=["GET"])
def api_get_classes():
    rows = db.get_all_classes()
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — SESSIONS LIST (for script.js renderHistoryPage)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/sessions", methods=["GET"])
def api_get_sessions():
    rows = db.get_all_sessions()
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — ATTENDANCE RECORDS FOR ONE SESSION
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/attendance/<class_code>/<date>", methods=["GET"])
def api_get_attendance(class_code, date):
    rows = db.get_attendance_session(class_code, date)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — STUDENTS LIST FOR A CLASS (for openFolderView)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/students/<class_code>", methods=["GET"])
def api_get_students(class_code):
    rows = db.get_students(class_code)
    return jsonify([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════════════════════
# API — LOGIN / REGISTER / ADMIN (for login.html + admin.html)
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def api_login():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    user  = db.get_instructor_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["password"] != pwd:
        return jsonify({"error": "Invalid email or password."}), 401
    if user["status"] == "pending":
        return jsonify({"error": "pending"}), 403
    return jsonify({"status": "ok", "email": user["email"]})


@app.route("/api/register", methods=["POST"])
def api_register():
    data  = request.json
    email = data.get("email", "").strip()
    pwd   = data.get("password", "").strip()
    if not email or not pwd:
        return jsonify({"error": "Fill all fields."}), 400
    existing = db.get_instructor_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered."}), 409
    db.register_instructor(email, pwd)
    return jsonify({"status": "ok"})


@app.route("/api/instructors", methods=["GET"])
def api_get_instructors():
    rows = db.get_all_instructors()
    return jsonify([dict(r) for r in rows])


@app.route("/api/instructors/<int:instructor_id>/approve", methods=["POST"])
def api_approve_instructor(instructor_id):
    db.approve_instructor(instructor_id)
    return jsonify({"status": "ok"})


@app.route("/api/instructors/<int:instructor_id>", methods=["DELETE"])
def api_delete_instructor(instructor_id):
    db.delete_instructor(instructor_id)
    return jsonify({"status": "ok"})


# ════════════════════════════════════════════════════════════════════════════════
# AUTH HTML PAGES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/login")
def login_page():
    return send_file("login.html")


@app.route("/admin")
def admin_page():
    return send_file("admin.html")

# ════════════════════════════════════════════════════════════════════════════════
# RUN
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)

\\
-------------------------------------------------------------------------------
# fixing area


\\helpers
--------------------------------
# added this def

def get_current_instructor_id(req):
    """
    Reads instructor email from the Authorization header sent by script.js
    and returns their instructor id from the database.
    Returns None if not found.
    """
    email = req.headers.get("X-Instructor-Email", "")
    if not email:
        return None
    instructor = db.get_instructor_by_email(email)
    return instructor["id"] if instructor else None


\\API CLASSES - after return jsonify({"error": f"{field} is required"}), 400
------------------------------------------------
# removed

def get_current_instructor_id(req):
    """
    Reads instructor email from the Authorization header sent by script.js
    and returns their instructor id from the database.
    Returns None if not found.
    """
    email = req.headers.get("X-Instructor-Email", "")
    if not email:
        return None
    instructor = db.get_instructor_by_email(email)
    return instructor["id"] if instructor else None

# replaced

instructor_id = get_current_instructor_id(request)

class_code    = data["id"],
        course_code   = data["course_code"],
        subject       = data["subject"],
        section       = data["section"],
        instructor_id = instructor_id,


\\ API — SCHEDULES
---------------------------------------------------

# removed

return jsonify([dict(r) for r in db.get_schedules()])

data = request.json

class_code = data.get("class_code", ""),
        time       = data["time"],
        subject    = data["subject"],
        room       = data["room"],

# replaced

instructor_id = get_current_instructor_id(request)
    return jsonify([dict(r) for r in db.get_schedules(instructor_id=instructor_id)])

    data          = request.json
    instructor_id = get_current_instructor_id(request)

    class_code    = data.get("class_code", ""),
        instructor_id = instructor_id,
        time          = data["time"],
        subject       = data["subject"],
        room          = data["room"],
        day           = data.get("day", "MON"),



\\API — CLASSES LIST (for script.js renderFolderPage)
-------------------------------------------------

# removed
rows = db.get_all_classes()

# added

    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_classes(instructor_id=instructor_id)

================================================================================================================

# this is the current database.py without the proper organization of database

"""
database.py
============
PostgreSQL database layer for the Attendance Monitoring System.
Matches the updated schema:
    classes    — id (VARCHAR), course_code, subject, section
    students   — sr_code (UNIQUE), class_code (FK), sex added
    attendance — sr_code (FK to students), class_code (FK)
    schedules  — class_code (FK)

Requirements:
    pip install psycopg2-binary

Update DB_CONFIG below to match your PostgreSQL setup.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime


# ── CONNECTION CONFIG ─────────────────────────────────────────────────────────
# Change these to match your PostgreSQL / pgAdmin setup

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "attendance_fr",   # create this in pgAdmin first
    "user":     "postgres",
    "password": "kelvin123",    # your pgAdmin password
}


# ── CONNECTION ────────────────────────────────────────────────────────────────

def get_db():
    """Returns a PostgreSQL connection."""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def get_cursor(conn):
    """
    Returns a DictCursor — rows behave like dicts: row["name"]
    Same feel as SQLite's row_factory = sqlite3.Row.
    """
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    """Creates all tables if they don't exist. Called once on app startup."""
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id           VARCHAR(50)  PRIMARY KEY,
            course_code  VARCHAR(20)  NOT NULL,
            subject      VARCHAR(50),
            section      VARCHAR(50),
            created      DATE DEFAULT CURRENT_DATE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name       VARCHAR(50)  NOT NULL,
            address    VARCHAR(100),
            number     VARCHAR(50),
            sr_code    VARCHAR(50),
            age        INTEGER,
            sex        VARCHAR(10),
            email      VARCHAR(100),
            photo      TEXT,
            signature  TEXT,
            UNIQUE (class_code, sr_code)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code     VARCHAR(50),
            name        VARCHAR(50)  NOT NULL,
            section     VARCHAR(50),
            subject     VARCHAR(50),
            status      VARCHAR(20)  NOT NULL,
            timestamp   TIMESTAMP(0) DEFAULT NOW(),
            date        DATE         NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
            time        VARCHAR(50),
            subject     VARCHAR(50),
            room        VARCHAR(50)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email    VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            status   VARCHAR(20) DEFAULT 'pending'
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] PostgreSQL tables ready.")


# ── CLASSES ───────────────────────────────────────────────────────────────────

def get_all_classes():
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes ORDER BY created DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_class(class_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM classes WHERE id = %s", (class_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row




def create_class(class_code, course_code, subject, section):
    """
    class_code  = teacher-defined unique ID  e.g. "CPET-3201-2026"
    course_code = e.g. "CPT-113"
    subject     = e.g. "Computer Programming"
    section     = e.g. "CPET-3201"
    created     = auto-set to today's date
    """
    conn    = get_db()
    cur     = get_cursor(conn)
    created = datetime.now().strftime("%Y-%m-%d")
    cur.execute(
        """INSERT INTO classes (id, course_code, subject, section, created)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (id) DO NOTHING""",
        (class_code, course_code, subject, section, created)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_class(class_code, course_code, subject, section):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE classes
           SET course_code=%s, subject=%s, section=%s
           WHERE id=%s""",
        (course_code, subject, section, class_code)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_class(class_code):
    """Deletes class + cascades to students, attendance, schedules."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM classes WHERE id = %s", (class_code,))
    conn.commit()
    cur.close(); conn.close()


# ── STUDENTS ──────────────────────────────────────────────────────────────────

def get_students(class_code):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "SELECT * FROM students WHERE class_code = %s ORDER BY name",
        (class_code,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_student(student_db_id):
    """Get one student by their auto-increment id."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM students WHERE id = %s", (student_db_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def get_student_by_srcode(sr_code):
    """Get one student by their SR code (unique student number)."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("SELECT * FROM students WHERE sr_code = %s", (sr_code,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def add_student(class_code, name, address, number,
                sr_code, age, sex, email, photo, signature):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """INSERT INTO students
           (class_code, name, address, number,
            sr_code, age, sex, email, photo, signature)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (class_code, name, address, number,
         sr_code, age, sex, email, photo, signature)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_student(student_db_id, name, address, number,
                 sr_code, age, sex, email):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """UPDATE students
           SET name=%s, address=%s, number=%s,
               sr_code=%s, age=%s, sex=%s, email=%s
           WHERE id=%s""",
        (name, address, number, sr_code, age, sex, email, student_db_id)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_student(student_db_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM students WHERE id = %s", (student_db_id,))
    conn.commit()
    cur.close(); conn.close()


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

def save_attendance(class_code, section, subject, records, date=None):
    """
    records = list of dicts:
        [
            {"name": "JohnDoe", "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            ...
        ]
    Deletes existing records for this class+date before inserting
    so the teacher can re-save without duplicates.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cur  = get_cursor(conn)

    # Remove existing records for this session (allow re-save)
    cur.execute(
        "DELETE FROM attendance WHERE class_code = %s AND date = %s",
        (class_code, date)
    )

    for r in records:
        # Build full timestamp: combine date + scan time from camera
        # e.g. date="2026-03-16", timestamp="07:02:34" → "2026-03-16 07:02:34"
        scan_time      = r.get("timestamp", "")
        full_timestamp = f"{date} {scan_time}" if scan_time else None

        cur.execute(
            """INSERT INTO attendance
               (class_code, sr_code, name, section, subject, status, timestamp, date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                class_code,
                r.get("sr_code", ""),
                r["name"],
                section,
                subject,
                r["status"],
                full_timestamp,   # "2026-03-16 07:02:34" — actual scan time
                date
            )
        )

    conn.commit()
    cur.close(); conn.close()


def get_attendance_session(class_code, date):
    """All attendance rows for one class on one date, sorted Present→Late→Absent."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT * FROM attendance
           WHERE class_code = %s AND date = %s
           ORDER BY
             CASE status
               WHEN 'Present' THEN 1
               WHEN 'Late'    THEN 2
               WHEN 'Absent'  THEN 3
             END,
             name""",
        (class_code, date)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_all_sessions():
    """One row per (class_code, date) — for the History page list."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               a.class_code,
               a.date,
               a.section,
               a.subject,
               COUNT(*)                                          AS total,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
               SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
           FROM attendance a
           GROUP BY a.class_code, a.date, a.section, a.subject
           ORDER BY a.date DESC"""
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_recent_activity(limit=10):
    """Most recent sessions for the dashboard Recent Activities list."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               class_code,
               date,
               section,
               subject,
               MIN(timestamp::text) AS time
           FROM attendance
           GROUP BY class_code, date, section, subject
           ORDER BY date DESC, time DESC
           LIMIT %s""",
        (limit,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_absence_counts():
    """Students with at least one absence — for the dashboard chart."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT name, COUNT(*) AS count
           FROM attendance
           WHERE status = 'Absent'
           GROUP BY name
           ORDER BY count DESC"""
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"name": r["name"], "count": r["count"]} for r in rows]


# ── SCHEDULES ─────────────────────────────────────────────────────────────────

def get_schedules(class_code=None):
    conn = get_db()
    cur  = get_cursor(conn)
    if class_code:
        cur.execute(
            "SELECT * FROM schedules WHERE class_code = %s ORDER BY id",
            (class_code,)
        )
    else:
        cur.execute("SELECT * FROM schedules ORDER BY id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def add_schedule(class_code, time, subject, room):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "INSERT INTO schedules (class_code, time, subject, room) VALUES (%s,%s,%s,%s)",
        (class_code, time, subject, room)
    )
    conn.commit()
    cur.close(); conn.close()


def edit_schedule(schedule_id, time, subject, room):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        "UPDATE schedules SET time=%s, subject=%s, room=%s WHERE id=%s",
        (time, subject, room, schedule_id)
    )
    conn.commit()
    cur.close(); conn.close()


def delete_schedule(schedule_id):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
    conn.commit()
    cur.close(); conn.close()


# ── INSTRUCTORS ───────────────────────────────────────────────────────────────

def get_all_instructors():
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT id, email, status FROM instructors ORDER BY id")
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows

def get_instructor_by_email(email):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM instructors WHERE email = %s", (email,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row

def register_instructor(email, password):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute(
        "INSERT INTO instructors (email, password, status) VALUES (%s, %s, %s)",
        (email, password, 'pending')
    )
    conn.commit(); cur.close(); conn.close()

def approve_instructor(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("UPDATE instructors SET status='approved' WHERE id=%s", (instructor_id,))
    conn.commit(); cur.close(); conn.close()

def delete_instructor(instructor_id):
    conn = get_db(); cur = get_cursor(conn)
    cur.execute("DELETE FROM instructors WHERE id=%s", (instructor_id,))
    conn.commit(); cur.close(); conn.close()


\\
--------------------------------------------------------------------
# fixing area

\\Init
-----------------------------------------
# removed

    id           VARCHAR(50)  PRIMARY KEY,
    course_code  VARCHAR(20)  NOT NULL,
    subject      VARCHAR(50),
    section      VARCHAR(50),
    created      DATE DEFAULT CURRENT_DATE


    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    class_code  VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
    time        VARCHAR(50),
    subject     VARCHAR(50),
    room        VARCHAR(50)



# replaced

    id            VARCHAR(50)  PRIMARY KEY,
    course_code   VARCHAR(20)  NOT NULL,
    subject       VARCHAR(50),
    section       VARCHAR(50),
    created       DATE DEFAULT CURRENT_DATE,
    instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE


    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    class_code    VARCHAR(50)  REFERENCES classes(id) ON DELETE CASCADE,
    instructor_id INTEGER REFERENCES instructors(id) ON DELETE CASCADE,
    time          VARCHAR(50),
    subject       VARCHAR(50),
    room          VARCHAR(50),
    day           VARCHAR(10)


\\classes
--------------------------------------
# removed

def get_all_classes():

cur.execute("SELECT * FROM classes ORDER BY created DESC")

def create_class(class_code, course_code, subject, section):

    class_code  = teacher-defined unique ID  e.g. "CPET-3201-2026"
    course_code = e.g. "CPT-113"
    subject     = e.g. "Computer Programming"
    section     = e.g. "CPET-3201"
    created     = auto-set to today's date


    """INSERT INTO classes (id, course_code, subject, section, created)
        VALUES (%s, %s, %s, %s, %s)

    (class_code, course_code, subject, section, created)


# replaced

def get_all_classes(instructor_id=None):

    if instructor_id:
        cur.execute(
            "SELECT * FROM classes WHERE instructor_id = %s ORDER BY created DESC",
            (instructor_id,)
        )
    else:
        cur.execute("SELECT * FROM classes ORDER BY created DESC")


def create_class(class_code, course_code, subject, section, instructor_id):
    
    class_code    = unique ID e.g. "CPT113-CPET3201-INS1"
    course_code   = e.g. "CPT-113"
    subject       = e.g. "Computer Programming"
    section       = e.g. "CPET-3201"
    instructor_id = FK to instructors table
    created       = auto-set to today's date

    """INSERT INTO classes (id, course_code, subject, section, created, instructor_id)
           VALUES (%s, %s, %s, %s, %s, %s)

    (class_code, course_code, subject, section, created, instructor_id)



\\SCHEDULES
----------------------------------------------------------
# removed

def get_schedules(class_code=None):

def add_schedule(class_code, time, subject, room):

     "INSERT INTO schedules (class_code, time, subject, room) VALUES (%s,%s,%s,%s)",
        (class_code, time, subject, room)



# replaced

def get_schedules(class_code=None, instructor_id=None):
    
    elif instructor_id:
        cur.execute(
            "SELECT * FROM schedules WHERE instructor_id = %s ORDER BY id",
            (instructor_id,))

def add_schedule(class_code, instructor_id, time, subject, room, day):

    """INSERT INTO schedules 
           (class_code, instructor_id, time, subject, room, day) 
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (class_code, instructor_id, time, subject, room, day)

=================================================================================================================================

# issue - adding schedule option along with the subject

\\index.html
----------------------------------------------------------

# removed

    <input type="text" id="modalSubject" placeholder="Subject Name" class="reg-input" required>

# replaced

    <!-- Subject is selected from existing schedules -->
    <select id="modalSubject" class="reg-input" required onchange="autoFillClassModal(this.value)">
        <option value="">Select Suggested Sched</option>
    </select>
    <!-- Auto-filled from schedule but editable -->
    <input type="text" id="modalSubjectName" class="reg-input hidden" placeholder="Subject Name" readonly>



\\script.js
------------------------------------------------------------

# removed

    const subject = document.getElementById('modalSubject').value;

    function openFolderModal() { editIdx = -1; document.getElementById('classModal').classList.remove('hidden'); }

    function openRealDoc(class_code, date) {
        window.open(`/api/download_pdf/${class_code}/${date}`, '_blank');


# replaced

    // Subject comes from the hidden field populated by autoFillClassModal
    // Falls back to select value if no autofill happened
    const subjectNameEl = document.getElementById('modalSubjectName');
    const subject = (subjectNameEl && subjectNameEl.value)
                    ? subjectNameEl.value
                    : document.getElementById('modalSubject').options[
                        document.getElementById('modalSubject').selectedIndex
                      ]?.dataset?.subject
                      || document.getElementById('modalSubject').value;


function openFolderModal() {
    editIdx = -1;
    populateSubjectSuggestions();   // fill the schedule dropdown before showing
    document.getElementById('modalSection').value = '';
    document.getElementById('modalYear').value    = '';
    document.getElementById('classModal').classList.remove('hidden');
}

added-->>
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


**------------------------------------------------------------**
# under the async function Save subject is schedule

# added

    const day = document.getElementById('modalDaySelect').value;

    // Switch the day filter to the saved schedule's day so it appears immediately
    selectedDay = day;


# removed

        day:        document.getElementById('modalDaySelect').value,

        await fetch('/api/schedules', {


# replaced

        day:        day,

        await authFetch('/api/schedules', {

================================================================================================================================
 # issues in leaking the datas to another instructor accounts

 **app.py**

# API DASHBOARD ---------------------------------------
# removed

    rows = db.get_recent_activity(limit=10)

    return jsonify(db.get_absence_counts())


# replaced

    instructor_id = get_current_instructor_id(request)
    rows = db.get_recent_activity(limit=10, instructor_id=instructor_id)

    instructor_id = get_current_instructor_id(request)
    return jsonify(db.get_absence_counts(instructor_id=instructor_id))

# API — SESSIONS LIST (for script.js renderHistoryPage) ---------------------------------------

# removed

    rows = db.get_all_sessions()

# replaced 

    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_sessions(instructor_id=instructor_id)


**database.py**

# ── ATTENDANCE ────────────────────────────────────────────────────────────────

# removed

def get_all_sessions():

    cur.execute(
        """SELECT
               a.class_code,
               a.date,
               a.section,
               a.subject,
               COUNT(*)                                          AS total,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
               SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
           FROM attendance a
           GROUP BY a.class_code, a.date, a.section, a.subject
           ORDER BY a.date DESC"""
    )

def get_recent_activity(limit=10):

    cur.execute(
        """SELECT
               class_code,
               date,
               section,
               subject,
               MIN(timestamp::text) AS time
           FROM attendance
           GROUP BY class_code, date, section, subject
           ORDER BY date DESC, time DESC
           LIMIT %s""",
        (limit,)
    )


def get_absence_counts():

    cur.execute(
        """SELECT name, COUNT(*) AS count
           FROM attendance
           WHERE status = 'Absent'
           GROUP BY name
           ORDER BY count DESC"""
    )




# replaced

def get_all_sessions(instructor_id=None):

    if instructor_id:
        cur.execute(
            """SELECT
                   a.class_code,
                   a.date,
                   a.section,
                   a.subject,
                   COUNT(*)                                          AS total,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
                   SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE c.instructor_id = %s
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC""",
            (instructor_id,)
        )
    else:
        cur.execute(
            """SELECT
                   a.class_code,
                   a.date,
                   a.section,
                   a.subject,
                   COUNT(*)                                          AS total,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
                   SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
               FROM attendance a
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC"""
        )


def get_recent_activity(limit=10, instructor_id=None):

    if instructor_id:
        cur.execute(
            """SELECT
                   a.class_code,
                   a.date,
                   a.section,
                   a.subject,
                   MIN(a.timestamp::text) AS time
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE c.instructor_id = %s
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC, time DESC
               LIMIT %s""",
            (instructor_id, limit)
        )
    else:
        cur.execute(
            """SELECT
                   class_code,
                   date,
                   section,
                   subject,
                   MIN(timestamp::text) AS time
               FROM attendance
               GROUP BY class_code, date, section, subject
               ORDER BY date DESC, time DESC
               LIMIT %s""",
            (limit,)
        )

def get_absence_counts(instructor_id=None):

    if instructor_id:
        cur.execute(
            """SELECT a.name, COUNT(*) AS count
               FROM attendance a
               JOIN classes c ON c.id = a.class_code
               WHERE a.status = 'Absent' AND c.instructor_id = %s
               GROUP BY a.name
               ORDER BY count DESC""",
            (instructor_id,)
        )
    else:
        cur.execute(
            """SELECT name, COUNT(*) AS count
               FROM attendance
               WHERE status = 'Absent'
               GROUP BY name
               ORDER BY count DESC"""
        )


=================================================================================================================================

# UPDATES: IN Classes and schedules**

    > create folder class successful
        > submission is working
        >database is working
        > added option schedule in registration

    >registration student successful
        > submission is working
        > database is working
        > possible issue:
**instructor id**

    > adding schedule is successful
        >displaying schedule in each of month
        >database is working


=================================================================================================================================

# Changes in the flow structure when runnng the app.py - it will now redirect to portal > login (admin/instructor) > home

**script.js**
# ── ON LOAD -------------------------------

# removed 

        window.location.href = "login.html";


# replaced

        window.location.href = "/";

# // ── SCHEDULE --------------------

# removed 

    const day = document.getElementById('modalDaySelect').value;


        day:        day,

        await authFetch('/api/schedules', {


# replaced

        day:        document.getElementById('modalDaySelect').value,

        await fetch('/api/schedules', {


        // Switch the day filter to the saved schedule's day so it appears immediately
    selectedDay = day;


# // ── CONFIRM DIALOG (unchanged logic, updated backend calls) ───────────────────

# removed 

            window.location.href = "login.html";


# replaced

            window.location.href = "/";



# LogIn.html

# removed

                setTimeout(() => { window.location.href = "index.html"; }, 1000);


# replaced

                setTimeout(() => { window.location.href = "/home"; }, 1000);


# app.py

# PAGE ROUTES — single page app, script.js handles all navigation ----------------------------

# added

def portal():
    return send_file("portal.html")


@app.route("/home")

# API — DASHBOARD -------------------------------------

# removed

    instructor_id = get_current_instructor_id(request)
    rows = db.get_recent_activity(limit=10, instructor_id=instructor_id)

        instructor_id = get_current_instructor_id(request)
    return jsonify(db.get_absence_counts(instructor_id=instructor_id))


# replaced

    rows = db.get_recent_activity(limit=10)

    return jsonify(db.get_absence_counts())

# API — SESSIONS LIST (for script.js renderHistoryPage) ------------------

# removed 

    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_sessions(instructor_id=instructor_id)


# replaced 

    rows = db.get_all_sessions()


=================================================================================================================================

# UPDATES: IN Classes and schedules**

    > create folder class successful
        > submission is working
        >database is working
        > added option schedule in registration

    >registration student successful
        > submission is working
        > database is working

    > adding schedule is successful
        >displaying schedule in each of month
        >database is working
**update issue**

    redirecting to portal as home is successful
        > account option successful
        > account registering successful
        > redirecting to login after registration
**add backtrack**

    > loging in multiple account is successful
        > does not leak the another data to another account
        >database verified
        > display successful

    > admin home and approval is successful
        > display successful
        > database none, 
**to be figuring out**

# Next goal is:
    >DESIGN IN HOME PORTAL
    >CAMERA
    >SCANNING
    >HISTORY
    >DASHBOARD


=================================================================================================================================

# FIXING CAMERA DISPLAY

**app.py**


# PAGE ROUTES--------------------------
# removed

def portal():
    return send_file("portal.html")


@app.route("/home")


# API — CAMERA / ATTENDANCE-------------------

# added

@app.route("/api/start_camera", methods=["POST"])
def api_start_camera():
    """Called by the frontend when the camera modal opens."""
    try:
        start_camera(0)   # 0 = default webcam
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


**script.js**


# ON LOAD ----------------------
# removed 

        window.location.href = "/";


# replaced

        window.location.href = "login.html";

# SCHEDULE --------------------

# removed

        await authFetch('/api/schedules', {



# replaced

        await fetch('/api/schedules', {


# CAMERA --------

# removed

function openCamera() {

// Replace dummyFeed content with real MJPEG stream

dummyFeed.innerHTML = `<img src="/video_feed" style="width:100%; height:100%; object-fit:cover;">`;


// Poll present students every 2 seconds

    }, 2000);


            window.location.href = "/";



# replaced

async function openCamera() {

---

--

--

        // Load the MJPEG stream — if it fails show an error
        const img = document.createElement('img');
        img.style = 'width:100%; height:100%; object-fit:cover;';
        img.src   = '/video_feed';
        img.onerror = () => {
            dummyFeed.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-center p-8">
                    <i data-lucide="camera-off" class="text-red-500 w-16 h-16 mb-4"></i>
                    <h3 class="text-white font-bold text-lg mb-2">No Video Feed</h3>
                    <p class="text-gray-400 text-xs">Could not connect to camera stream. Make sure the webcam is available.</p>
                </div>`;
            lucide.createIcons();
        };
        dummyFeed.innerHTML = '';
        dummyFeed.appendChild(img);

        // Step 3: Poll present students every 2 seconds


    }, 1500);


            window.location.href = "login.html";


# added

    // Step 1: Tell Flask to start the camera capture
    try {
        await authFetch('/api/start_camera', { method: 'POST' });
    } catch (e) {
        document.getElementById('cameraLoading').innerHTML = `
            <div class="flex flex-col items-center justify-center text-center">
                <i data-lucide="camera-off" class="text-red-500 w-16 h-16 mb-4"></i>
                <h3 class="text-white font-bold text-lg mb-2">Camera Failed to Start</h3>
                <p class="text-gray-400 text-xs">Check that your webcam is connected and not in use by another app.</p>
            </div>`;
        lucide.createIcons();
        return;
    }

    // Step 2: Short delay to let the camera warm up, then show the stream

================================================================================

# FIXING CAMERA LOGIC (LATE, PRESENT, ABSENT) along with redirecting to portal when running


**app.py**

# PAGE ROUTES —-------------------------

# added

def portal():
    return send_file("portal.html")


@app.route("/home")


# API — CAMERA / ATTENDANCE ----------------

# removed

    """Called by the frontend when the camera modal opens."""

        start_camera(0)   # 0 = default webcam


    return jsonify({"status": "ok"})


    return jsonify({"status": "ok"})





# replaced

    """Start the webcam capture and reset attendance for a new session."""

        global _camera_started, recognizer, known_enc, known_names
        # If camera was previously stopped, rebuild the recognizer
        if not _camera_started:
            recognizer = FaceRecognizer(known_enc, known_names)
            recognizer.start(0)
            _camera_started = True
        else:
            recognizer.reset_attendance()


    return jsonify({"status": "ok", "message": "Attendance saved."})

    return jsonify({"status": "ok", "message": "Attendance saved."})


# added

@app.route("/api/stop_camera", methods=["POST"])
def api_stop_camera():
    """Stop the camera and return the scan log (name → first_seen unix timestamp)."""
    global _camera_started
    try:
        scan_log = recognizer.get_scan_log()
        recognizer.stop_and_reset()
        _camera_started = False
        return jsonify({"status": "ok", "scan_log": scan_log})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan_log")
def api_scan_log():
    """Returns {name: first_seen_unix_timestamp} for all scanned students."""
    return jsonify(recognizer.get_scan_log())


# script.js ---------------------------

# ── ON LOAD --------------------------

# removed

        window.location.href = "login.html";



# added

        window.location.href = "/";


# ── CAMERA --------------------------------

# removed 

// ── CAMERA ────────────────────────────────────────────────────────────────────
// Connects to Flask /video_feed (MJPEG stream from facerecog.py)
// Polls /api/present_students every 2 seconds for the recognition panel

**-------------**
let _pollInterval = null;

**-------------**
    document.getElementById('recognizedList').innerHTML = "";

**-------------**
    // Step 1: Tell Flask to start the camera capture

**-------------**
            <div class="flex flex-col items-center justify-center text-center">
                <i data-lucide="camera-off" class="text-red-500 w-16 h-16 mb-4"></i>

**-------------**
                <p class="text-gray-400 text-xs">Check that your webcam is connected and not in use by another app.</p>

**-------------**
        lucide.createIcons();

**-------------**
    // Step 2: Short delay to let the camera warm up, then show the stream

**-------------**
        // Load the MJPEG stream — if it fails show an error


**-------------**
        img.style = 'width:100%; height:100%; object-fit:cover;';
        img.src   = '/video_feed';


**-------------**
                    <i data-lucide="camera-off" class="text-red-500 w-16 h-16 mb-4"></i>


**-------------**
                    <p class="text-gray-400 text-xs">Could not connect to camera stream. Make sure the webcam is available.</p>


**-------------**
            lucide.createIcons();

**-------------**
        // Step 3: Poll present students every 2 seconds


**-------------**
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


**-------------**
 function closeCamera() {


**-------------**
    if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }


**-------------**
// Save attendance from camera panel


**-------------**
        const res      = await authFetch('/api/present_students');
        const present  = await res.json();


**-------------**
        // Build all students list: present ones + mark rest as absent


**-------------**
        const records = allStud.map(s => ({
            name:      s.name,
            sr_code:   s.sr_code || '',
            status:    present.includes(s.name) ? 'Present' : 'Absent',
            timestamp: present.includes(s.name) ? new Date().toTimeString().substring(0,8) : ''
        }));


**-------------**
                records:    records


**-------------**
        closeCamera();
        alert('Attendance saved!');
    } catch {
        alert('Failed to save attendance.');


**-------------**
            window.location.href = "login.html";




# replaced

// ── CAMERA ───────────────────────────────────────────────────────────────────
// Full attendance logic:
//   0–5 min  after open → Present
//   5–15 min after open → Late
//   15+ min  OR dismiss → Absent (unscanned)
// On close → auto-save → show in History + Dashboard

**-------------**
let _pollInterval    = null;
let _cameraOpenTime  = null;   // Date when camera was opened
let _attendanceTimer = null;   // Interval that updates status badges
let _scannedStudents = {};     // { name: { status, time } } — live tracked

// Status thresholds (minutes)
const PRESENT_WINDOW = 5;
const LATE_WINDOW    = 15;

function getStatusForScanTime(scanUnixTime) {
    if (!_cameraOpenTime) return 'Present';
    const minutesAfterOpen = (scanUnixTime * 1000 - _cameraOpenTime) / 60000;
    if (minutesAfterOpen <= PRESENT_WINDOW) return 'Present';
    if (minutesAfterOpen <= LATE_WINDOW)    return 'Late';
    return 'Absent';
}

**-------------**
    if (!currentOpenedFolder) return;

    _scannedStudents = {};
    _cameraOpenTime  = Date.now();

    document.getElementById('recognizedList').innerHTML = '';

**-------------**
    // Update header badge to show counts
    updateDetectionHeader();

    // Start camera on backend

**-------------**
            <div class="flex flex-col items-center justify-center text-center px-8">

**-------------**
                <p class="text-gray-400 text-xs">Check that your webcam is connected and not in use.</p>

**-------------**
    // Get class schedule to know dismissal time
    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};
    const classSchedule = schedules.find(s =>
        s.subject && cls.subject &&
        s.subject.toLowerCase() === cls.subject.toLowerCase()
    );
    

**-------------**
        img.style.cssText = 'width:100%; height:100%; object-fit:cover;';
        img.src = '/video_feed';


**-------------**
                    <p class="text-gray-400 text-xs">Could not connect to camera. Make sure the webcam is available.</p>


**-------------**


**-------------**
        // ── Poll face recognition results every 2 seconds ──────────────────


**-------------**
                // Get scan log: { name: first_seen_unix_timestamp }
                const res     = await authFetch('/api/scan_log');
                const scanLog = await res.json();

                // Classify each scanned student based on when they were first seen
                Object.entries(scanLog).forEach(([name, firstSeenUnix]) => {
                    const status = getStatusForScanTime(firstSeenUnix);
                    _scannedStudents[name] = {
                        status,
                        time: new Date(firstSeenUnix * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    };
                });

                renderAttendancePanel();
                updateDetectionHeader();


**-------------**
function parseTimeStr(timeStr) {
    // Parse "9:00 AM" or "11:30 AM" into a Date for today
    try {
        const [time, ampm] = timeStr.split(' ');
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

    const entries = Object.entries(_scannedStudents);
    if (entries.length === 0) {
        list.innerHTML = '<p class="text-[10px] text-gray-400 text-center py-4">No faces detected yet...</p>';
        return;
    }

    // Sort: Present → Late → Absent
    const order = { Present: 0, Late: 1, Absent: 2 };
    entries.sort((a, b) => order[a[1].status] - order[b[1].status]);

    list.innerHTML = entries.map(([name, data]) => {
        const color = data.status === 'Present' ? 'text-green-500'
                    : data.status === 'Late'    ? 'text-yellow-500'
                    :                             'text-red-500';
        const bg    = data.status === 'Present' ? 'bg-green-50'
                    : data.status === 'Late'    ? 'bg-yellow-50'
                    :                             'bg-red-50';
        return `
            <div class="flex justify-between items-center border-b pb-3 mb-1 ${bg} px-2 py-2 rounded-xl">
                <div>
                    <p class="text-sm font-black text-gray-900">${name}</p>
                    <p class="text-[9px] font-bold text-gray-400">${data.time}</p>
                </div>
                <span class="text-[10px] font-black ${color} uppercase">${data.status}</span>
            </div>`;
    }).join('');
}

function updateDetectionHeader() {
    const entries  = Object.values(_scannedStudents);
    const present  = entries.filter(e => e.status === 'Present').length;
    const late     = entries.filter(e => e.status === 'Late').length;
    const headerEl = document.querySelector('#cameraModal .flex.gap-2.mt-2');
    if (!headerEl) return;
    headerEl.innerHTML = `
        <span class="bg-green-100 text-green-600 text-[9px] font-black px-2 py-1 rounded">PRESENT: ${present}</span>
        <span class="bg-yellow-100 text-yellow-600 text-[9px] font-black px-2 py-1 rounded">LATE: ${late}</span>`;
}

async function closeCamera(autoDismiss = false) {
    // Stop polling
    if (_pollInterval)    { clearInterval(_pollInterval);    _pollInterval    = null; }
    if (_attendanceTimer) { clearInterval(_attendanceTimer); _attendanceTimer = null; }

    // Save attendance before closing
    await saveAttendanceFromCamera();



**-------------**
    _cameraOpenTime = null;

    if (autoDismiss) {
        showToast('Class dismissed! Attendance saved automatically.', 'success');
    }


**-------------**
// Save attendance from camera panel — called automatically on closeCamera


**-------------**
        // Stop camera and get final scan log from backend
        const stopRes  = await authFetch('/api/stop_camera', { method: 'POST' });
        const stopData = await stopRes.json();
        const scanLog  = stopData.scan_log || {};


**-------------**
        // Get all registered students for this class


**-------------**
        // Build records: scanned = Present/Late, unscanned = Absent
        const records = allStud.map(s => {
            const firstSeenUnix = scanLog[s.name];
            if (firstSeenUnix) {
                const status    = getStatusForScanTime(firstSeenUnix);
                const timestamp = new Date(firstSeenUnix * 1000).toTimeString().substring(0, 8);
                return { name: s.name, sr_code: s.sr_code || '', status, timestamp };
            }
            // Not scanned at all → Absent
            return { name: s.name, sr_code: s.sr_code || '', status: 'Absent', timestamp: '' };
        });


**-------------**
                records


**-------------**
        // Clear local tracking
        _scannedStudents = {};

        showToast('Attendance saved successfully!', 'success');

    } catch (e) {
        showToast('Failed to save attendance.', 'error');


**-------------**

            window.location.href = "/";



# added


        // ── Re-evaluate statuses every 30 seconds as time windows shift ────
        _attendanceTimer = setInterval(() => {
            // Re-classify anyone whose status might have changed (Present→Late)
            // We do this by re-calling getStatusForScanTime on each stored entry
            // Since _scannedStudents stores the status not the original time,
            // we need to re-fetch scan log to re-evaluate
        }, 30000);

        // ── Auto-dismiss: check if class end time has passed every minute ──
        if (classSchedule && classSchedule.time) {
            const timeParts = classSchedule.time.split(' - ');
            if (timeParts.length === 2) {
                const endTimeStr = timeParts[1].trim();
                const checkDismiss = setInterval(() => {
                    const now     = new Date();
                    const endTime = parseTimeStr(endTimeStr);
                    if (endTime && now >= endTime) {
                        clearInterval(checkDismiss);
                        closeCamera(true);  // auto-close at dismissal
                    }
                }, 60000);
            }
        }

**-------------**

function showToast(msg, type = 'success') {
    // Reuse the toast element if it exists, otherwise create one
    let toast = document.getElementById('attendanceToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'attendanceToast';
        toast.style.cssText = `
            position:fixed; bottom:30px; left:50%; transform:translateX(-50%);
            padding:14px 28px; border-radius:12px; font-weight:700; font-size:13px;
            z-index:9999; transition:opacity 0.4s; box-shadow:0 8px 24px rgba(0,0,0,0.15);`;
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.background = type === 'success' ? '#1B5E20' : '#B71C1C';
    toast.style.color       = 'white';
    toast.style.opacity     = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 3500);
}



# face recog file

# ── RECOGNIZER --------------------

# added

        self._scan_log       = {}           # {name: first_seen_time}


 # ── public API -----------------------

 # added

     def get_scan_log(self):
        """Returns dict of {name: first_seen_timestamp} for all scanned students."""
        with self._lock:
            return dict(self._scan_log)

    def reset_attendance(self):
        """Clears the present set and scan log for a new session."""
        with self._lock:
            self._present_set = set()
            self._scan_log    = {}

    def stop_and_reset(self):
        """Stops the camera and clears attendance data."""
        self._running = False
        if hasattr(self, "cap"):
            self.cap.release()
        with self._lock:
            self._present_set    = set()
            self._scan_log       = {}
            self._latest_frame   = None
            self._face_locations = []
            self._face_names     = []
        global _camera_started
        _camera_started = False

# ── internals----------------------

# added

                        if name not in self._scan_log:
                            self._scan_log[name] = time.time()


===============================================================================================================================

# Fixing the attendance record and adding pop up  warning before proceeding in camera

# script.js

#  ── ON LOAD 

# removed

        window.location.href = "/";


# replaced

        window.location.href = "login.html";

# ── SCHEDULE 

# removed
        await authFetch('/api/schedules', {



# replaced
        await fetch('/api/schedules', {

# ── CAMERA  

# removed
// Full attendance logic:
//   0–5 min  after open → Present
//   5–15 min after open → Late
//   15+ min  OR dismiss → Absent (unscanned)
// On close → auto-save → show in History + Dashboard

**--------------**
let _cameraOpenTime  = null;   // Date when camera was opened
let _attendanceTimer = null;   // Interval that updates status badges
let _scannedStudents = {};     // { name: { status, time } } — live tracked

**--------------**

// Status thresholds (minutes)
const PRESENT_WINDOW = 5;
const LATE_WINDOW    = 15;

**--------------**
function getStatusForScanTime(scanUnixTime) {


**--------------**
    const minutesAfterOpen = (scanUnixTime * 1000 - _cameraOpenTime) / 60000;
    if (minutesAfterOpen <= PRESENT_WINDOW) return 'Present';
    if (minutesAfterOpen <= LATE_WINDOW)    return 'Late';

**--------------**
async function openCamera() {


**--------------**

    // Update header badge to show counts


**--------------**
    // Get class schedule to know dismissal time
    const cls = classFolders.find(f => f.id === currentOpenedFolder) || {};
    const classSchedule = schedules.find(s =>
        s.subject && cls.subject &&
        s.subject.toLowerCase() === cls.subject.toLowerCase()
    );



**--------------**
                    <p class="text-gray-400 text-xs">Could not connect to camera. Make sure the webcam is available.</p>


**--------------**
        dummyFeed.innerHTML = '';


**--------------**
        // ── Poll face recognition results every 2 seconds ──────────────────


**--------------**
                // Get scan log: { name: first_seen_unix_timestamp }


**--------------**
                // Classify each scanned student based on when they were first seen
                Object.entries(scanLog).forEach(([name, firstSeenUnix]) => {
                    const status = getStatusForScanTime(firstSeenUnix);
                    _scannedStudents[name] = {
                        status,
                        time: new Date(firstSeenUnix * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    };



**--------------**
        // ── Re-evaluate statuses every 30 seconds as time windows shift ────
        _attendanceTimer = setInterval(() => {
            // Re-classify anyone whose status might have changed (Present→Late)
            // We do this by re-calling getStatusForScanTime on each stored entry
            // Since _scannedStudents stores the status not the original time,
            // we need to re-fetch scan log to re-evaluate
        }, 30000);

        // ── Auto-dismiss: check if class end time has passed every minute ──
        if (classSchedule && classSchedule.time) {
            const timeParts = classSchedule.time.split(' - ');
            if (timeParts.length === 2) {
                const endTimeStr = timeParts[1].trim();
                const checkDismiss = setInterval(() => {
                    const now     = new Date();
                    const endTime = parseTimeStr(endTimeStr);
                    if (endTime && now >= endTime) {
                        clearInterval(checkDismiss);
                        closeCamera(true);  // auto-close at dismissal



**--------------**
                }, 60000);



**--------------**

    // Parse "9:00 AM" or "11:30 AM" into a Date for today


**--------------**

        const [time, ampm] = timeStr.split(' ');


**--------------**

    const entries = Object.entries(_scannedStudents);



**--------------**

    // Sort: Present → Late → Absent



**--------------**
    entries.sort((a, b) => order[a[1].status] - order[b[1].status]);

    list.innerHTML = entries.map(([name, data]) => {
        const color = data.status === 'Present' ? 'text-green-500'
                    : data.status === 'Late'    ? 'text-yellow-500'
                    :                             'text-red-500';
        const bg    = data.status === 'Present' ? 'bg-green-50'
                    : data.status === 'Late'    ? 'bg-yellow-50'
                    :                             'bg-red-50';


**--------------**
            <div class="flex justify-between items-center border-b pb-3 mb-1 ${bg} px-2 py-2 rounded-xl">



**--------------**
                    <p class="text-sm font-black text-gray-900">${name}</p>
                    <p class="text-[9px] font-bold text-gray-400">${data.time}</p>



**--------------**
                <span class="text-[10px] font-black ${color} uppercase">${data.status}</span>


**--------------**
    const entries  = Object.values(_scannedStudents);
    const present  = entries.filter(e => e.status === 'Present').length;
    const late     = entries.filter(e => e.status === 'Late').length;
    const headerEl = document.querySelector('#cameraModal .flex.gap-2.mt-2');
    if (!headerEl) return;
    headerEl.innerHTML = `



**--------------**

    // Stop polling
    if (_pollInterval)    { clearInterval(_pollInterval);    _pollInterval    = null; }
    if (_attendanceTimer) { clearInterval(_attendanceTimer); _attendanceTimer = null; }


**--------------**
    // Save attendance before closing


**--------------**
    _cameraOpenTime = null;



**--------------**
    if (autoDismiss) {
        showToast('Class dismissed! Attendance saved automatically.', 'success');
    }



**--------------**
// Save attendance from camera panel — called automatically on closeCamera



**--------------**
        const scanLog  = stopData.scan_log || {};



**--------------**
        // Get all registered students for this class



**--------------**
        // Build records: scanned = Present/Late, unscanned = Absent


**--------------**
            const firstSeenUnix = scanLog[s.name];
            if (firstSeenUnix) {
                const status    = getStatusForScanTime(firstSeenUnix);
                const timestamp = new Date(firstSeenUnix * 1000).toTimeString().substring(0, 8);



**--------------**

            // Not scanned at all → Absent


**--------------**
            method: 'POST',


**--------------**
                section:    cls.section || '',
                subject:    cls.subject || '',



**--------------**
        // Clear local tracking
        _scannedStudents = {};

        showToast('Attendance saved successfully!', 'success');


**--------------**
    // Reuse the toast element if it exists, otherwise create one

**--------------**
        toast.style.cssText = `
            position:fixed; bottom:30px; left:50%; transform:translateX(-50%);
            padding:14px 28px; border-radius:12px; font-weight:700; font-size:13px;
            z-index:9999; transition:opacity 0.4s; box-shadow:0 8px 24px rgba(0,0,0,0.15);`;



**--------------**
    toast.textContent = msg;



**--------------**
    toast.style.color       = 'white';
    toast.style.opacity     = '1';


# // ── CONFIRM DIALOG
**--------------**
            window.location.href = "/";



**--------------**



# replaced

// Attendance windows (minutes after camera opens):
//   0 – PRESENT_WINDOW  → Present
//   PRESENT_WINDOW – LATE_WINDOW → Late
//   > LATE_WINDOW OR never scanned → Absent

const PRESENT_WINDOW = 5;   // minutes
const LATE_WINDOW    = 15;  // minutes

**--------------**
let _cameraOpenTime  = null;   // unix ms when camera opened
let _dismissTimer    = null;   // auto-close at class end
let _scannedStudents = {};     // { normalizedName: { displayName, status, time } }
let _customSchedule  = null;   // set when instructor picks make-up schedule

**--------------**

// Normalize name: "Kelvin_Lloyd_Africa" → "Kelvin Lloyd Africa"
function normalizeName(n) { return n.replace(/_/g, ' ').trim(); }

**--------------**
function getStatusForScanTime(firstSeenUnix) {



**--------------**
    const mins = (firstSeenUnix * 1000 - _cameraOpenTime) / 60000;
    if (mins <= PRESENT_WINDOW) return 'Present';
    if (mins <= LATE_WINDOW)    return 'Late';



**--------------**
// ── SCHEDULE CHECK MODAL ─────────────────────────────────────────────────────

function openCamera() {



**--------------**



**--------------**



**--------------**
                    <p class="text-gray-400 text-xs">Could not connect to camera stream.</p>



**--------------**



**--------------**
        // Poll scan log every 2 seconds



**--------------**



**--------------**
                Object.entries(scanLog).forEach(([rawName, firstSeenUnix]) => {
                    const displayName = normalizeName(rawName);
                    const status      = getStatusForScanTime(firstSeenUnix);
                    const time        = new Date(firstSeenUnix * 1000)
                                          .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    _scannedStudents[displayName] = { displayName, status, time, rawName };


**--------------**
        // Auto-dismiss at class end time
        if (activeSchedule && activeSchedule.time) {
            const parts = activeSchedule.time.split(' - ');
            if (parts.length === 2) {
                const endTime = parseTimeStr(parts[1].trim());
                if (endTime) {
                    const msUntilEnd = endTime.getTime() - Date.now();
                    if (msUntilEnd > 0) {
                        _dismissTimer = setTimeout(() => closeCamera(true), msUntilEnd);



**--------------**
                    }


**--------------**



**--------------**
        const [time, ampm] = timeStr.trim().split(' ');



**--------------**
    const entries = Object.values(_scannedStudents);



**--------------**



**--------------**

    entries.sort((a, b) => order[a.status] - order[b.status]);
    list.innerHTML = entries.map(e => {
        const color = e.status === 'Present' ? 'text-green-500'
                    : e.status === 'Late'    ? 'text-yellow-500' : 'text-red-500';
        const bg    = e.status === 'Present' ? 'bg-green-50'
                    : e.status === 'Late'    ? 'bg-yellow-50'   : 'bg-red-50';

**--------------**
            <div class="flex justify-between items-center ${bg} px-3 py-3 rounded-xl mb-2">



**--------------**
                    <p class="text-sm font-black text-gray-900">${e.displayName}</p>
                    <p class="text-[9px] font-bold text-gray-400">${e.time}</p>



**--------------**
                <span class="text-[10px] font-black ${color} uppercase">${e.status}</span>




**--------------**
    const vals    = Object.values(_scannedStudents);
    const present = vals.filter(e => e.status === 'Present').length;
    const late    = vals.filter(e => e.status === 'Late').length;
    const el      = document.querySelector('#cameraModal .flex.gap-2.mt-2');
    if (!el) return;
    el.innerHTML = `



**--------------**
    if (_pollInterval)   { clearInterval(_pollInterval);  _pollInterval  = null; }
    if (_dismissTimer)   { clearTimeout(_dismissTimer);   _dismissTimer  = null; }



**--------------**




**--------------**
    _cameraOpenTime  = null;
    _customSchedule  = null;
    _scannedStudents = {};



**--------------**

    showToast(autoDismiss
        ? 'Class dismissed! Attendance saved automatically.'
        : 'Attendance saved successfully!', 'success');


**--------------**




**--------------**
        const scanLog  = stopData.scan_log || {};   // { rawName: unix_timestamp }



**--------------**
        // Get all registered students



**--------------**



**--------------**
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



**--------------**
            // Not scanned → Absent



**--------------**
            method:  'POST',



**--------------**

                section:    cls.section  || '',
                subject:    cls.subject  || '',
                room:       activeSchedule ? activeSchedule.room || '' : '',


**--------------**

        toast.style.cssText = `position:fixed;bottom:30px;left:50%;transform:translateX(-50%);
            padding:14px 28px;border-radius:12px;font-weight:700;font-size:13px;
            z-index:9999;transition:opacity 0.4s;box-shadow:0 8px 24px rgba(0,0,0,0.15);`;


**--------------**
    toast.textContent    = msg;




**--------------**
    toast.style.color      = 'white';
    toast.style.opacity    = '1';




# // ── CONFIRM DIALOG
**--------------**

            window.location.href = "login.html";


**--------------**





# added

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
                <button onclick="document.getElementById('scheduleWarningModal').remove(); showMakeupScheduleModal(
                    ${JSON.stringify(cls)},
                    ${JSON.stringify(classSchedule)},
                    function(){ startCameraSession(${JSON.stringify(cls)}, _customSchedule); }
                )"
                    class="flex-1 py-4 bg-[#D32F2F] text-white font-bold rounded-xl shadow-lg hover:bg-[#B71C1C] transition">
                    Set Make-Up Schedule
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);
}

function showMakeupScheduleModal(cls, originalSchedule, onConfirm) {
    const existing = document.getElementById('makeupModal');
    if (existing) existing.remove();

    // Build time options
    let timeOpts = '';
    for (let i = 7; i <= 21; i++) {
        const h = i > 12 ? i - 12 : i;
        const ap = i >= 12 ? 'PM' : 'AM';
        timeOpts += `<option value="${h}:00 ${ap}">${h}:00 ${ap}</option>`;
        timeOpts += `<option value="${h}:30 ${ap}">${h}:30 ${ap}</option>`;
    }
    const days = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
    const dayOpts = days.map(d => `<option value="${d}">${d}</option>`).join('');

    const modal = document.createElement('div');
    modal.id = 'makeupModal';
    modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-md z-[300] flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-[2rem] w-full max-w-md p-8 shadow-2xl">
            <h2 class="text-xl font-black text-[#D32F2F] mb-1">Make-Up / Custom Schedule</h2>
            <p class="text-xs text-gray-400 font-bold mb-6 uppercase tracking-wider">${cls.subject || ''} — ${cls.section || ''}</p>
            <div class="space-y-4">
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 block">Day</label>
                    <select id="mkDay" class="reg-input">${dayOpts}</select>
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
                <button onclick="confirmMakeupSchedule()" 
                    class="flex-1 py-4 bg-[#D32F2F] text-white font-bold rounded-xl shadow-lg hover:bg-[#B71C1C] transition">
                    Start Scanning
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);

    // Store callback for when confirmed
    window._makeupOnConfirm = onConfirm;
}

function confirmMakeupSchedule() {
    const day  = document.getElementById('mkDay').value;
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

# ── CORE CAMERA SESSION ───────────────────────────────────────────────────────

async function startCameraSession(cls, activeSchedule) {

**--------------**
        dummyFeed.innerHTML = '';



**--------------**
        // Use custom schedule info if makeup class
        const activeSchedule = _customSchedule || schedules.find(s =>
            s.subject && cls.subject &&
            s.subject.trim().toLowerCase() === cls.subject.trim().toLowerCase()
        );




**--------------**

        console.error('Save attendance failed:', e);


**---------------------------------------------------------------------**

# app. py

# ── SCHEDULE 

# removed
**--------------**
    """Start the webcam capture and reset attendance for a new session."""



**--------------**
        global _camera_started, recognizer, known_enc, known_names
        # If camera was previously stopped, rebuild the recognizer



**--------------**
    """Stop the camera and return the scan log (name → first_seen unix timestamp)."""



**--------------**
@app.route("/api/scan_log")
def api_scan_log():
    """Returns {name: first_seen_unix_timestamp} for all scanned students."""
    return jsonify(recognizer.get_scan_log())





**--------------**
    return jsonify({"status": "ok", "message": "Attendance saved."})


**--------------**
    return jsonify({"status": "ok", "message": "Attendance saved."})


**--------------**





# replaced
**--------------**
    """Start webcam and reset attendance for a fresh session."""
    global _camera_started, recognizer, known_enc, known_names



**--------------**



**--------------**
    """Stop webcam and return the final scan log."""



**--------------**

    return jsonify({"status": "ok"})


**--------------**
    return jsonify({"status": "ok"})


**--------------**





# added

**--------------**
@app.route("/api/scan_log")
def api_scan_log():
    """Live scan log: {name: first_seen_unix_timestamp}."""
    try:
        return jsonify(recognizer.get_scan_log())
    except Exception:
        return jsonify({})


**----------------------------------------------------------------**

# face recognition


# ── RECOGNIZER 

# removed
**--------------**
        self._scan_log       = {}           # {name: first_seen_time}
        
# replaced



**--------------**
        self._scan_log       = {}           # {name: first_seen_unix_time}

**--------------**


# ── public API 

**--------------**
        """Returns dict of {name: first_seen_timestamp} for all scanned students."""



**--------------**
        """Clears the present set and scan log for a new session."""



**--------------**
        """Stops the camera and clears attendance data."""


**--------------**
            self.cap.release()



**--------------**
        global _camera_started
        _camera_started = False


# replaced
**--------------**
        """Returns {name: first_seen_unix_timestamp} for all scanned students."""



**--------------**
        """Clears present set and scan log for a new session."""



**--------------**
        """Stops the camera capture and clears all session data."""



**--------------**
            try:
                self.cap.release()
            except Exception:
                pass



**--------------**
================================================================================================================================
# ── adding moddifying, and fixing the issue on history , where history file created, the other panel, and the pdf generating  

**script.js**

# ── HISTORY 

# removed
**--------------**

        const res = await authFetch('/api/sessions');
        historyFolders = await res.json();
    } catch {
        historyFolders = [];
    }


**--------------**
    const filtered    = historyFolders.filter(f =>
        (f.section + f.subject + f.date).toLowerCase().includes(searchVal.toLowerCase())



**--------------**
    const activeData  = filtered[selectedHistoryIdx] || null;
    let dynamicTitle  = "Select a session";
    if (showAllHistoryFiles) dynamicTitle = "ALL SESSIONS";
    else if (activeData) dynamicTitle = `${activeData.section} — ${activeData.date}`;



**--------------**
            <div class="flex space-x-2">
                <button onclick="showAllHistoryFiles = true; renderHistoryPage()" class="bg-gray-100 text-gray-600 px-6 py-3 rounded-xl text-[10px] font-black uppercase hover:bg-black hover:text-white transition">Show All Files</button>
            </div>



**--------------**

            <input type="text" oninput="searchVal = this.value; renderHistoryPage()" value="${searchVal}" placeholder="Search archives..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">

**--------------**
        <div class="flex gap-10 h-[calc(100%-250px)]">
            <div class="w-1/3 space-y-4 overflow-y-auto pr-4 border-r border-gray-50">
                ${filtered.map((f, i) => `
                    <div onclick="selectedHistoryIdx = ${i}; showAllHistoryFiles = false; renderHistoryPage()"
                         class="p-6 rounded-[2rem] cursor-pointer transition flex items-center justify-between ${!showAllHistoryFiles && i === selectedHistoryIdx ? 'bg-red-50 border-2 border-red-100' : 'bg-white hover:bg-gray-50'}">
                        <div class="flex items-center space-x-4 min-w-0">
                            <div class="w-10 h-10 rounded-xl flex items-center justify-center ${!showAllHistoryFiles && i === selectedHistoryIdx ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-gray-400'}">
                                <i data-lucide="folder-archive" class="w-5 h-5"></i>



**--------------**
                                <h4 class="font-black text-gray-900 truncate">${f.section}</h4>
                                <p class="text-[9px] font-bold text-gray-400 uppercase">${f.subject} | ${f.date}</p>



**--------------**
            <div class="flex-1 bg-gray-50/50 border-2 border-dashed border-gray-200 rounded-[3rem] p-8 overflow-y-auto flex flex-col">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="font-black text-[12px] text-gray-400 uppercase tracking-widest">${dynamicTitle}</h3>
                    ${activeData ? `
                    <button onclick="downloadPDF('${activeData.class_code}', '${activeData.date}')"
                            class="flex items-center space-x-2 px-4 py-2 bg-red-50 text-[#D32F2F] rounded-xl font-bold text-xs hover:bg-red-100 transition">
                        <i data-lucide="download" class="w-4 h-4"></i> <span>Download PDF</span>
                    </button>` : ''}



**--------------**
                ${activeData ? `
                <div id="sessionDetail">
                    <p class="text-center text-gray-300 font-bold py-4 text-xs">Loading records...</p>
                </div>` : `
                <div class="flex-1 flex items-center justify-center text-gray-300 font-bold text-xs uppercase">
                    Select a session on the left
                </div>`}



**--------------**
    if (activeData) loadSessionDetail(activeData.class_code, activeData.date);


**--------------**




# replaced
**--------------**
        const res = await authFetch('/api/classes');
        classFolders = await res.json();
    } catch { classFolders = []; }



**--------------**
    const filtered = classFolders.filter(f =>
        (f.subject + f.section).toLowerCase().includes(searchVal.toLowerCase())



**--------------**



**--------------**



**--------------**

            <input type="text" oninput="searchVal=this.value; renderHistoryPage()" value="${searchVal}"
                placeholder="Search classes..." class="w-full bg-gray-50 border-none rounded-2xl py-4 pl-12 pr-4 text-sm font-bold outline-none">


**--------------**
        <div class="flex gap-6 h-[calc(100vh-280px)] min-h-[400px]">

            <!-- Column 1: Class Folders -->
            <div class="w-64 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">
                <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-3">Class Folders</p>
                ${filtered.length === 0 ? '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No classes yet</p>' :
                  filtered.map(f => `
                    <div onclick="historySelectClass('${f.id}')"
                         class="p-4 rounded-2xl cursor-pointer transition border ${historySelectedClass === '${f.id}' ? 'bg-red-50 border-[#D32F2F]' : 'bg-white border-gray-100 hover:border-red-200'}">
                        <div class="flex items-center space-x-3">
                            <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${historySelectedClass === '${f.id}' ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-gray-400'}">
                                <i data-lucide="folder" class="w-4 h-4"></i>



**--------------**

                                <p class="font-black text-gray-900 text-sm truncate">${f.subject}</p>
                                <p class="text-[9px] text-gray-400 font-bold uppercase truncate">${f.section}</p>


**--------------**

            <!-- Column 2: Attendance Files for selected class -->
            <div class="w-64 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">
                <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-3">Attendance Files</p>
                <div id="historyFilesList">
                    <p class="text-[10px] text-gray-300 font-bold text-center py-8">Select a class folder</p>



**--------------**

            </div>

            <!-- Column 3: Session Detail + View & Print -->
            <div class="flex-1 overflow-y-auto">
                <div id="historyDetailPanel" class="h-full bg-gray-50/50 border-2 border-dashed border-gray-200 rounded-[2.5rem] p-8 flex flex-col">
                    <div class="flex-1 flex items-center justify-center text-gray-300 font-bold text-xs uppercase">
                        Select an attendance file
                    </div>
                </div>


**--------------**
    // Restore column 2 if class already selected
    if (historySelectedClass) {
        await historyLoadFiles(historySelectedClass);
        if (historySelectedSession) {
            await historyLoadDetail(historySelectedSession.class_code,
                                    historySelectedSession.date,
                                    historySelectedSession.session_time);
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
        listEl.innerHTML = '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No attendance records yet</p>';
        return;
    }

    listEl.innerHTML = historyClassSessions.map((s, i) => {
        const isActive = historySelectedSession &&
                         historySelectedSession.date === s.date &&
                         historySelectedSession.session_time === s.session_time;
        const dispDate = new Date(s.date + 'T00:00:00').toLocaleDateString('en-US',
                          { month:'short', day:'numeric', year:'numeric' });
        const dispTime = s.session_time ? s.session_time.substring(0,5) : '';
        return `
            <div onclick="historySelectSession('${s.class_code}','${s.date}','${s.session_time || ''}')"
                 class="p-4 rounded-2xl cursor-pointer transition border ${isActive ? 'bg-red-50 border-[#D32F2F]' : 'bg-white border-gray-100 hover:border-red-200'}">
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-[#D32F2F]'}">
                        <i data-lucide="file-text" class="w-4 h-4"></i>
                    </div>
                    <div class="min-w-0">
                        <p class="font-black text-gray-900 text-xs truncate">Log_${dispDate}</p>
                        <p class="text-[9px] text-gray-400 font-bold">${dispTime} • P:${s.present} L:${s.late} A:${s.absent}</p>
                    </div>
                </div>
            </div>`;
    }).join('');
    lucide.createIcons();
}

async function historySelectSession(class_code, date, session_time) {
    historySelectedSession = { class_code, date, session_time };
    await historyLoadDetail(class_code, date, session_time);
    // Re-render files list to highlight active
    await historyLoadFiles(class_code);
}

async function historyLoadDetail(class_code, date, session_time) {
    const panel = document.getElementById('historyDetailPanel');
    if (!panel) return;
    panel.innerHTML = '<p class="text-[10px] text-gray-400 text-center py-8">Loading...</p>';

    try {
        const url = `/api/attendance/${class_code}/${date}` + (session_time ? `?session_time=${session_time}` : '');
        const res     = await authFetch(url);
        const records = await res.json();
        const present = records.filter(r => r.status === 'Present');
        const late    = records.filter(r => r.status === 'Late');
        const absent  = records.filter(r => r.status === 'Absent');

        const cls     = classFolders.find(f => f.id === class_code) || {};
        const dispDate= new Date(date + 'T00:00:00').toLocaleDateString('en-US',
                          { weekday:'long', year:'numeric', month:'long', day:'numeric' });
        const dispTime= session_time ? session_time.substring(0,5) : '';

        const renderRows = (list, color, label) => list.length === 0
            ? `<p class="text-[10px] text-gray-300 font-bold py-2 pl-2">None</p>`
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
                    <p class="text-[10px] text-gray-400 font-bold uppercase">${cls.section || ''} • ${dispDate} • ${dispTime}</p>
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
            <div class="space-y-4 overflow-y-auto">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Present (${present.length})</p>
                ${renderRows(present,'text-green-500','Present')}
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Late (${late.length})</p>
                ${renderRows(late,'text-yellow-500','Late')}
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Absent (${absent.length})</p>
                ${renderRows(absent,'text-red-500','Absent')}
            </div>`;
        lucide.createIcons();
    } catch(e) {
        panel.innerHTML = `<p class="text-center text-gray-300 font-bold py-8 text-xs">Could not load records.</p>`;
    }
}

function formatDisplayTime(ts) {
    if (!ts) return '—';
    try {
        const s = String(ts).split('.')[0];
        const d = s.includes(' ') ? new Date(s.replace(' ','T')) : new Date('1970-01-01T' + s);
        if (isNaN(d)) return s.substring(11,16) || s;
        return d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
    } catch { return String(ts).substring(11,16) || String(ts); }
}

async function viewAndPrintPDF(class_code, date, session_time) {
    const cls    = classFolders.find(f => f.id === class_code) || {};
    const sParam = session_time ? `?session_time=${session_time}` : '';

    // Fetch records to render in-page preview
    try {
        const res     = await authFetch(`/api/attendance/${class_code}/${date}${sParam}`);
        const records = await res.json();
        const present = records.filter(r => r.status === 'Present');
        const late    = records.filter(r => r.status === 'Late');
        const absent  = records.filter(r => r.status === 'Absent');

        const sched   = schedules.find(s =>
            s.subject && cls.subject &&
            s.subject.trim().toLowerCase() === cls.subject.trim().toLowerCase());
        const timeVal = sched ? sched.time : '';
        const roomVal = sched ? sched.room : '';
        const dispDate= new Date(date + 'T00:00:00').toLocaleDateString('en-US',
                          { year:'numeric', month:'long', day:'numeric' });

        const session = JSON.parse(localStorage.getItem('active_session') || '{}');
        const faculty = (session.email || '').split('@')[0].replace(/[._]/g,' ')
                        .replace(/\w/g, l => l.toUpperCase());

        const statusColor = s => s === 'Present' ? '#388E3C' : s === 'Late' ? '#E65100' : '#D32F2F';

        const tableRows = (list) => list.map((r, i) => `
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:6px 4px;font-size:11px;">${i+1}.</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:600;">${r.name}</td>
                <td style="padding:6px 4px;font-size:11px;">${r.sr_code || ''}</td>
                <td style="padding:6px 4px;font-size:11px;">${formatDisplayTime(r.timestamp)}</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:700;color:${statusColor(r.status)}">${r.status}</td>
                <td style="padding:6px 4px;font-size:11px;border-bottom:1px solid #ccc;min-width:80px;"></td>
            </tr>`).join('');

        const absentRows = absent.map((r, i) => `
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:6px 4px;font-size:11px;">${i+1}.</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:600;">${r.name}</td>
                <td style="padding:6px 4px;font-size:11px;">${r.sr_code || ''}</td>
                <td style="padding:6px 4px;font-size:11px;color:#D32F2F;font-weight:700;">ABSENT</td>
            </tr>`).join('');

        document.getElementById('printArea').innerHTML = `
            <div style="max-width:760px;margin:0 auto;background:white;padding:32px;font-family:'Segoe UI',sans-serif;">
                <!-- Header -->
                <table style="width:100%;border-collapse:collapse;border:1px solid #333;">
                    <tr>
                        <td style="width:120px;padding:12px;text-align:center;border-right:1px solid #ccc;">
                            <div style="width:60px;height:60px;background:#f5f5f5;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:9px;color:#999;text-align:center;">BSU LOGO</div>
                        </td>
                        <td style="padding:12px;text-align:center;border-right:1px solid #ccc;">
                            <p style="font-size:11px;font-weight:800;margin:0;">Batangas State University</p>
                            <p style="font-size:10px;font-weight:700;margin:2px 0;">ARASOF-Nasugbu Campus</p>
                            <p style="font-size:13px;font-weight:900;color:#D32F2F;margin:6px 0 2px;">ATTENDANCE SHEET</p>
                            <p style="font-size:10px;margin:0;color:#555;">Student Class Attendance</p>
                        </td>
                        <td style="padding:10px;font-size:9px;color:#666;vertical-align:top;min-width:140px;">
                            <div>Reference No.: <b>BatStateU-REC-ATT-11</b></div>
                            <div style="margin-top:4px;">Effectivity: <b>January 3, 2017</b></div>
                            <div style="margin-top:4px;">Revision No.: <b>00</b></div>
                        </td>
                    </tr>
                </table>
                <!-- Info -->
                <table style="width:100%;border-collapse:collapse;border:1px solid #333;border-top:none;">
                    <tr>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;width:140px;border-right:1px solid #ccc;">Course Code & Title:</td>
                        <td style="padding:7px 10px;font-size:11px;border-right:1px solid #ccc;">${cls.subject || ''}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;width:70px;border-right:1px solid #ccc;">Section:</td>
                        <td style="padding:7px 10px;font-size:11px;">${cls.section || ''}</td>
                    </tr>
                    <tr style="border-top:1px solid #ccc;">
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Assigned Faculty:</td>
                        <td style="padding:7px 10px;font-size:11px;font-weight:600;border-right:1px solid #ccc;">${faculty.toUpperCase()}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Date:</td>
                        <td style="padding:7px 10px;font-size:11px;">${dispDate}</td>
                    </tr>
                    <tr style="border-top:1px solid #ccc;">
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Venue / Room:</td>
                        <td style="padding:7px 10px;font-size:11px;border-right:1px solid #ccc;">${roomVal}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Time:</td>
                        <td style="padding:7px 10px;font-size:11px;">${timeVal}</td>
                    </tr>
                </table>
                <!-- Attendance Table -->
                <p style="font-size:11px;font-weight:800;color:#D32F2F;margin:16px 0 6px;">Attendance Log</p>
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#D32F2F;color:white;">
                            <th style="padding:7px 4px;font-size:10px;text-align:center;width:30px;">#</th>
                            <th style="padding:7px 8px;font-size:10px;text-align:left;">Name</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:80px;">SR Code</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px;">Time In</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px;">Status</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:center;width:100px;">Signature</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${present.length + late.length === 0
                            ? '<tr><td colspan="6" style="text-align:center;padding:16px;color:#999;font-size:11px;">No students attended.</td></tr>'
                            : tableRows(present) + tableRows(late)}
                    </tbody>
                </table>
                ${absent.length > 0 ? `
                <p style="font-size:11px;font-weight:800;color:#757575;margin:16px 0 6px;">Absent Students</p>
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#757575;color:white;">
                            <th style="padding:7px 4px;font-size:10px;width:30px;">#</th>
                            <th style="padding:7px 8px;font-size:10px;text-align:left;">Name</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:120px;">SR Code</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>${absentRows}</tbody>
                </table>` : ''}
                <!-- Summary -->
                <div style="margin-top:16px;background:#FFEBEE;border:1px solid #D32F2F;border-radius:8px;padding:12px 16px;display:flex;gap:32px;">
                    <span style="font-size:11px;font-weight:700;">Total: <b>${records.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#388E3C;">Present: <b>${present.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#E65100;">Late: <b>${late.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#D32F2F;">Absent: <b>${absent.length}</b></span>
                </div>
                <!-- Signature -->
                <div style="margin-top:32px;">
                    <p style="font-size:10px;color:#777;margin-bottom:32px;">Prepared by:</p>
                    <div style="border-top:1px solid #333;width:200px;padding-top:6px;">
                        <p style="font-size:11px;font-weight:800;margin:0;">${faculty.toUpperCase()}</p>
                        <p style="font-size:9px;color:#777;margin:2px 0 0;">Faculty / Instructor</p>
                    </div>
                </div>
                <p style="font-size:8px;color:#999;text-align:center;margin-top:24px;border-top:1px solid #eee;padding-top:8px;">
                    Generated: ${new Date().toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'})} | Attendance Monitoring System | BatStateU-REC-ATT-11
                </p>
            </div>`;
        document.getElementById('docTitle').innerText = `Report: ${date} ${session_time ? session_time.substring(0,5) : ''}`;
        document.getElementById('docViewer').classList.remove('hidden');
    } catch(e) {
        alert('Could not load attendance record: ' + e.message);
    }
}

function downloadPDF(class_code, date, session_time) {
    const sParam = session_time ? `?session_time=${session_time}` : '';
    const session = JSON.parse(localStorage.getItem('active_session') || '{}');
    const url = `/api/download_pdf/${class_code}/${date}${sParam}`;
    // Open with auth header via fetch then blob download
    authFetch(url).then(r => r.blob()).then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `Attendance_${class_code}_${date}.pdf`;
        a.click();
    }).catch(() => window.open(url, '_blank'));


**--------------**


# added

**--------------**

// History state
let historySelectedClass    = null;   // class_code of selected folder
let historySelectedSession  = null;   // { date, session_time } of selected session
let historyClassSessions    = [];     // sessions for the selected class



**--------------**

    // Load all classes for the left panel


**--------------**

# // ── CORE CAMERA SESSION 

# removed
**--------------**

                class_code: currentOpenedFolder,
                section:    cls.section  || '',
                subject:    cls.subject  || '',
                room:       activeSchedule ? activeSchedule.room || '' : '',


**--------------**


# replaced
**--------------**
                class_code:   currentOpenedFolder,
                section:      cls.section  || '',
                subject:      cls.subject  || '',
                room:         activeSchedule ? activeSchedule.room || '' : '',
                session_time: sessionTime,



**--------------**



# added

**--------------**
        const sessionTime = new Date().toTimeString().substring(0, 8);



**---------------------------------------------------------**


# app.py

# API — CAMERA / ATTENDANCE 

# removed
**--------------**
    """Start webcam and reset attendance for a fresh session."""



**--------------**
    """Stop webcam and return the final scan log."""



**--------------**
    """Live scan log: {name: first_seen_unix_timestamp}."""



**--------------**



**--------------**
        class_code = data["class_code"],
        section    = data["section"],
        subject    = data["subject"],
        records    = data["records"],


**--------------**
    rows = db.get_recent_activity(limit=10)



**--------------**
    return jsonify(db.get_absence_counts())



**--------------**



# replaced
**--------------**



**--------------**
        class_code   = data["class_code"],
        section      = data["section"],
        subject      = data["subject"],
        records      = data["records"],
        session_time = data.get("session_time", _dt.now().strftime("%H:%M:%S")),



**--------------**

    instructor_id = get_current_instructor_id(request)
    rows = db.get_recent_activity(limit=10, instructor_id=instructor_id)


**--------------**

    instructor_id = get_current_instructor_id(request)
    return jsonify(db.get_absence_counts(instructor_id=instructor_id))


**--------------**


# added

**--------------**
    from datetime import datetime as _dt


**--------------**


#  PDF DOWNLOAD =------------------------------------------------ 

# ── SCHEDULE 

# removed
**--------------**
    cls     = db.get_class(class_code)
    records = db.get_attendance_session(class_code, date)



**--------------**

    schedules = db.get_schedules(class_code)
    room      = schedules[0]["room"] if schedules else "TBA"


**--------------**
        class_id = class_code,
        subject  = cls["subject"],
        section  = cls["section"],
        room     = room,
        date     = date,
        records  = records,



**--------------**


# replaced
**--------------**

    session_time = request.args.get("session_time")
    cls          = db.get_class(class_code)
    records      = db.get_attendance_session(class_code, date, session_time)


**--------------**
    class_schedules = db.get_schedules(class_code=class_code)
    if not class_schedules:
        class_schedules = db.get_schedules(instructor_id=get_current_instructor_id(request))
    room = class_schedules[0]["room"] if class_schedules else "TBA"
    time_str = class_schedules[0]["time"] if class_schedules else ""

    # Get instructor info for PDF header
    instructor_email = request.headers.get("X-Instructor-Email", "")
    instructor       = db.get_instructor_by_email(instructor_email)
    faculty_name     = instructor_email.split("@")[0].replace(".", " ").title() if instructor else "Instructor"



**--------------**

        class_id     = class_code,
        subject      = cls["subject"],
        section      = cls["section"],
        room         = room,
        date         = date,
        time_str     = time_str,
        faculty_name = faculty_name,
        records      = records,


**--------------**

# API — SESSIONS LIST (for script.js renderHistoryPage)----------------------------------------


# removed
**--------------**
    rows = db.get_all_sessions()



**--------------**
    rows = db.get_attendance_session(class_code, date)



**--------------**


# replaced
**--------------**

    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_sessions(instructor_id=instructor_id)
    return jsonify([dict(r) for r in rows])


@app.route("/api/sessions/<class_code>", methods=["GET"])
def api_get_sessions_by_class(class_code):
    """All attendance sessions for one class folder."""
    rows = db.get_sessions_by_class(class_code)


**--------------**

    session_time = request.args.get("session_time")
    rows = db.get_attendance_session(class_code, date, session_time)


**-----------------------------------------------**

**database.p**

# ──── INIT -----------------------------------

# removed
**--------------**
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code     VARCHAR(50),
            name        VARCHAR(50)  NOT NULL,
            section     VARCHAR(50),
            subject     VARCHAR(50),
            status      VARCHAR(20)  NOT NULL,
            timestamp   TIMESTAMP(0) DEFAULT NOW(),
            date        DATE         NOT NULL



**--------------**



**--------------**



# replaced
**--------------**

            id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code   VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code      VARCHAR(50),
            name         VARCHAR(50)  NOT NULL,
            section      VARCHAR(50),
            subject      VARCHAR(50),
            status       VARCHAR(20)  NOT NULL,
            timestamp    TIMESTAMP(0) DEFAULT NOW(),
            date         DATE         NOT NULL,
            session_time VARCHAR(20)  DEFAULT '00:00:00'


**--------------**

# added

**--------------**
    # Add session_time column if upgrading existing DB
    try:
        cur.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS session_time VARCHAR(20) DEFAULT '00:00:00'")
    except Exception:
        pass


**--------------**


# ── ATTENDANCE ------------------------------ 

# removed
**--------------**
def save_attendance(class_code, section, subject, records, date=None):



**--------------**
    records = list of dicts:
        [
            {"name": "JohnDoe", "sr_code": "2021-0001",
             "status": "Present", "timestamp": "07:02:34"},
            ...
        ]
    Deletes existing records for this class+date before inserting
    so the teacher can re-save without duplicates.



**--------------**
    # Remove existing records for this session (allow re-save)



**--------------**
        "DELETE FROM attendance WHERE class_code = %s AND date = %s",
        (class_code, date)



**--------------**
               (class_code, sr_code, name, section, subject, status, timestamp, date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",


**--------------**
                full_timestamp,   # "2026-03-16 07:02:34" — actual scan time
                date



**--------------**
def get_attendance_session(class_code, date):
    """All attendance rows for one class on one date, sorted Present→Late→Absent."""



**--------------**

    cur.execute(
        """SELECT * FROM attendance
           WHERE class_code = %s AND date = %s
           ORDER BY
             CASE status
               WHEN 'Present' THEN 1
               WHEN 'Late'    THEN 2
               WHEN 'Absent'  THEN 3
             END,
             name""",
        (class_code, date)
    )


**--------------**

    """One row per (class_code, date) — for the History page list."""


**--------------**
                   a.class_code,
                   a.date,
                   a.section,
                   a.subject,
                   COUNT(*)                                          AS total,


**--------------**
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC""",



**--------------**
                   a.class_code,
                   a.date,
                   a.section,
                   a.subject,
                   COUNT(*)                                          AS total,



**--------------**
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC"""



**--------------**

            """SELECT
                   a.class_code,
                   a.date,
                   a.section,
                   a.subject,
                   MIN(a.timestamp::text) AS time


**--------------**
               GROUP BY a.class_code, a.date, a.section, a.subject
               ORDER BY a.date DESC, time DESC


**--------------**

            """SELECT
                   class_code,
                   date,
                   section,
                   subject,
                   MIN(timestamp::text) AS time


**--------------**

               GROUP BY class_code, date, section, subject
               ORDER BY date DESC, time DESC


**--------------**

               GROUP BY a.name
               ORDER BY count DESC""",


**--------------**

            """SELECT name, COUNT(*) AS count
               FROM attendance
               WHERE status = 'Absent'
               GROUP BY name
               ORDER BY count DESC"""


**--------------**




# replaced
**--------------**

def save_attendance(class_code, section, subject, records, date=None, session_time=None):


**--------------**

    records = list of dicts: {"name", "sr_code", "status", "timestamp"}
    Each call creates a new session identified by date + session_time.
    Multiple sessions per day are supported.


**--------------**

    # Delete only if exact same session_time (prevents overwrite of other sessions)


**--------------**

        "DELETE FROM attendance WHERE class_code = %s AND date = %s AND session_time = %s",
        (class_code, date, session_time)


**--------------**
               (class_code, sr_code, name, section, subject, status, timestamp, date, session_time)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",


**--------------**

                full_timestamp,
                date,
                session_time


**--------------**
def get_attendance_session(class_code, date, session_time=None):
    """All attendance rows for one session, sorted Present→Late→Absent."""



**--------------**
    if session_time:
        cur.execute(
            """SELECT * FROM attendance
               WHERE class_code = %s AND date = %s AND session_time = %s
               ORDER BY
                 CASE status WHEN 'Present' THEN 1 WHEN 'Late' THEN 2 ELSE 3 END, name""",
            (class_code, date, session_time)
        )
    else:
        cur.execute(
            """SELECT * FROM attendance
               WHERE class_code = %s AND date = %s
               ORDER BY
                 CASE status WHEN 'Present' THEN 1 WHEN 'Late' THEN 2 ELSE 3 END, name""",
            (class_code, date)
        )



**--------------**
    """One row per session (class_code + date + session_time)."""



**--------------**
                   a.class_code, a.date, a.session_time, a.section, a.subject,
                   COUNT(*)                                             AS total,


**--------------**
               GROUP BY a.class_code, a.date, a.session_time, a.section, a.subject
               ORDER BY a.date DESC, a.session_time DESC""",



**--------------**
                   a.class_code, a.date, a.session_time, a.section, a.subject,
                   COUNT(*)                                             AS total,



**--------------**
               GROUP BY a.class_code, a.date, a.session_time, a.section, a.subject
               ORDER BY a.date DESC, a.session_time DESC"""



**--------------**

            """SELECT a.class_code, a.date, a.session_time, a.section, a.subject,
                      MIN(a.timestamp::text) AS time


**--------------**

               GROUP BY a.class_code, a.date, a.session_time, a.section, a.subject
               ORDER BY a.date DESC, a.session_time DESC



**--------------**
            """SELECT class_code, date, session_time, section, subject,
                      MIN(timestamp::text) AS time



**--------------**
               GROUP BY class_code, date, session_time, section, subject
               ORDER BY date DESC, session_time DESC



**--------------**
               GROUP BY a.name ORDER BY count DESC""",



**--------------**

            """SELECT name, COUNT(*) AS count FROM attendance
               WHERE status = 'Absent' GROUP BY name ORDER BY count DESC"""


**--------------**


# added

**--------------**

    if session_time is None:
        session_time = datetime.now().strftime("%H:%M:%S")


**--------------**
 def get_sessions_by_class(class_code):
    """All sessions for one class folder, newest first."""
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute(
        """SELECT
               a.class_code, a.date, a.session_time, a.section, a.subject,
               COUNT(*)                                             AS total,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status='Late'    THEN 1 ELSE 0 END) AS late,
               SUM(CASE WHEN a.status='Absent'  THEN 1 ELSE 0 END) AS absent
           FROM attendance a
           WHERE a.class_code = %s
           GROUP BY a.class_code, a.date, a.session_time, a.section, a.subject
           ORDER BY a.date DESC, a.session_time DESC""",
        (class_code,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows





**--------------**


============================================================================================================================
# ── fixing the bug in schedule panel 


**script.js**


# // ── ON LOAD  ---------------------------------------

# removed
**--------------**
        window.location.href = "login.html";



**--------------**





# replaced
**--------------**
        window.location.href = "/";



**--------------**


# ── HISTORY -----------------------------------------------

# removed
**--------------**
let historySelectedClass    = null;   // class_code of selected folder
let historySelectedSession  = null;   // { date, session_time } of selected session
let historyClassSessions    = [];     // sessions for the selected class



**--------------**
    // Load all classes for the left panel



**--------------**
        <div class="relative mb-8">



**--------------**
            <div class="w-64 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">



**--------------**

                ${filtered.length === 0 ? '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No classes yet</p>' :
                  filtered.map(f => `
                    <div onclick="historySelectClass('${f.id}')"
                         class="p-4 rounded-2xl cursor-pointer transition border ${historySelectedClass === '${f.id}' ? 'bg-red-50 border-[#D32F2F]' : 'bg-white border-gray-100 hover:border-red-200'}">
                        <div class="flex items-center space-x-3">
                            <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${historySelectedClass === '${f.id}' ? 'bg-[#D32F2F] text-white' : 'bg-gray-100 text-gray-400'}">
                                <i data-lucide="folder" class="w-4 h-4"></i>
                            </div>
                            <div class="min-w-0">
                                <p class="font-black text-gray-900 text-sm truncate">${f.subject}</p>
                                <p class="text-[9px] text-gray-400 font-bold uppercase truncate">${f.section}</p>



**--------------**
                        </div>
                    </div>`).join('')}



**--------------**

            <!-- Column 2: Attendance Files for selected class -->
            <div class="w-64 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">


**--------------**
            <!-- Column 3: Session Detail + View & Print -->



**--------------**
            await historyLoadDetail(historySelectedSession.class_code,
                                    historySelectedSession.date,
                                    historySelectedSession.session_time);



**--------------**
        listEl.innerHTML = '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No attendance records yet</p>';


**--------------**
    listEl.innerHTML = historyClassSessions.map((s, i) => {



**--------------**
                        <p class="text-[9px] text-gray-400 font-bold">${dispTime} • P:${s.present} L:${s.late} A:${s.absent}</p>



**--------------**
    // Re-render files list to highlight active
    await historyLoadFiles(class_code);



**--------------**
        const url = `/api/attendance/${class_code}/${date}` + (session_time ? `?session_time=${session_time}` : '');
        const res     = await authFetch(url);



**--------------**
        const dispTime= session_time ? session_time.substring(0,5) : '';


**--------------**

            ? `<p class="text-[10px] text-gray-300 font-bold py-2 pl-2">None</p>`


**--------------**

                    <p class="text-[10px] text-gray-400 font-bold uppercase">${cls.section || ''} • ${dispDate} • ${dispTime}</p>


**--------------**

            <div class="space-y-4 overflow-y-auto">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Present (${present.length})</p>
                ${renderRows(present,'text-green-500','Present')}
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Late (${late.length})</p>
                ${renderRows(late,'text-yellow-500','Late')}
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Absent (${absent.length})</p>
                ${renderRows(absent,'text-red-500','Absent')}
            </div>`;


**--------------**

        panel.innerHTML = `<p class="text-center text-gray-300 font-bold py-8 text-xs">Could not load records.</p>`;


**--------------**
        if (isNaN(d)) return s.substring(11,16) || s;


**--------------**
    const sParam = session_time ? `?session_time=${session_time}` : '';



**--------------**
    // Fetch records to render in-page preview



**--------------**
        const res     = await authFetch(`/api/attendance/${class_code}/${date}${sParam}`);



**--------------**

        const faculty = (session.email || '').split('@')[0].replace(/[._]/g,' ')
                        .replace(/\w/g, l => l.toUpperCase());

        const statusColor = s => s === 'Present' ? '#388E3C' : s === 'Late' ? '#E65100' : '#D32F2F';


**--------------**
        const tableRows = (list) => list.map((r, i) => `
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:6px 4px;font-size:11px;">${i+1}.</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:600;">${r.name}</td>
                <td style="padding:6px 4px;font-size:11px;">${r.sr_code || ''}</td>
                <td style="padding:6px 4px;font-size:11px;">${formatDisplayTime(r.timestamp)}</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:700;color:${statusColor(r.status)}">${r.status}</td>
                <td style="padding:6px 4px;font-size:11px;border-bottom:1px solid #ccc;min-width:80px;"></td>



**--------------**

        const absentRows = absent.map((r, i) => `
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:6px 4px;font-size:11px;">${i+1}.</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:600;">${r.name}</td>
                <td style="padding:6px 4px;font-size:11px;">${r.sr_code || ''}</td>
                <td style="padding:6px 4px;font-size:11px;color:#D32F2F;font-weight:700;">ABSENT</td>



**--------------**
            <div style="max-width:760px;margin:0 auto;background:white;padding:32px;font-family:'Segoe UI',sans-serif;">
                <!-- Header -->
                <table style="width:100%;border-collapse:collapse;border:1px solid #333;">



**--------------**
                        <td style="width:120px;padding:12px;text-align:center;border-right:1px solid #ccc;">
                            <div style="width:60px;height:60px;background:#f5f5f5;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:9px;color:#999;text-align:center;">BSU LOGO</div>



**--------------**
                        <td style="padding:12px;text-align:center;border-right:1px solid #ccc;">
                            <p style="font-size:11px;font-weight:800;margin:0;">Batangas State University</p>
                            <p style="font-size:10px;font-weight:700;margin:2px 0;">ARASOF-Nasugbu Campus</p>
                            <p style="font-size:13px;font-weight:900;color:#D32F2F;margin:6px 0 2px;">ATTENDANCE SHEET</p>
                            <p style="font-size:10px;margin:0;color:#555;">Student Class Attendance</p>



**--------------**
                        <td style="padding:10px;font-size:9px;color:#666;vertical-align:top;min-width:140px;">


**--------------**
                            <div style="margin-top:4px;">Effectivity: <b>January 3, 2017</b></div>
                            <div style="margin-top:4px;">Revision No.: <b>00</b></div>



**--------------**
                <!-- Info -->
                <table style="width:100%;border-collapse:collapse;border:1px solid #333;border-top:none;">



**--------------**
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;width:140px;border-right:1px solid #ccc;">Course Code & Title:</td>
                        <td style="padding:7px 10px;font-size:11px;border-right:1px solid #ccc;">${cls.subject || ''}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;width:70px;border-right:1px solid #ccc;">Section:</td>
                        <td style="padding:7px 10px;font-size:11px;">${cls.section || ''}</td>



**--------------**
                    <tr style="border-top:1px solid #ccc;">
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Assigned Faculty:</td>
                        <td style="padding:7px 10px;font-size:11px;font-weight:600;border-right:1px solid #ccc;">${faculty.toUpperCase()}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Date:</td>
                        <td style="padding:7px 10px;font-size:11px;">${dispDate}</td>



**--------------**
                    <tr style="border-top:1px solid #ccc;">
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Venue / Room:</td>
                        <td style="padding:7px 10px;font-size:11px;border-right:1px solid #ccc;">${roomVal}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc;">Time:</td>
                        <td style="padding:7px 10px;font-size:11px;">${timeVal}</td>


**--------------**

                <!-- Attendance Table -->
                <p style="font-size:11px;font-weight:800;color:#D32F2F;margin:16px 0 6px;">Attendance Log</p>
                <table style="width:100%;border-collapse:collapse;">


**--------------**
                        <tr style="background:#D32F2F;color:white;">
                            <th style="padding:7px 4px;font-size:10px;text-align:center;width:30px;">#</th>
                            <th style="padding:7px 8px;font-size:10px;text-align:left;">Name</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:80px;">SR Code</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px;">Time In</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px;">Status</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:center;width:100px;">Signature</th>



**--------------**
                            ? '<tr><td colspan="6" style="text-align:center;padding:16px;color:#999;font-size:11px;">No students attended.</td></tr>'



**--------------**
                <p style="font-size:11px;font-weight:800;color:#757575;margin:16px 0 6px;">Absent Students</p>
                <table style="width:100%;border-collapse:collapse;">



**--------------**
                        <tr style="background:#757575;color:white;">
                            <th style="padding:7px 4px;font-size:10px;width:30px;">#</th>
                            <th style="padding:7px 8px;font-size:10px;text-align:left;">Name</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:120px;">SR Code</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px;">Status</th>


**--------------**
                <!-- Summary -->
                <div style="margin-top:16px;background:#FFEBEE;border:1px solid #D32F2F;border-radius:8px;padding:12px 16px;display:flex;gap:32px;">
                    <span style="font-size:11px;font-weight:700;">Total: <b>${records.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#388E3C;">Present: <b>${present.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#E65100;">Late: <b>${late.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#D32F2F;">Absent: <b>${absent.length}</b></span>



**--------------**
                <!-- Signature -->
                <div style="margin-top:32px;">
                    <p style="font-size:10px;color:#777;margin-bottom:32px;">Prepared by:</p>
                    <div style="border-top:1px solid #333;width:200px;padding-top:6px;">
                        <p style="font-size:11px;font-weight:800;margin:0;">${faculty.toUpperCase()}</p>
                        <p style="font-size:9px;color:#777;margin:2px 0 0;">Faculty / Instructor</p>



**--------------**
                <p style="font-size:8px;color:#999;text-align:center;margin-top:24px;border-top:1px solid #eee;padding-top:8px;">



**--------------**
        document.getElementById('docTitle').innerText = `Report: ${date} ${session_time ? session_time.substring(0,5) : ''}`;



**--------------**
        alert('Could not load attendance record: ' + e.message);


**--------------**
    const sParam = session_time ? `?session_time=${session_time}` : '';
    const session = JSON.parse(localStorage.getItem('active_session') || '{}');
    const url = `/api/download_pdf/${class_code}/${date}${sParam}`;
    // Open with auth header via fetch then blob download
    authFetch(url).then(r => r.blob()).then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `Attendance_${class_code}_${date}.pdf`;
        a.click();
    }).catch(() => window.open(url, '_blank'));
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



**--------------**



# replaced
**--------------**
let historySelectedClass   = null;
let historySelectedSession = null;
let historyClassSessions   = [];



**--------------**



**--------------**

        <div class="relative mb-6">


**--------------**

            <div class="w-60 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">


**--------------**
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


**--------------**

                        </div>`).join('')}


**--------------**

            <!-- Column 2: Attendance Files -->
            <div class="w-60 flex-shrink-0 space-y-3 overflow-y-auto pr-2 border-r border-gray-100">


**--------------**

            <!-- Column 3: Detail panel -->


**--------------**



**--------------**
            await historyLoadDetail(
                historySelectedSession.class_code,
                historySelectedSession.date,
                historySelectedSession.session_time
            );


**--------------**
        listEl.innerHTML = '<p class="text-[10px] text-gray-300 font-bold text-center py-8">No records yet</p>';



**--------------**
    listEl.innerHTML = historyClassSessions.map(s => {



**--------------**
                        <p class="text-[9px] text-gray-400 font-bold">${dispTime} · P:${s.present} L:${s.late} A:${s.absent}</p>



**--------------**



**--------------**
        const sp      = session_time ? `?session_time=${encodeURIComponent(session_time)}` : '';
        const res     = await authFetch(`/api/attendance/${class_code}/${date}${sp}`);


**--------------**



**--------------**
            ? '<p class="text-[10px] text-gray-300 font-bold py-2 pl-2">None</p>'

**--------------**

                    <p class="text-[10px] text-gray-400 font-bold uppercase">${cls.section || ''} · ${dispDate}</p>


**--------------**
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Present (${present.length})</p>
            ${renderRows(present,'text-green-500','Present')}
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Late (${late.length})</p>
            ${renderRows(late,'text-yellow-500','Late')}
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-4">Absent (${absent.length})</p>
            ${renderRows(absent,'text-red-500','Absent')}`;



**--------------**
        panel.innerHTML = '<p class="text-center text-gray-300 font-bold py-8 text-xs">Could not load records.</p>';



**--------------**
        if (isNaN(d.getTime())) return s.substring(11,16) || s;


**--------------**
    const sp     = session_time ? `?session_time=${encodeURIComponent(session_time)}` : '';


**--------------**



**--------------**

        const res     = await authFetch(`/api/attendance/${class_code}/${date}${sp}`);


**--------------**

        const faculty = (session.email || '').split('@')[0]
                          .replace(/[._]/g,' ').replace(/\b\w/g, l => l.toUpperCase());


**--------------**
        const sc = s => s === 'Present' ? '#388E3C' : s === 'Late' ? '#E65100' : '#D32F2F';
        const tableRows = list => list.map((r,i) => `
            <tr style="border-bottom:1px solid #eee">
                <td style="padding:6px 4px;font-size:11px">${i+1}.</td>
                <td style="padding:6px 8px;font-size:11px;font-weight:600">${r.name}</td>
                <td style="padding:6px 4px;font-size:11px">${r.sr_code||''}</td>
                <td style="padding:6px 4px;font-size:11px">${formatDisplayTime(r.timestamp)}</td>
                <td style="padding:6px 4px;font-size:11px;font-weight:700;color:${sc(r.status)}">${r.status}</td>
                <td style="padding:6px 4px;font-size:11px;border-bottom:1px solid #ccc;min-width:80px"></td>

**--------------**
        const absentRows = absent.map((r,i) => `
            <tr style="border-bottom:1px solid #eee">
                <td style="padding:6px 4px;font-size:11px">${i+1}.</td>
                <td style="padding:6px 8px;font-size:11px;font-weight:600">${r.name}</td>
                <td style="padding:6px 4px;font-size:11px">${r.sr_code||''}</td>
                <td style="padding:6px 4px;font-size:11px;color:#D32F2F;font-weight:700">ABSENT</td>



**--------------**

            <div style="max-width:760px;margin:0 auto;background:white;padding:32px;font-family:'Segoe UI',sans-serif">
                <table style="width:100%;border-collapse:collapse;border:1px solid #333">


**--------------**
                        <td style="width:110px;padding:12px;text-align:center;border-right:1px solid #ccc">
                            <div style="width:56px;height:56px;background:#f5f5f5;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:8px;color:#999;text-align:center">BSU<br>LOGO</div>



**--------------**
                        <td style="padding:12px;text-align:center;border-right:1px solid #ccc">
                            <p style="font-size:11px;font-weight:800;margin:0">Batangas State University</p>
                            <p style="font-size:10px;font-weight:700;margin:2px 0">ARASOF-Nasugbu Campus</p>
                            <p style="font-size:14px;font-weight:900;color:#D32F2F;margin:6px 0 2px">ATTENDANCE SHEET</p>
                            <p style="font-size:10px;margin:0;color:#555">Student Class Attendance</p>



**--------------**
                        <td style="padding:10px;font-size:9px;color:#666;vertical-align:top;min-width:140px">


**--------------**
                            <div style="margin-top:4px">Effectivity: <b>January 3, 2017</b></div>
                            <div style="margin-top:4px">Revision No.: <b>00</b></div>



**--------------**
                <table style="width:100%;border-collapse:collapse;border:1px solid #333;border-top:none">



**--------------**
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;width:140px;border-right:1px solid #ccc">Course Code &amp; Title:</td>
                        <td style="padding:7px 10px;font-size:11px;border-right:1px solid #ccc">${cls.subject||''}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;width:70px;border-right:1px solid #ccc">Section:</td>
                        <td style="padding:7px 10px;font-size:11px">${cls.section||''}</td>



**--------------**
                    <tr style="border-top:1px solid #ccc">
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc">Assigned Faculty:</td>
                        <td style="padding:7px 10px;font-size:11px;font-weight:600;border-right:1px solid #ccc">${faculty.toUpperCase()}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc">Date:</td>
                        <td style="padding:7px 10px;font-size:11px">${dispDate}</td>



**--------------**
                    <tr style="border-top:1px solid #ccc">
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc">Venue / Room:</td>
                        <td style="padding:7px 10px;font-size:11px;border-right:1px solid #ccc">${roomVal}</td>
                        <td style="padding:7px 10px;font-size:10px;font-weight:700;border-right:1px solid #ccc">Time:</td>
                        <td style="padding:7px 10px;font-size:11px">${timeVal}</td>


**--------------**

                <p style="font-size:11px;font-weight:800;color:#D32F2F;margin:16px 0 6px">Attendance Log</p>
                <table style="width:100%;border-collapse:collapse">


**--------------**

                        <tr style="background:#D32F2F;color:white">
                            <th style="padding:7px 4px;font-size:10px;text-align:center;width:30px">#</th>
                            <th style="padding:7px 8px;font-size:10px;text-align:left">Name</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:80px">SR Code</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px">Time In</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px">Status</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:center;width:100px">Signature</th>



**--------------**
                            ? '<tr><td colspan="6" style="text-align:center;padding:16px;color:#999;font-size:11px">No students attended.</td></tr>'



**--------------**

                <p style="font-size:11px;font-weight:800;color:#757575;margin:16px 0 6px">Absent Students</p>
                <table style="width:100%;border-collapse:collapse">


**--------------**

                        <tr style="background:#757575;color:white">
                            <th style="padding:7px 4px;font-size:10px;width:30px">#</th>
                            <th style="padding:7px 8px;font-size:10px;text-align:left">Name</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:120px">SR Code</th>
                            <th style="padding:7px 4px;font-size:10px;text-align:left;width:70px">Status</th>


**--------------**

                <div style="margin-top:16px;background:#FFEBEE;border:1px solid #D32F2F;border-radius:8px;padding:12px 16px;display:flex;gap:32px">
                    <span style="font-size:11px;font-weight:700">Total: <b>${records.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#388E3C">Present: <b>${present.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#E65100">Late: <b>${late.length}</b></span>
                    <span style="font-size:11px;font-weight:700;color:#D32F2F">Absent: <b>${absent.length}</b></span>


**--------------**

                <div style="margin-top:32px">
                    <p style="font-size:10px;color:#777;margin-bottom:32px">Prepared by:</p>
                    <div style="border-top:1px solid #333;width:200px;padding-top:6px">
                        <p style="font-size:11px;font-weight:800;margin:0">${faculty.toUpperCase()}</p>
                        <p style="font-size:9px;color:#777;margin:2px 0 0">Faculty / Instructor</p>


**--------------**

                <p style="font-size:8px;color:#999;text-align:center;margin-top:24px;border-top:1px solid #eee;padding-top:8px">


**--------------**

        document.getElementById('docTitle').innerText = `Report: ${date}`;


**--------------**
        alert('Could not load record: ' + e.message);


**--------------**
    const sp = session_time ? `?session_time=${encodeURIComponent(session_time)}` : '';
    authFetch(`/api/download_pdf/${class_code}/${date}${sp}`)
        .then(r => r.blob())
        .then(blob => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `Attendance_${class_code}_${date}.pdf`;
            a.click();
        }).catch(() => window.open(`/api/download_pdf/${class_code}/${date}${sp}`, '_blank'));



**--------------**








# added

**--------------**
    await historyLoadFiles(class_code);



**--------------**

    historySelectedClass = class_code;


**---------------------------------------------------------**

# // ── SCHEDULE---------------------------------------



# removed
**--------------**
        await fetch('/api/schedules', {



**--------------**



# replaced
**--------------**

        await authFetch('/api/schedules', {


**--------------**


# added
**--------------**
    selectedDay = payload.day;



**--------------**

# // ── CORE CAMERA SESSION 


# removed
**--------------**
        const sessionTime = new Date().toTimeString().substring(0, 8);


**--------------**
                class_code:   currentOpenedFolder,
                section:      cls.section  || '',
                subject:      cls.subject  || '',
                room:         activeSchedule ? activeSchedule.room || '' : '',
                session_time: sessionTime,




# replaced
**--------------**
                                class_code: currentOpenedFolder,
                section:    cls.section  || '',
                subject:    cls.subject  || '',
                room:       activeSchedule ? activeSchedule.room || '' : '',




**------------------------------------------------------------------------------------**

# // ── CONFIRM DIALOG (unchanged logic, updated backend calls)

# removed
**--------------**
            window.location.href = "login.html";


**--------------**




# replaced
**--------------**
            window.location.href = "/";



**--------------**
============================================================================================================================
# ── fixing the setup class modal  

# // ── SCHEDULE CHECK MODAL ---------------------------------------------

# removed
**--------------**

    // Remove existing modal if any


**--------------**

                <button onclick="document.getElementById('scheduleWarningModal').remove(); showMakeupScheduleModal(
                    ${JSON.stringify(cls)},
                    ${JSON.stringify(classSchedule)},
                    function(){ startCameraSession(${JSON.stringify(cls)}, _customSchedule); }
                )"


**--------------**


# replaced
**--------------**



**--------------**
                <button onclick="_onMakeupConfirmed()"


**--------------**

# added

**--------------**

    // Store data safely — avoids embedding JSON in onclick attributes
    window._warningCls      = cls;
    window._warningSchedule = classSchedule;



**--------------**

function _onMakeupConfirmed() {
    const cls           = window._warningCls;
    const classSchedule = window._warningSchedule;
    document.getElementById('scheduleWarningModal').remove();
    showMakeupScheduleModal(cls, classSchedule, () => startCameraSession(cls, _customSchedule));
}



**--------------**

=================================================================================================================================

# adding the unabled/gray open camera button and error mesages in registration students


**script.js**


# // ── FOLDER VIEW (inside a class) 

# removed
**--------------**

    // Get class info from already-loaded classFolders



**--------------**

            <div class="flex space-x-3">
                <button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-[10px] font-black uppercase">Registration</button>
                <button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2">
                    <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>
                </button>
            </div>


**--------------**
    // Load students from backend



**--------------**
        const area     = document.getElementById('studentListArea');
        if (students.length === 0) {
            area.innerHTML = `<div class="mt-10 text-center py-20 border-2 border-dashed border-gray-100 rounded-[3rem] text-gray-300 font-bold uppercase text-[10px]">No students yet. Click Registration to add.</div>`;



**--------------**




# replaced
**--------------**



**--------------**



**--------------**

    // Load students FIRST — then render camera button based on count


**--------------**
        const hasStudents = students.length > 0;

        // Now render the action buttons knowing if students exist
        const actionButtons = `
            <div class="flex space-x-3">
                <button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-[10px] font-black uppercase hover:bg-gray-200 transition">Registration</button>
                ${hasStudents
                    ? `<button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 hover:bg-gray-800 transition">
                            <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>
                       </button>`
                    : `<button disabled title="Register at least one student before scanning"
                            class="bg-gray-200 text-gray-400 px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 cursor-not-allowed opacity-60">
                            <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>
                       </button>`
                }
            </div>`;

        // Inject buttons into the header
        document.querySelector('#content-area > div:first-child').insertAdjacentHTML('beforeend', actionButtons);
        lucide.createIcons();

        const area = document.getElementById('studentListArea');
        if (!hasStudents) {
            area.innerHTML = `
                <div class="mt-10 text-center py-20 border-2 border-dashed border-gray-100 rounded-[3rem]">
                    <i data-lucide="user-x" class="w-10 h-10 text-gray-200 mx-auto mb-4"></i>
                    <p class="text-gray-300 font-bold uppercase text-[10px]">No students yet.</p>
                    <p class="text-gray-300 text-[9px] mt-1">Click <b>Registration</b> to add students before opening the camera.</p>
                </div>`;
            lucide.createIcons();



**--------------**


# added

**--------------**

    // Show loading state first


**--------------**


# // ── STUDENT REGISTRATION 

# removed
**--------------**
    // Ensure class_code is set (backup in case hidden field is empty)



**--------------**
            alert('Error: ' + (data.error || 'Failed to save student.'));



**--------------**
        openFolderView(currentOpenedFolder);  // reload student list


**--------------**
        alert('Failed to save student: ' + e.message);



**--------------**
# replaced


**--------------**
            showRegError([data.error || 'Failed to save student.']);



**--------------**
        openFolderView(currentOpenedFolder);



**--------------**
        showRegError(['Server error: ' + e.message]);
    }
}

function showRegError(errors) {
    // Remove old error box if present
    const old = document.getElementById('regErrorBox');
    if (old) old.remove();

    const box = document.createElement('div');
    box.id = 'regErrorBox';
    box.style.cssText = `
        background:#FFF5F5; border:1px solid #FCA5A5; border-radius:12px;
        padding:12px 16px; margin-bottom:16px; font-size:12px; color:#B91C1C;`;
    box.innerHTML = `
        <p style="font-weight:800;margin:0 0 6px">Please fix the following:</p>
        <ul style="margin:0;padding-left:16px;">
            ${errors.map(e => `<li style="margin-bottom:3px">${e}</li>`).join('')}
        </ul>`;

    // Insert before the first input in the form
    const form = document.getElementById('studentRegForm');
    if (form) {
        const firstInput = form.querySelector('input, select');
        if (firstInput) form.insertBefore(box, firstInput);
        else form.prepend(box);
        box.scrollIntoView({ behavior: 'smooth', block: 'center' });


**--------------**

# added
**--------------**

    // ── Frontend Validation ───────────────────────────────────────────────────
    const name    = (formData.get('name')   || '').trim();
    const srCode  = (formData.get('sr_code')|| '').trim();
    const phone   = (formData.get('number') || '').trim();
    const email   = (formData.get('email')  || '').trim();
    const photo   = formData.get('photo');
    const sig     = formData.get('signature');

    const errors = [];

    if (!name)                          errors.push('Full name is required.');
    if (!srCode)                        errors.push('SR Code is required.');
    if (!email || !email.includes('@')) errors.push('A valid email address is required.');

    // Phone: must be exactly 11 digits (digits only after stripping spaces/dashes)
    const phoneDigits = phone.replace(/[\s\-]/g, '');
    if (!phone) {
        errors.push('Contact number is required.');
    } else if (!/^0\d{10}$/.test(phoneDigits)) {
        errors.push('Contact number must be 11 digits starting with 0 (e.g. 09994408409).');
    }

    // Photo: required (face recognition needs it)
    if (!photo || photo.size === 0) {
        errors.push('Student photo (ID picture) is required for face recognition.');
    } else {
        const allowedTypes = ['image/jpeg','image/jpg','image/png'];
        if (!allowedTypes.includes(photo.type)) {
            errors.push('Photo must be a JPG or PNG image.');
        }
    }

    // Signature: required
    if (!sig || sig.size === 0) {
        errors.push('E-Signature image is required.');
    } else {
        const allowedTypes = ['image/jpeg','image/jpg','image/png'];
        if (!allowedTypes.includes(sig.type)) {
            errors.push('Signature must be a JPG or PNG image.');
        }
    }

    if (errors.length > 0) {
        showRegError(errors);
        return;
    }

    // ── Submit ────────────────────────────────────────────────────────────────



**--------------**

=================================================================================================================================

# issues:
# update of schedules in terms of day not changing
# when the schedule are going to delete there should a warning sign that indicates that, cannot be deleted, used schedule

**schedule moddiff issue js**

# // ── AUTHENTICATED FETCH --------------------------------------

# removed
**--------------**
let editIdx         = -1;
let editSchedId     = -1;



**--------------**


# replaced
**--------------**
let editIdx                 = -1;
let editSchedId             = -1;
let _editingSchedOldSubject = '';   // stores subject before edit for sync



**--------------**

# // ── FOLDER VIEW (inside a class)--------------------------- 

# removed

**--------------**


**--------------**
    // Show loading state first



**--------------**



**--------------**
        <div id="studentListArea" class="mt-10">
            <p class="text-center text-gray-300 font-bold py-4 text-xs">Loading students...</p>
        </div>`;



**--------------**
    // Load students FIRST — then render camera button based on count



**--------------**
        const res      = await authFetch(`/api/students/${class_code}`);
        const students = await res.json();
        const hasStudents = students.length > 0;

        // Now render the action buttons knowing if students exist
        const actionButtons = `
            <div class="flex space-x-3">
                <button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-[10px] font-black uppercase hover:bg-gray-200 transition">Registration</button>
                ${hasStudents
                    ? `<button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 hover:bg-gray-800 transition">
                            <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>
                       </button>`
                    : `<button disabled title="Register at least one student before scanning"
                            class="bg-gray-200 text-gray-400 px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 cursor-not-allowed opacity-60">
                            <i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span>
                       </button>`
                }
            </div>`;

        // Inject buttons into the header
        document.querySelector('#content-area > div:first-child').insertAdjacentHTML('beforeend', actionButtons);
        lucide.createIcons();

        const area = document.getElementById('studentListArea');
        if (!hasStudents) {
            area.innerHTML = `
                <div class="mt-10 text-center py-20 border-2 border-dashed border-gray-100 rounded-[3rem]">
                    <i data-lucide="user-x" class="w-10 h-10 text-gray-200 mx-auto mb-4"></i>
                    <p class="text-gray-300 font-bold uppercase text-[10px]">No students yet.</p>
                    <p class="text-gray-300 text-[9px] mt-1">Click <b>Registration</b> to add students before opening the camera.</p>
                </div>`;
            lucide.createIcons();


**--------------**



# replaced
**--------------**



**--------------**
    // Load students FIRST then render camera button based on count
    let students = [];
    try {
        const res = await authFetch(`/api/students/${class_code}`);
        students  = await res.json();
    } catch {}

    const hasStudents = students.length > 0;



**--------------**



**--------------**
        <div id="studentListArea" class="mt-10"></div>`;



**--------------**
    const area = document.getElementById('studentListArea');


**--------------**
        if (students.length === 0) {
            area.innerHTML = `<div class="mt-10 text-center py-20 border-2 border-dashed border-gray-100 rounded-[3rem]"><p class="text-gray-300 font-bold uppercase text-[10px]">No students yet. Click Registration to add.</p></div>`;



**--------------**


# added

**--------------**

    // Get class info from already-loaded classFolders



**--------------**
            <div class="flex space-x-3">
                <button onclick="openRegModal()" class="bg-gray-100 text-gray-600 px-8 py-4 rounded-2xl text-[10px] font-black uppercase hover:bg-gray-200 transition">Registration</button>
                ${hasStudents
                    ? `<button onclick="openCamera()" class="bg-black text-white px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 hover:bg-gray-800 transition"><i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span></button>`
                    : `<button disabled title="Register at least one student before scanning" class="bg-gray-200 text-gray-400 px-8 py-4 rounded-2xl text-[10px] font-black uppercase flex items-center space-x-2 cursor-not-allowed opacity-60"><i data-lucide="camera" class="w-4 h-4"></i> <span>Open Camera</span></button>`}
            </div>



**--------------**
# // ── SCHEDULE ------------------------

# removed
**--------------**
        class_code: currentOpenedFolder || null,
        subject:    document.getElementById('modalSubName').value,
        day:        document.getElementById('modalDaySelect').value,
        room:       document.getElementById('modalRoom').value,
        time:       document.getElementById('modalTimeFrom').value + ' - ' + document.getElementById('modalTimeTo').value,


**--------------**
 



**--------------**

   document.getElementById('modalSubName').value  = s.subject;
    document.getElementById('modalDaySelect').value = s.day;
    document.getElementById('modalRoom').value     = s.room;

# replaced

**--------------**
        class_code:  currentOpenedFolder || null,
        subject:     document.getElementById('modalSubName').value,
        day:         document.getElementById('modalDaySelect').value,
        room:        document.getElementById('modalRoom').value,
        time:        document.getElementById('modalTimeFrom').value + ' - ' + document.getElementById('modalTimeTo').value,
        old_subject: _editingSchedOldSubject || '',   // for subject-sync on edit



**--------------**



**--------------**
    _editingSchedOldSubject = s.subject;   // store original subject for sync

    document.getElementById('modalSubName').value   = s.subject;
    document.getElementById('modalRoom').value      = s.room;
    document.getElementById('taskModalTitle').textContent = 'Edit Schedule';

    // Pre-fill day — must set AFTER modal is visible so the select renders
    const daySelect = document.getElementById('modalDaySelect');
    daySelect.value = s.day;
    // Force-select correct option in case value didn't match
    Array.from(daySelect.options).forEach(opt => {
        opt.selected = opt.value === s.day;
    });

    // Pre-fill time dropdowns
    const timeParts = (s.time || '').split(' - ');
    if (timeParts.length === 2) {
        const fromSel = document.getElementById('modalTimeFrom');
        const toSel   = document.getElementById('modalTimeTo');
        Array.from(fromSel.options).forEach(opt => { opt.selected = opt.value === timeParts[0].trim(); });
        Array.from(toSel.options).forEach(opt =>   { opt.selected = opt.value === timeParts[1].trim(); });
    }



**--------------**

# added

**--------------**
    _editingSchedOldSubject = '';



**--------------**
# // ── STUDENT REGISTRATION  

# removed


**--------------**

    if (!formData.get('class_code')) {
        formData.set('class_code', currentOpenedFolder);
    }

    // ── Frontend Validation ───────────────────────────────────────────────────
    const name    = (formData.get('name')   || '').trim();
    const srCode  = (formData.get('sr_code')|| '').trim();
    const phone   = (formData.get('number') || '').trim();
    const email   = (formData.get('email')  || '').trim();
    const photo   = formData.get('photo');
    const sig     = formData.get('signature');



**--------------**


**--------------**
    if (!name)                          errors.push('Full name is required.');
    if (!srCode)                        errors.push('SR Code is required.');



**--------------**
    // Phone: must be exactly 11 digits (digits only after stripping spaces/dashes)
    const phoneDigits = phone.replace(/[\s\-]/g, '');
    if (!phone) {
        errors.push('Contact number is required.');
    } else if (!/^0\d{10}$/.test(phoneDigits)) {
        errors.push('Contact number must be 11 digits starting with 0 (e.g. 09994408409).');
    }



**--------------**
    // Photo: required (face recognition needs it)
    if (!photo || photo.size === 0) {
        errors.push('Student photo (ID picture) is required for face recognition.');
    } else {
        const allowedTypes = ['image/jpeg','image/jpg','image/png'];
        if (!allowedTypes.includes(photo.type)) {
            errors.push('Photo must be a JPG or PNG image.');
        }
    }



**--------------**
    // Signature: required
    if (!sig || sig.size === 0) {
        errors.push('E-Signature image is required.');
    } else {
        const allowedTypes = ['image/jpeg','image/jpg','image/png'];
        if (!allowedTypes.includes(sig.type)) {
            errors.push('Signature must be a JPG or PNG image.');
        }
    }



**--------------**
    if (errors.length > 0) {
        showRegError(errors);
        return;
    }


**--------------**

    // ── Submit ────────────────────────────────────────────────────────────────



**--------------**
            method: 'POST',
            body: formData,



**--------------**
        if (!res.ok) {
            showRegError([data.error || 'Failed to save student.']);
            return;
        }



**--------------**
    } catch(e) {
        showRegError(['Server error: ' + e.message]);
    }



**--------------**
    // Remove old error box if present


**--------------**
    box.style.cssText = `
        background:#FFF5F5; border:1px solid #FCA5A5; border-radius:12px;
        padding:12px 16px; margin-bottom:16px; font-size:12px; color:#B91C1C;`;
    box.innerHTML = `
        <p style="font-weight:800;margin:0 0 6px">Please fix the following:</p>
        <ul style="margin:0;padding-left:16px;">
            ${errors.map(e => `<li style="margin-bottom:3px">${e}</li>`).join('')}
        </ul>`;

    // Insert before the first input in the form



**--------------**
    if (form) {
        const firstInput = form.querySelector('input, select');
        if (firstInput) form.insertBefore(box, firstInput);
        else form.prepend(box);
        box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

**--------------**


# replaced


**--------------**
    if (!formData.get('class_code')) formData.set('class_code', currentOpenedFolder);



**--------------**



**--------------**
    if (!name)  errors.push('Full name is required.');
    if (!sr)    errors.push('SR Code is required.');



**--------------**
    const digits = phone.replace(/[\s\-]/g, '');
    if (!phone)                         errors.push('Contact number is required.');
    else if (!/^0\d{10}$/.test(digits)) errors.push('Contact number must be 11 digits starting with 0 (e.g. 09994408409).');



**--------------**
    if (!photo || photo.size === 0)     errors.push('Student photo (ID picture) is required for face recognition.');
    else if (!['image/jpeg','image/jpg','image/png'].includes(photo.type))
                                        errors.push('Photo must be a JPG or PNG image.');



**--------------**
    if (!sig || sig.size === 0)         errors.push('E-Signature image is required.');
    else if (!['image/jpeg','image/jpg','image/png'].includes(sig.type))
                                        errors.push('Signature must be a JPG or PNG image.');


**--------------**
    if (errors.length > 0) { showRegError(errors); return; }



**--------------**
            method: 'POST', body: formData,



**--------------**
        if (!res.ok) { showRegError([data.error || 'Failed to save student.']); return; }



**--------------**
    } catch(e) { showRegError(['Server error: ' + e.message]); }



**--------------**
    box.style.cssText = 'background:#FFF5F5;border:1px solid #FCA5A5;border-radius:12px;padding:12px 16px;margin-bottom:16px;font-size:12px;color:#B91C1C;';
    box.innerHTML = `<p style="font-weight:800;margin:0 0 6px">Please fix the following:</p><ul style="margin:0;padding-left:16px;">${errors.map(e=>`<li style="margin-bottom:3px">${e}</li>`).join('')}</ul>`;


**--------------**
    if (form) { const first = form.querySelector('input,select'); if (first) form.insertBefore(box,first); else form.prepend(box); box.scrollIntoView({behavior:'smooth',block:'center'}); }



**--------------**

# added


**--------------**

    const name  = (formData.get('name')   || '').trim();
    const sr    = (formData.get('sr_code')|| '').trim();
    const phone = (formData.get('number') || '').trim();
    const email = (formData.get('email')  || '').trim();
    const photo = formData.get('photo');
    const sig   = formData.get('signature');


**--------------**

# // ── CONFIRM DIALOG (unchanged logic, updated backend calls) 

**--------------**

            // Check if any class folder is using this schedule first
            try {
                const usageRes  = await authFetch(`/api/schedules/${id}/check_usage`);
                const usedBy    = await usageRes.json();
                if (usedBy.length > 0) {
                    const classList = usedBy.map(f => `"${f.subject} — ${f.section}"`).join(', ');
                    closeConfirm();
                    showScheduleDeleteWarning(id, classList);
                    return;
                }
            } catch {}


**--------------**
function showScheduleDeleteWarning(scheduleId, classList) {
    // Show a specific warning modal when a schedule is used by class folders
    const existing = document.getElementById('scheduleDeleteWarnModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'scheduleDeleteWarnModal';
    modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-md z-[300] flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-[2rem] w-full max-w-md p-8 shadow-2xl">
            <div class="flex items-center space-x-3 mb-4">
                <div class="w-12 h-12 bg-yellow-100 rounded-2xl flex items-center justify-center text-yellow-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                    </svg>
                </div>
                <div>
                    <h2 class="text-xl font-black text-gray-900">Schedule In Use!</h2>
                    <p class="text-[10px] text-yellow-600 font-bold uppercase tracking-widest">Class folders are linked to this schedule</p>
                </div>
            </div>
            <div class="bg-yellow-50 border border-yellow-200 rounded-2xl p-4 mb-6 text-sm">
                <p class="text-gray-700 text-xs">The following class folder(s) are currently using this schedule:</p>
                <p class="font-black text-gray-900 mt-2">${classList}</p>
            </div>
            <p class="text-sm text-gray-500 mb-6">
                Deleting this schedule will <b>remove the time/room link</b> from those class folders.
                The folders themselves and their students will <b>not</b> be deleted.
                Are you sure you want to continue?
            </p>
            <div class="flex space-x-3">
                <button onclick="document.getElementById('scheduleDeleteWarnModal').remove()"
                    class="flex-1 py-4 text-gray-400 font-bold rounded-xl border border-gray-100 hover:bg-gray-50 transition">
                    Cancel — Keep Schedule
                </button>
                <button onclick="forceDeleteSchedule(${scheduleId})"
                    class="flex-1 py-4 bg-yellow-500 text-white font-bold rounded-xl shadow-lg hover:bg-yellow-600 transition">
                    Delete Anyway
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);
}

async function forceDeleteSchedule(id) {
    document.getElementById('scheduleDeleteWarnModal').remove();
    await authFetch(`/api/schedules/${id}`, { method: 'DELETE' });
    await loadSchedules();
    renderDayFilters();
}



**-------------------------------------------------------------------**


**schedule moddiff issue app**

# API — CAMERA / ATTENDANCE------------------------ 

# removed
**--------------**
@app.route("/api/start_camera", methods=["POST"])
def api_start_camera():
    global _camera_started, recognizer, known_enc, known_names
    try:
        if not _camera_started:
            recognizer = FaceRecognizer(known_enc, known_names)
            recognizer.start(0)
            _camera_started = True
        else:
            recognizer.reset_attendance()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stop_camera", methods=["POST"])
def api_stop_camera():
    global _camera_started
    try:
        scan_log = recognizer.get_scan_log()
        recognizer.stop_and_reset()
        _camera_started = False
        return jsonify({"status": "ok", "scan_log": scan_log})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan_log")
def api_scan_log():
    try:
        return jsonify(recognizer.get_scan_log())
    except Exception:
        return jsonify({})





**--------------**

    from datetime import datetime as _dt


**--------------**

        class_code   = data["class_code"],
        section      = data["section"],
        subject      = data["subject"],
        records      = data["records"],
        session_time = data.get("session_time", _dt.now().strftime("%H:%M:%S")),


**--------------**


**--------------**

# replaced

**--------------**



**--------------**



**--------------**
        class_code = data["class_code"],
        section    = data["section"],
        subject    = data["subject"],
        records    = data["records"],



**--------------**


# API — DASHBOARD

# removed
**--------------**
    instructor_id = get_current_instructor_id(request)
    rows = db.get_recent_activity(limit=10, instructor_id=instructor_id)


**--------------**
    instructor_id = get_current_instructor_id(request)
    return jsonify(db.get_absence_counts(instructor_id=instructor_id))



**--------------**
# replaced

**--------------**
    rows = db.get_recent_activity(limit=10)



**--------------**
    return jsonify(db.get_absence_counts())



**--------------**

# API — SCHEDULES ------------------------------------ 

# removed

**--------------**
    data = request.json
    db.edit_schedule(schedule_id, data["time"], data["subject"], data["room"])


**--------------**



# replaced

**--------------**
    data        = request.json
    old_subject = data.get("old_subject", "")
    new_subject = data["subject"]
    day         = data.get("day")

    db.edit_schedule(schedule_id, data["time"], new_subject, data["room"], day=day)

    # If subject name changed, sync linked class folders
    if old_subject and old_subject.strip().lower() != new_subject.strip().lower():
        db.update_class_subject_by_schedule(schedule_id, old_subject, new_subject)




**--------------**


# added
**--------------**
@app.route("/api/schedules/<int:schedule_id>/check_usage", methods=["GET"])
def api_check_schedule_usage(schedule_id):
    """Returns classes that use this schedule so frontend can warn before delete."""
    rows = db.get_classes_using_schedule(schedule_id)
    return jsonify([dict(r) for r in rows])





**--------------**
# PDF DOWNLOAD


# removed
**--------------**
    session_time = request.args.get("session_time")
    cls          = db.get_class(class_code)
    records      = db.get_attendance_session(class_code, date, session_time)



**--------------**
    class_schedules = db.get_schedules(class_code=class_code)
    if not class_schedules:
        class_schedules = db.get_schedules(instructor_id=get_current_instructor_id(request))
    room = class_schedules[0]["room"] if class_schedules else "TBA"
    time_str = class_schedules[0]["time"] if class_schedules else ""

    # Get instructor info for PDF header
    instructor_email = request.headers.get("X-Instructor-Email", "")
    instructor       = db.get_instructor_by_email(instructor_email)
    faculty_name     = instructor_email.split("@")[0].replace(".", " ").title() if instructor else "Instructor"



**--------------**
        class_id     = class_code,
        subject      = cls["subject"],
        section      = cls["section"],
        room         = room,
        date         = date,
        time_str     = time_str,
        faculty_name = faculty_name,
        records      = records,



**--------------**
# replaced

**--------------**

    cls     = db.get_class(class_code)
    records = db.get_attendance_session(class_code, date)


**--------------**
    schedules = db.get_schedules(class_code)
    room      = schedules[0]["room"] if schedules else "TBA"


**--------------**
        class_id = class_code,
        subject  = cls["subject"],
        section  = cls["section"],
        room     = room,
        date     = date,
        records  = records,



**--------------**

# API — SESSIONS LIST (for script.js renderHistoryPage) 

# removed

**--------------**
    instructor_id = get_current_instructor_id(request)
    rows = db.get_all_sessions(instructor_id=instructor_id)
    return jsonify([dict(r) for r in rows])


@app.route("/api/sessions/<class_code>", methods=["GET"])
def api_get_sessions_by_class(class_code):
    """All attendance sessions for one class folder."""
    rows = db.get_sessions_by_class(class_code)



**--------------**
# replaced

**--------------**

    rows = db.get_all_sessions()



**--------------**
# API — ATTENDANCE RECORDS FOR ONE SESSION

# removed


**--------------**
    session_time = request.args.get("session_time")
    rows = db.get_attendance_session(class_code, date, session_time)


**--------------**
# replaced


**--------------**
    rows = db.get_attendance_session(class_code, date)



**-------------------------------------------------------------**

**schedule moddiff issue db**


# ── INIT -----------------------------------------------------
# removed

**--------------**

            id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code   VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code      VARCHAR(50),
            name         VARCHAR(50)  NOT NULL,
            section      VARCHAR(50),
            subject      VARCHAR(50),
            status       VARCHAR(20)  NOT NULL,
            timestamp    TIMESTAMP(0) DEFAULT NOW(),
            date         DATE         NOT NULL,
            session_time VARCHAR(20)  DEFAULT '00:00:00'


**--------------**
    # Add session_time column if upgrading existing DB
    try:
        cur.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS session_time VARCHAR(20) DEFAULT '00:00:00'")
    except Exception:
        pass



**--------------**
# replaced


**--------------**
            id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            class_code  VARCHAR(50)  NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            sr_code     VARCHAR(50),
            name        VARCHAR(50)  NOT NULL,
            section     VARCHAR(50),
            subject     VARCHAR(50),
            status      VARCHAR(20)  NOT NULL,
            timestamp   TIMESTAMP(0) DEFAULT NOW(),
            date        DATE         NOT NULL


**--------------**

# ── ATTENDANCE -----------------------------

**--------------**

