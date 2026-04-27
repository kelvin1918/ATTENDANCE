const isMobile = () => window.innerWidth <= 768;

// --- INITIALIZE MOBILE VIEW ---
document.addEventListener('DOMContentLoaded', () => {
    if (isMobile()) {
        initializeMobileView();
    }
    
    // Listen for window resize to adapt
    window.addEventListener('resize', () => {
        if (isMobile()) {
            initializeMobileView();
        } else {
            restoreDesktopView();
        }
    });
});

function initializeMobileView() {
    // Hide desktop sidebar and adjust layout
    const navSidebar = document.getElementById('navSidebar');
    const mainContent = document.querySelector('main');
    const aside = document.querySelector('aside');
    const desktopSchedule = document.querySelector('aside:not(#navSidebar)');
    const editBtn = document.getElementById('editProfileBtn'); 
   
    if (editBtn) {
        editBtn.style.setProperty('display', 'flex', 'important');
        editBtn.style.setProperty('visibility', 'visible', 'important');
    }

    if (navSidebar) {
        navSidebar.classList.add('hidden');
    }
    
    if (mainContent) {
        mainContent.classList.remove('shadow-2xl');
        mainContent.classList.add('w-full');
        mainContent.style.width = '100%';
        mainContent.style.display = 'block';
    }

    if (desktopSchedule) {
        desktopSchedule.style.display = 'none'; 
    }
    
    if (aside) {
        aside.classList.add('hidden');
    }
    
    // Create mobile header
    createMobileHeader();
    
    // Create mobile bottom navigation
    createMobileBottomNav();
    
    // Create schedule toggle button
    createScheduleToggle();
    
    // Create schedule panel
    createSchedulePanel();
    
    // Adjust main content padding for mobile
    adjustContentForMobile();
    
    // Hide desktop elements
    hideDesktopElements();
}

function restoreDesktopView() {
    const navSidebar = document.getElementById('navSidebar');
    const mainContent = document.querySelector('main');
    const aside = document.querySelector('aside');
    
    if (navSidebar) {
        navSidebar.classList.remove('hidden');
    }
    
    if (mainContent) {
        mainContent.classList.add('shadow-2xl');
    }
    
    if (aside) {
        aside.classList.remove('hidden');
    }
    
    // Remove mobile elements
    const mobileHeader = document.getElementById('mobileHeader');
    const mobileBottomNav = document.getElementById('mobileBottomNav');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (mobileHeader) mobileHeader.remove();
    if (mobileBottomNav) mobileBottomNav.remove();
    if (mobileMenu) mobileMenu.remove();
}

function createMobileHeader() {
    // Check if already exists
    if (document.getElementById('mobileHeader')) return;
    
    const header = document.createElement('div');
    header.id = 'mobileHeader';
    header.className = 'fixed top-0 left-0 right-0 bg-white border-b border-gray-100 z-40 shadow-sm';
    header.innerHTML = `
        <div class="flex items-center justify-between p-4">
            <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded-lg bg-[#D32F2F] flex items-center justify-center text-white font-black text-sm">A</div>
                <h1 class="font-black text-lg text-gray-900">ATTENDANCE</h1>
            </div>
            <button onclick="toggleMobileMenu()" class="p-2 hover:bg-gray-100 rounded-lg transition" id="menuBtn">
                <i data-lucide="menu" class="w-6 h-6"></i>
            </button>
        </div>
    `;
    
    document.body.insertBefore(header, document.body.firstChild);
    lucide.createIcons();
}

function createMobileBottomNav() {
    // Check if already exists
    if (document.getElementById('mobileBottomNav')) return;
    
    const nav = document.createElement('div');
    nav.id = 'mobileBottomNav';
    nav.className = 'fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-30';
    nav.innerHTML = `
        <div class="flex items-center justify-between p-3">
            <div class="flex items-center gap-3 flex-1 min-w-0">
                <div class="w-10 h-10 rounded-full bg-[#D32F2F] flex-shrink-0 flex items-center justify-center text-white font-bold text-sm">
                    <span id="userInitial">I</span>
                </div>
                <div class="min-w-0 flex-1">
                    <p id="mobileUserName" class="font-bold text-sm text-gray-900 truncate">Instructor</p>
                    <p id="mobileUserEmail" class="text-xs text-gray-400 truncate">email@school.edu</p>
                </div>
            </div>
            <button onclick="confirmAction('logout')" class="p-2 text-gray-600 hover:text-[#D32F2F] transition">
                <i data-lucide="log-out" class="w-5 h-5"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(nav);
    
    // Update user info
    const session = JSON.parse(localStorage.getItem('active_session')) || {};
    document.getElementById('mobileUserName').textContent = session.name || 'Instructor';
    document.getElementById('mobileUserEmail').textContent = session.email || 'email@school.edu';
    document.getElementById('userInitial').textContent = (session.name || 'I').charAt(0).toUpperCase();
    
    lucide.createIcons();
}

function createMobileMenu() {
    // Check if already exists
    if (document.getElementById('mobileMenu')) return;
    
    const menu = document.createElement('div');
    menu.id = 'mobileMenu';
    menu.className = 'fixed top-16 left-0 right-0 bg-white border-b border-gray-200 z-30 shadow-md hidden';
    menu.innerHTML = `
        <div class="flex flex-col">
            <button onclick="showPage('home', this); toggleMobileMenu()" class="flex items-center gap-3 p-4 border-l-4 border-transparent text-gray-600 hover:bg-gray-50 hover:border-[#D32F2F] hover:text-[#D32F2F] transition nav-btn">
                <i data-lucide="layout-dashboard" class="w-5 h-5"></i>
                <span class="font-bold text-sm">Dashboard</span>
            </button>
            <button onclick="showPage('classes', this); toggleMobileMenu()" class="flex items-center gap-3 p-4 border-l-4 border-transparent text-gray-600 hover:bg-gray-50 hover:border-[#D32F2F] hover:text-[#D32F2F] transition nav-btn">
                <i data-lucide="layers" class="w-5 h-5"></i>
                <span class="font-bold text-sm">Classes</span>
            </button>
            <button onclick="showPage('history', this); toggleMobileMenu()" class="flex items-center gap-3 p-4 border-l-4 border-transparent text-gray-600 hover:bg-gray-50 hover:border-[#D32F2F] hover:text-[#D32F2F] transition nav-btn">
                <i data-lucide="archive" class="w-5 h-5"></i>
                <span class="font-bold text-sm">History</span>
            </button>
            <button onclick="showPage('profile'); toggleMobileMenu()" class="flex items-center gap-3 p-4 border-l-4 border-transparent text-gray-600 hover:bg-gray-50 hover:border-[#D32F2F] hover:text-[#D32F2F] transition nav-btn">
                <i data-lucide="user" class="w-5 h-5"></i>
                <span class="font-bold text-sm">Profile</span>
            </button>
        </div>
    `;
    
    document.body.insertBefore(menu, document.getElementById('mobileBottomNav'));
    lucide.createIcons();
}

function toggleMobileMenu() {
    if (!document.getElementById('mobileMenu')) {
        createMobileMenu();
    }
    const menu = document.getElementById('mobileMenu');
    menu.classList.toggle('hidden');
}

function adjustContentForMobile() {
    const contentArea = document.getElementById('content-area');
    const profilePage = document.getElementById('profilePage');
    
    if (contentArea) {
        contentArea.classList.remove('p-12');
        contentArea.classList.add('p-4', 'pt-20', 'pb-24');
    }
    
    if (profilePage) {
        profilePage.classList.remove('px-12', 'pt-20', 'pb-12');
        profilePage.classList.add('px-4', 'pt-20', 'pb-24');
    }
    
    // Adjust modals for mobile
    const modals = document.querySelectorAll('[id$="Modal"]');
    modals.forEach(modal => {
        if (modal.classList.contains('fixed')) {
            modal.classList.add('p-4');
        }
    });
}

function hideDesktopElements() {
    // Hide desktop-only buttons and elements
    const profileEditBtn = document.getElementById('profileEditBtn');
    if (profileEditBtn) {
        profileEditBtn.classList.add('hidden');
    }
    
    // Adjust sidebar toggle button
    const toggleBtn = document.querySelector('button[onclick="toggleMiniSidebar()"]');
    if (toggleBtn) {
        toggleBtn.classList.add('hidden');
    }
    
    // Hide schedule section on mobile
    const aside = document.querySelector('aside');
    if (aside) {
        aside.classList.add('hidden');
    }
}

function createScheduleToggle() {
    // Check if already exists
    if (document.getElementById('scheduleToggle')) return;
    
    const toggle = document.createElement('div');
    toggle.id = 'scheduleToggle';
    toggle.className = 'fixed top-16 right-4 z-40';
    toggle.innerHTML = `
        <button onclick="toggleSchedulePanel()" class="bg-[#D32F2F] text-white p-3 rounded-full shadow-lg hover:bg-[#B71C1C] transition flex items-center justify-center">
            <i data-lucide="calendar" class="w-5 h-5"></i>
        </button>
    `;
    
    document.body.appendChild(toggle);
    lucide.createIcons();
}

function toggleSchedulePanel() {
    let panel = document.getElementById('schedulePanel');
    
    if (!panel) {
        createSchedulePanel();
        panel = document.getElementById('schedulePanel');
    }
    
    panel.classList.toggle('hidden');
}

function createSchedulePanel() {
    if (document.getElementById('schedulePanel')) return;
    
    const panel = document.createElement('div');
    panel.id = 'schedulePanel';
    panel.className = 'fixed top-32 right-4 bg-white rounded-2xl shadow-2xl border border-gray-100 z-40 max-w-sm max-h-96 overflow-y-auto hidden';
    panel.innerHTML = `
        <div class="p-6">
            <div class="flex items-center justify-between mb-4">
                <h3 class="font-black text-sm text-gray-900 uppercase tracking-widest">Daily Schedule</h3>
                <button onclick="document.getElementById('schedulePanel').classList.add('hidden')" class="p-1 hover:bg-gray-100 rounded transition">
                    <i data-lucide="x" class="w-4 h-4 text-gray-400"></i>
                </button>
            </div>
            
            <div id="mobileClockDisplay" class="mb-6 text-center">
                <h1 id="mobileClock" class="text-2xl font-black text-[#D32F2F] tracking-tighter">00:00:00</h1>
                <p id="mobileDate" class="text-gray-400 text-[10px] uppercase font-bold tracking-widest mt-1">Loading...</p>
            </div>
            
            <div id="mobileDayFilters" class="flex flex-wrap gap-2 mb-4"></div>
            
            <div id="mobileScheduleList" class="space-y-3">
                <p class="text-xs text-gray-400 text-center py-4">No schedule</p>
            </div>
            
            <button onclick="openTaskModal()" class="mt-4 w-full bg-[#D32F2F] text-white font-bold py-3 rounded-lg shadow-lg hover:bg-[#B71C1C] transition flex items-center justify-center space-x-2 text-sm">
                <i data-lucide="plus-circle" class="w-4 h-4"></i> <span>Add Schedule</span>
            </button>
        </div>
    `;
    
    document.body.appendChild(panel);
    
    // Update schedule display
    updateMobileScheduleDisplay();
    
    // Update time every second
    setInterval(updateMobileTime, 1000);
    
    lucide.createIcons();
}

function updateMobileTime() {
    const clockEl = document.getElementById('mobileClock');
    const dateEl = document.getElementById('mobileDate');
    const now = new Date();
    if(clockEl) clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    if(dateEl) dateEl.textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}

function updateMobileScheduleDisplay() {
    const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const today = new Date();
    const selectedDay = days[today.getDay()];
    
    const filterContainer = document.getElementById('mobileDayFilters');
    if (filterContainer) {
        filterContainer.innerHTML = days.map(d => `
            <button onclick="updateMobileScheduleForDay('${d}')" class="flex-1 py-2 text-[9px] font-black border rounded-lg transition ${d === selectedDay ? 'bg-[#D32F2F] text-white border-[#D32F2F]' : 'bg-white text-gray-400 border-gray-200'}">${d}</button>
        `).join('');
    }
    
    updateMobileScheduleForDay(selectedDay);
}

function updateMobileScheduleForDay(day) {
    // Get schedules from localStorage
    const schedules = JSON.parse(localStorage.getItem('attendace_sched_v3')) || [];
    const filtered = schedules.filter(s => s.day === day);
    
    const listContainer = document.getElementById('mobileScheduleList');
    if (!listContainer) return;
    
    if (filtered.length === 0) {
        listContainer.innerHTML = '<p class="text-xs text-gray-400 text-center py-4">Free Schedule</p>';
    } else {
        listContainer.innerHTML = filtered.map(s => `
            <div class="bg-gray-50 p-3 rounded-lg border border-gray-200">
                <div class="flex justify-between items-start mb-1">
                    <h4 class="font-bold text-gray-900 text-sm">${s.name}</h4>
                    <div class="flex space-x-1">
                        <button onclick="editSchedule(${s.id})" class="text-gray-300 hover:text-blue-500 transition">
                            <i data-lucide="edit-3" class="w-3 h-3"></i>
                        </button>
                        <button onclick="confirmAction('deleteSubject', ${s.id})" class="text-gray-300 hover:text-red-500 transition">
                            <i data-lucide="trash-2" class="w-3 h-3"></i>
                        </button>
                    </div>
                </div>
                <p class="text-[9px] text-gray-400 font-bold uppercase tracking-widest">RM ${s.room} • <span class="text-[#D32F2F]">${s.timeFrom} - ${s.timeTo}</span></p>
            </div>
        `).join('');
    }
    
    lucide.createIcons();
}

function toggleMobileMenu() {
    if (!document.getElementById('mobileMenu')) {
        createMobileMenu();
    }
    const menu = document.getElementById('mobileMenu');
    menu.classList.toggle('hidden');
}

// Override original showPage to handle mobile
const originalShowPage = window.showPage;
window.showPage = function(pageId, btn) {
    // Close mobile menu when navigating
    const mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
        mobileMenu.classList.add('hidden');
    }
    
    // Call original function
    if (originalShowPage) {
        originalShowPage.call(this, pageId, btn);
    }
    
    // Adjust mobile view after page change
    if (isMobile()) {
        adjustContentForMobile();
    }
};

// Adjust modal sizes for mobile
const style = document.createElement('style');
style.textContent = `
    @media (max-width: 768px) {
        body {
            font-size: 16px;
        }
        
        input, select, textarea {
            font-size: 16px;
        }
        
        button {
            -webkit-appearance: none;
            appearance: none;
        }
        
        button, a, input[type="checkbox"], input[type="radio"] {
            min-height: 44px;
            min-width: 44px;
        }
        
        #cameraModal {
            max-width: 100% !important;
        }
        
        #cameraModal .bg-white {
            border-radius: 1.5rem !important;
            max-height: 90vh !important;
        }
        
        #regModal, #classModal, #taskModal {
            max-width: 100% !important;
        }
        
        #regModal .bg-white, 
        #classModal .bg-white, 
        #taskModal .bg-white {
            border-radius: 1.5rem !important;
            max-height: 90vh !important;
            margin: 1rem !important;
        }
        
        .folder-grid {
            grid-template-columns: 1fr !important;
        }
        
        .grid.grid-cols-2 {
            grid-template-columns: 1fr !important;
        }
        
        .grid.grid-cols-3 {
            grid-template-columns: 1fr !important;
        }
        
        main {
            padding-top: 0 !important;
        }
        
        #profilePage {
            padding-top: 5rem !important;
            padding-bottom: 6rem !important;
        }
    }
`;
document.head.appendChild(style);

console.log('Mobile view initialized. Screen width:', window.innerWidth);