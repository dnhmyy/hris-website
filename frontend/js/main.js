// js/main.js - RotiKebanggaan

// Toast notification - di tengah layar, ukuran besar
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const iconEl = document.getElementById('toastIcon');
    const msgEl = document.getElementById('toastMessage');
    if (!toast || !msgEl) return;

    toast.className = 'toast ' + type;
    const icons = { success: '✓', error: '!', info: '' };
    iconEl.textContent = icons[type] || icons.success;
    msgEl.textContent = message;
    toast.classList.remove('hidden');

    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => {
        toast.classList.add('hidden');
    }, 3500);
}

// Confirm modal - ganti native confirm(), tampil di tengah layar
function showConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const msgEl = document.getElementById('confirmMessage');
        const btnOk = document.getElementById('confirmOk');
        const btnCancel = document.getElementById('confirmCancel');
        if (!modal || !msgEl) {
            resolve(false);
            return;
        }

        msgEl.textContent = message;
        modal.classList.remove('hidden');

        const close = (result) => {
            modal.classList.add('hidden');
            btnOk.onclick = null;
            btnCancel.onclick = null;
            modal.onclick = null;
            resolve(result);
        };

        btnOk.onclick = () => close(true);
        btnCancel.onclick = () => close(false);
        modal.onclick = (e) => { if (e.target === modal) close(false); };
    });
}

// Simpan data karyawan global untuk filtering
let employeesData = [];
let activeAttendanceData = [];
let activeReportData = [];
let employeesCurrentPage = 1;
let attendanceCurrentPage = 1;
let reportCurrentPage = 1;
const itemsPerPage = 35;
let filteredEmployees = [];
let sortColumn = 'id';
let sortDirection = 'asc'; // 'asc' or 'desc'
let currentUser = null;

// ============================================
// AUTHENTICATION LOGIC
// ============================================

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/check-auth`);
        const data = await response.json();

        if (data.authenticated) {
            currentUser = data.user;
            showMainApp(true);
            document.getElementById('displayUsername').textContent = currentUser.username;
            refreshAllData();
        } else {
            showMainApp(false);
        }
    } catch (error) {
        console.error('Error checking auth:', error);
        showMainApp(false);
    }
}

function showMainApp(isLoggedIn) {
    const loginSection = document.getElementById('loginSection');
    const mainApp = document.getElementById('mainApp');

    if (isLoggedIn) {
        loginSection.classList.add('hidden');
        mainApp.classList.remove('hidden');
    } else {
        loginSection.classList.remove('hidden');
        mainApp.classList.add('hidden');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Login Berhasil! Selamat datang.', 'success');
            checkAuth();
        } else {
            showToast(data.error || 'Login gagal', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Terjadi kesalahan koneksi', 'error');
    }
}

async function handleLogout() {
    const confirm = await showConfirm('Apakah Anda yakin ingin keluar?');
    if (!confirm) return;

    try {
        await fetch(`${API_BASE}/logout`, { method: 'POST' });

        // Reset form login agar kosong saat logout
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.reset();
        }

        showToast('Anda telah logout', 'info');
        checkAuth();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function refreshAllData() {
    fetchEmployees();
    fetchDashboardStats();
    loadAttendance(); // Optional: load if active
}

// Fungsi untuk mengambil data karyawan dari backend
async function fetchEmployees() {
    try {
        const response = await fetch(`${API_BASE}/employees`);
        employeesData = await response.json();
        filteredEmployees = [...employeesData]; // Init filtered data
        renderEmployeesTable(); // Render page 1
        populateEmployeeBranchFilter(); // Isi filter cabang
    } catch (error) {
        console.error('Gagal mengambil data karyawan:', error);
        showToast('Tidak bisa memuat data. Silakan coba lagi.', 'error');
    }
}

// Fungsi Filter Karyawan
function handleEmployeeFilter() {
    const searchTerm = document.getElementById('searchEmployeeName').value.toLowerCase();
    const branchFilter = document.getElementById('filterEmployeeBranch').value;

    filteredEmployees = employeesData.filter(emp => {
        const matchName = emp.name.toLowerCase().includes(searchTerm) || String(emp.id).toLowerCase().includes(searchTerm);
        const matchBranch = branchFilter ? emp.branch_id === branchFilter : true;
        return matchName && matchBranch;
    });

    employeesCurrentPage = 1; // Reset ke halaman 1 saat filter
    renderEmployeesTable();
}

// Populate filter cabang khusus page karyawan
function populateEmployeeBranchFilter() {
    const select = document.getElementById('filterEmployeeBranch');
    if (!select || typeof HRIS_CONFIG === 'undefined') return;

    // Jangan overwrite jika sudah ada selection (kecuali kosong)
    if (select.options.length > 2) return;

    const options = HRIS_CONFIG.branches.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    select.innerHTML = '<option value="">Semua Cabang</option>' + options;
}

// Event Listeners untuk Filter
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchEmployeeName');
    const branchSelect = document.getElementById('filterEmployeeBranch');

    if (searchInput) searchInput.addEventListener('input', handleEmployeeFilter);
    if (branchSelect) branchSelect.addEventListener('change', handleEmployeeFilter);
});

// Fungsi render tabel karyawan dengan Pagination
function renderEmployeesTable() {
    const tbody = document.getElementById('employeesTableBody');
    const paginationContainer = document.getElementById('employeePagination');
    if (!tbody) return;

    if (filteredEmployees.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 2rem;">Tidak ada data karyawan</td></tr>';
        if (paginationContainer) paginationContainer.innerHTML = '';
        return;
    }

    // Logic Sorting
    const sortedData = [...filteredEmployees].sort((a, b) => {
        let valA, valB;

        switch (sortColumn) {
            case 'id':
                valA = parseInt(a.id);
                valB = parseInt(b.id);
                break;
            case 'name':
                valA = a.name.toLowerCase();
                valB = b.name.toLowerCase();
                break;
            case 'position':
                valA = (a.position || '').toLowerCase();
                valB = (b.position || '').toLowerCase();
                break;
            case 'department':
                valA = (a.department || '').toLowerCase();
                valB = (b.department || '').toLowerCase();
                break;
            case 'branch':
                valA = getBranchName(a.branch_id).toLowerCase();
                valB = getBranchName(b.branch_id).toLowerCase();
                break;
            case 'status':
                valA = a.is_active ? 1 : 0;
                valB = b.is_active ? 1 : 0;
                break;
            default:
                valA = a[sortColumn];
                valB = b[sortColumn];
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    // Logic Pagination menggunakan data yang sudah disortir
    const totalPages = Math.ceil(sortedData.length / itemsPerPage);
    const startIndex = (employeesCurrentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = sortedData.slice(startIndex, endIndex);

    tbody.innerHTML = pageData.map((emp, index) => `
      <tr>
          <td>${startIndex + index + 1}</td>
          <td>${emp.id}</td>
          <td>${emp.name}</td>
          <td>${emp.position || '-'}</td>
          <td>${emp.department || '-'}</td>
          <td><span class="shift-badge">${emp.shift_start}–${emp.shift_end}</span></td>
          <td><span class="branch-badge ${emp.branch_id}">${getBranchName(emp.branch_id)}</span></td>
          <td><span class="status-badge ${emp.is_active ? 'status-active' : 'status-inactive'}">
              ${emp.is_active ? 'Aktif' : 'Resign'}
          </span></td>
          <td class="actions-cell">
              <button class="btn-edit" onclick="editEmployee('${emp.id}')">Edit</button>
              ${emp.is_active ?
            `<button class="btn-deactivate" onclick="toggleEmployeeStatus('${emp.id}', false)">Nonaktif</button>` :
            `<button class="btn-activate" onclick="toggleEmployeeStatus('${emp.id}', true)">Aktif</button>`
        }
          </td>
      </tr>
  `).join('');

    renderPaginationControls(totalPages, employeesCurrentPage, 'employeePagination', 'changeEmployeesPage');
    updateSortIcons();
}

// Fungsi untuk menangani klik header tabel (Sorting)
function handleSort(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    employeesCurrentPage = 1; // Reset ke halaman 1 setiap kali sort berubah
    renderEmployeesTable();
}

// Update icon panah di header tabel
function updateSortIcons() {
    const headers = {
        'id': 'sortId',
        'name': 'sortName',
        'position': 'sortPosition',
        'department': 'sortDept',
        'branch': 'sortBranch',
        'status': 'sortStatus'
    };

    // Reset semua icon
    Object.values(headers).forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '↕';
    });

    // Set icon untuk kolom yang aktif
    const activeIcon = document.getElementById(headers[sortColumn]);
    if (activeIcon) {
        activeIcon.textContent = sortDirection === 'asc' ? '↑' : '↓';
    }
}

// Helper untuk tombol aksi (karena pakai onclick di render)
function editEmployee(id) {
    const emp = employeesData.find(e => e.id == id);
    if (emp) openEditEmployeeModal(emp);
}

function toggleEmployeeStatus(id, isActive) {
    if (isActive) {
        // Mau mengaktifkan
        activateEmployee(id);
    } else {
        // Mau menonaktifkan
        deactivateEmployee(id);
    }
}

// Render Tombol Pagination (Generic)
function renderPaginationControls(totalPages, currentPage, containerId, changePageFuncName) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let buttons = '';

    // Prev Button
    buttons += `<button class="btn-secondary" ${currentPage === 1 ? 'disabled' : ''} onclick="${changePageFuncName}(${currentPage - 1})">Prev</button>`;

    // Page Numbers (Max 5 visible)
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            buttons += `<button class="btn-secondary ${i === currentPage ? 'active-page' : ''}" onclick="${changePageFuncName}(${i})" style="${i === currentPage ? 'background: var(--primary); color: white;' : ''}">${i}</button>`;
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            buttons += `<span style="padding: 0.5rem;">...</span>`;
        }
    }

    // Next Button
    buttons += `<button class="btn-secondary" ${currentPage === totalPages ? 'disabled' : ''} onclick="${changePageFuncName}(${currentPage + 1})">Next</button>`;

    container.innerHTML = buttons;
}

function changeEmployeesPage(page) {
    const totalPages = Math.ceil(filteredEmployees.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    employeesCurrentPage = page;
    renderEmployeesTable();
}

// Fungsi untuk mengambil statistik dashboard
async function fetchDashboardStats() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/stats`);
        const stats = await response.json();

        document.getElementById('totalEmployees').textContent = stats.total_employees;
        document.getElementById('presentToday').textContent = stats.present_today;
        document.getElementById('totalForToday').textContent = stats.total_employees;

        // Update branch cards
        if (stats.branch_counts) {
            HRIS_CONFIG.branches.forEach(branch => {
                const count = stats.branch_counts[branch.id] || 0;
                // Find card by branch id. Since we use card-${branch.colorClass} in render,
                // and colorClass matches id in config.js
                const cardValue = document.querySelector(`.card-${branch.colorClass} .card-value`);
                if (cardValue) {
                    cardValue.textContent = count;
                }
            });
        }
    } catch (error) {
        console.error('Gagal mengambil statistik:', error);
    }
}

// Helper: Ambil nama cabang dari ID
function getBranchName(branchId) {
    const branch = HRIS_CONFIG.branches.find(b => b.id === branchId);
    return branch ? branch.name : branchId;
}

// Helper: Hitung lama kerja dari start_date
function calculateWorkDuration(startDate) {
    if (!startDate) return '-';

    const start = new Date(startDate);
    const now = new Date();

    let years = now.getFullYear() - start.getFullYear();
    let months = now.getMonth() - start.getMonth();

    if (months < 0) {
        years--;
        months += 12;
    }

    if (years === 0 && months === 0) {
        const days = Math.floor((now - start) / (1000 * 60 * 60 * 24));
        return `${days} hari`;
    } else if (years === 0) {
        return `${months} bulan`;
    } else if (months === 0) {
        return `${years} tahun`;
    } else {
        return `${years} tahun ${months} bulan`;
    }
}

// Helper: Format tanggal yyyy-mm-dd
function formatDate(dateString, includeWeekday = false) {
    if (!dateString) return 'dd/mm/yyyy';

    // Handle format dari DB: "2024-02-13 00:00:00" -> ambil bagian tanggal saja
    // Cek apakah formatnya YYYY-MM-DD dengan spasi (MySQL standard)
    if (typeof dateString === 'string' && /^\d{4}-\d{2}-\d{2}/.test(dateString) && dateString.includes(' ')) {
        dateString = dateString.split(' ')[0];
    }

    // Jika formatnya ISO/GMT
    if (typeof dateString === 'string' && (dateString.includes('T') || dateString.includes('GMT'))) {
        const d = new Date(dateString);
        if (!isNaN(d.getTime())) {
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            dateString = `${year}-${month}-${day}`;
        }
    }

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    const days = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];

    const parts = dateString.split('-');
    if (parts.length !== 3) return dateString;

    const day = parts[2];
    const month = months[parseInt(parts[1]) - 1];
    const year = parts[0];

    let formatted = `${day} ${month} ${year}`;

    if (includeWeekday) {
        const d = new Date(dateString);
        if (!isNaN(d.getTime())) {
            const dayName = days[d.getDay()];
            formatted = `${dayName}, ${formatted}`;
        }
    }

    return formatted;
}

// Helper: Format tanggal ke yyyy-mm-dd untuk input type="date"
function formatDateToYYYYMMDD(dateString) {
    if (!dateString) return '';

    // Jika formatnya "2024-02-13 00:00:00", ambil bagian depannya saja
    if (typeof dateString === 'string' && dateString.includes(' ')) {
        const part = dateString.split(' ')[0];
        if (part.split('-').length === 3) return part;
    }

    try {
        const d = new Date(dateString);
        if (isNaN(d.getTime())) {
            // Fallback manual jika gagal parse
            if (typeof dateString === 'string') {
                const match = dateString.match(/\d{4}-\d{2}-\d{2}/);
                return match ? match[0] : '';
            }
            return '';
        }
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    } catch (e) {
        return '';
    }
}

// Fungsi untuk update tampilan overlay pada input type="date"
function handleDateInputDisplay(el) {
    if (!el) return;
    el.setAttribute('data-date', formatDate(el.value));
}

// ========== ABSENSI ==========
// Helper: Format durasi menit ke "Xj Ym" (e.g. 65 -> 1j 5m)
function formatDuration(minutes) {
    if (!minutes || minutes <= 0) return '-';

    // Pastikan integer
    const totalMinutes = Math.round(parseFloat(minutes));
    if (totalMinutes === 0) return '-';

    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;

    if (hours > 0) {
        return `${hours}j ${mins}m`;
    }
    return `${mins}m`;
}

// ========== ABSENSI ==========
async function loadAttendance() {
    const branch = document.getElementById('branchFilter').value;
    const date = document.getElementById('dateFilter').value;

    let url = `${API_BASE}/attendance`;
    const params = new URLSearchParams();
    if (branch) params.append('branch', branch);
    if (date) params.append('date', date);

    if (params.toString()) {
        url += '?' + params.toString();
    }

    try {
        const response = await fetch(url);
        const attendance = await response.json();
        activeAttendanceData = attendance; // Simpan untuk filtering
        attendanceCurrentPage = 1; // Reset to page 1
        renderAttendanceTable();
    } catch (error) {
        console.error('Gagal memuat data absensi:', error);
    }
}

function handleAttendanceFilter() {
    attendanceCurrentPage = 1; // Reset case for search
    renderAttendanceTable();
}

function renderAttendanceTable(data = null) {
    const tbody = document.querySelector('#attendance tbody');
    const paginationContainer = document.getElementById('attendancePagination');
    if (!tbody) return;

    let displayData = data || activeAttendanceData;
    const searchTerm = document.getElementById('searchAttendance') ? document.getElementById('searchAttendance').value.toLowerCase() : '';

    if (searchTerm) {
        displayData = displayData.filter(record =>
            record.name.toLowerCase().includes(searchTerm) ||
            String(record.employee_id).toLowerCase().includes(searchTerm)
        );
    }

    if (!displayData || displayData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align: center;">Tidak ada data absensi</td></tr>';
        if (paginationContainer) paginationContainer.innerHTML = '';
        return;
    }

    // Pagination Logic
    const totalPages = Math.ceil(displayData.length / itemsPerPage);
    const startIndex = (attendanceCurrentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = displayData.slice(startIndex, endIndex);

    tbody.innerHTML = pageData.map((record, index) => `
        <tr>
            <td>${startIndex + index + 1}</td>
            <td>${formatDate(record.date)}</td>
            <td>${record.employee_id}</td>
            <td>${record.name}</td>
            <td><span class="branch-badge ${record.branch_id}">${getBranchName(record.branch_id)}</span></td>
            <td>${record.shift_start || '-'}</td>
            <td>${record.shift_end || '-'}</td>
            <td>${record.check_in || '-'}</td>
            <td>${record.check_out || '-'}</td>
            <td>${formatDuration(record.late_minutes)}</td>
            <td>${formatDuration(record.overtime_minutes)}</td>
        </tr>
    `).join('');

    renderPaginationControls(totalPages, attendanceCurrentPage, 'attendancePagination', 'changeAttendancePage');
}

function changeAttendancePage(page) {
    const totalPages = Math.ceil(activeAttendanceData.length / itemsPerPage);
    attendanceCurrentPage = page;
    renderAttendanceTable();
}

// ========== LAPORAN BULANAN ==========
async function loadMonthlyReport() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    const branch = document.getElementById('reportBranch').value;

    if (!startDate || !endDate) {
        showToast('Pilih tanggal mulai dan tanggal akhir', 'error');
        return;
    }

    let url = `${API_BASE}/reports/monthly?start_date=${startDate}&end_date=${endDate}`;
    if (branch) url += `&branch=${branch}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        // Update summary stats
        document.getElementById('reportTotalEmployees').textContent = data.summary.total_employees;
        document.getElementById('reportTotalPresent').textContent = data.summary.total_present;
        document.getElementById('reportTotalOvertime').textContent = formatDuration(data.summary.total_overtime_hours * 60);
        document.getElementById('reportTotalOvertime').textContent = data.summary.total_overtime_hours + ' jam'; // Keep summary simple/existing for now unless requested.

        document.getElementById('reportTotalLate').textContent = data.summary.total_late_minutes;

        // Render table
        activeReportData = data.employees;
        reportCurrentPage = 1; // Reset to page 1
        renderMonthlyReportTable();

        // Render branch summary cards
        renderBranchSummaryCards(data.branch_summary);

        showToast('Laporan berhasil dimuat', 'success');
    } catch (error) {
        console.error('Gagal memuat laporan:', error);
        showToast('Gagal memuat laporan', 'error');
    }
}

function handleReportFilter() {
    reportCurrentPage = 1; // Reset case for search
    renderMonthlyReportTable();
}

function renderMonthlyReportTable(data = null) {
    const tbody = document.getElementById('reportTableBody');
    const paginationContainer = document.getElementById('reportPagination');
    if (!tbody) return;

    let displayData = data || activeReportData;
    const searchTerm = document.getElementById('searchReport') ? document.getElementById('searchReport').value.toLowerCase() : '';

    if (searchTerm) {
        displayData = displayData.filter(emp =>
            emp.name.toLowerCase().includes(searchTerm) ||
            String(emp.id).toLowerCase().includes(searchTerm)
        );
    }

    if (!displayData || displayData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" style="text-align: center;">Tidak ada data</td></tr>';
        if (paginationContainer) paginationContainer.innerHTML = '';
        return;
    }

    // Pagination Logic
    const totalPages = Math.ceil(displayData.length / itemsPerPage);
    const startIndex = (reportCurrentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = displayData.slice(startIndex, endIndex);

    tbody.innerHTML = pageData.map((record, index) => `
        <tr>
            <td>${startIndex + index + 1}</td>
            <td>${formatDate(record.date)}</td>
            <td>${record.employee_id}</td>
            <td>${record.name}</td>
            <td><span class="branch-badge ${record.branch_id}">${getBranchName(record.branch_id)}</span></td>
            <td>${record.shift_start}</td>
            <td>${record.shift_end}</td>
            <td>${record.check_in}</td>
            <td>${record.check_out}</td>
            <td><span class="late-badge">${formatDuration(record.late_minutes)}</span></td>
            <td><span class="overtime-badge">${formatDuration(record.overtime_minutes)}</span></td>
        </tr>
    `).join('');

    renderPaginationControls(totalPages, reportCurrentPage, 'reportPagination', 'changeReportPage');
}

function changeReportPage(page) {
    reportCurrentPage = page;
    renderMonthlyReportTable();
}

function renderBranchSummaryCards(branchSummary) {
    const container = document.getElementById('branchSummaryCards');
    if (!container) return;

    if (!branchSummary || branchSummary.length === 0) {
        container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-muted);">Tidak ada data</p>';
        return;
    }

    // Urutkan berdasarkan urutan di HRIS_CONFIG.branches
    const sortedSummary = [...branchSummary].sort((a, b) => {
        const indexA = HRIS_CONFIG.branches.findIndex(br => br.id === a.branch_id);
        const indexB = HRIS_CONFIG.branches.findIndex(br => br.id === b.branch_id);
        return indexA - indexB;
    });

    container.innerHTML = sortedSummary.map(branch => `
        <div class="card card-${branch.branch_id}">
            <div class="card-content" style="width: 100%">
                <h3>${getBranchName(branch.branch_id)}</h3>
                <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.9rem; color: var(--text-muted);">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Total Karyawan:</span> <strong style="color: var(--text)">${branch.total_employees}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Kehadiran:</span> <strong style="color: var(--text)">${branch.attendance_rate}%</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Lembur:</span> <strong class="overtime-badge">${branch.total_overtime_hours} jam</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Telat:</span> <strong class="late-badge">${branch.total_late_count} kali</strong>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function viewEmployeeDetail(employeeId) {
    showToast(`Detail karyawan ${employeeId} akan segera hadir!`, 'info');
}


function exportReport() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    const branch = document.getElementById('reportBranch').value;

    if (!startDate || !endDate) {
        showToast('Pilih tanggal mulai dan tanggal akhir', 'error');
        return;
    }

    let url = `${API_BASE}/reports/export?start_date=${startDate}&end_date=${endDate}`;
    if (branch) url += `&branch=${branch}`;

    showToast('Sedang mendownload laporan...', 'info');
    window.location.href = url;
}



// Populate branch filter untuk laporan
function populateReportBranchFilter() {
    const select = document.getElementById('reportBranch');
    if (!select) return;

    const options = HRIS_CONFIG.branches.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    select.innerHTML = '<option value="">Semua Cabang</option>' + options;
}

// ========== MODAL TAMBAH/EDIT KARYAWAN ==========
let currentModalMode = 'add'; // 'add' atau 'edit'

function populateBranchSelect() {
    const select = document.querySelector('#employeeForm [name="branch_id"]');
    if (!select || typeof HRIS_CONFIG === 'undefined') return;

    select.innerHTML = '<option value="">Pilih Cabang</option>' +
        HRIS_CONFIG.branches.map(branch =>
            `<option value="${branch.id}">${branch.name}</option>`
        ).join('');
}

function openAddEmployeeModal() {
    currentModalMode = 'add';
    document.getElementById('modalTitle').textContent = 'Tambah Karyawan Baru';
    document.getElementById('employeeForm').reset();
    document.getElementById('inputId').disabled = false;
    document.getElementById('employeeId').value = '';

    // Sembunyikan field lama bekerja saat tambah baru
    const durationGroup = document.getElementById('workDurationGroup');
    if (durationGroup) durationGroup.style.display = 'none';

    populateBranchSelect();
    document.getElementById('employeeModal').classList.remove('hidden');
}

function openEditEmployeeModal(employee) {
    currentModalMode = 'edit';
    document.getElementById('modalTitle').textContent = 'Edit Karyawan';

    // Isi form dengan data karyawan
    document.getElementById('employeeId').value = employee.id;
    document.getElementById('inputId').value = employee.id;
    document.getElementById('inputId').disabled = true; // ID tidak bisa diubah
    document.querySelector('input[name="name"]').value = employee.name || '';
    document.querySelector('input[name="position"]').value = employee.position || '';
    document.querySelector('select[name="department"]').value = employee.department || '';

    // Select branch
    populateBranchSelect();
    document.querySelector('select[name="branch_id"]').value = employee.branch_id || '';

    document.querySelector('input[name="shift_start"]').value = employee.shift_start || '09:00';
    document.querySelector('input[name="shift_end"]').value = employee.shift_end || '17:00';
    document.querySelector('select[name="is_active"]').value = employee.is_active ? '1' : '0';

    // Contract fields
    const formattedStartDate = formatDateToYYYYMMDD(employee.start_date);
    const startDateInput = document.querySelector('input[name="start_date"]');
    if (startDateInput) startDateInput.value = formattedStartDate;
    document.querySelector('select[name="contract_duration_months"]').value = employee.contract_duration_months || '';

    // Hitung dan tampilkan lama bekerja
    const durationGroup = document.getElementById('workDurationGroup');
    const durationDisplay = document.getElementById('workDurationDisplay');

    if (durationGroup && durationDisplay) {
        durationGroup.style.display = 'block';
        durationDisplay.value = calculateWorkDuration(employee.start_date);
    }

    if (startDateInput) {
        handleDateInputDisplay(startDateInput);

        const syncUpdate = (e) => {
            handleDateInputDisplay(e.target);
            if (durationDisplay) {
                durationDisplay.value = calculateWorkDuration(e.target.value);
            }
        };

        // Gunakan oninput dan onchange agar benar-benar terupdate di semua browser
        startDateInput.oninput = syncUpdate;
        startDateInput.onchange = syncUpdate;
    }

    document.getElementById('employeeModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('employeeModal').classList.add('hidden');
}

async function deactivateEmployee(id) {
    const ok = await showConfirm('Apakah Anda yakin ingin menandai karyawan ini sebagai resign?');
    if (!ok) return;

    try {
        const res = await fetch(`${API_BASE}/employees/${id}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            showToast('Karyawan berhasil ditandai resign');
            fetchEmployees();
        } else {
            const err = await res.json();
            showToast(err.error || 'Gagal memproses', 'error');
        }
    } catch (error) {
        console.error(error);
        showToast('Koneksi gagal. Silakan coba lagi.', 'error');
    }
}

async function activateEmployee(id) {
    const ok = await showConfirm('Apakah Anda yakin ingin mengaktifkan kembali karyawan ini?');
    if (!ok) return;

    try {
        const res = await fetch(`${API_BASE}/employees/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: 1 })
        });

        if (res.ok) {
            showToast('Karyawan berhasil diaktifkan');
            fetchEmployees();
        } else {
            const err = await res.json();
            showToast(err.error || 'Gagal memproses', 'error');
        }
    } catch (error) {
        console.error(error);
        showToast('Koneksi gagal. Silakan coba lagi.', 'error');
    }
}

// Update event listener untuk tombol Tambah Karyawan & setup modal
document.addEventListener('DOMContentLoaded', function () {
    populateBranchSelect();

    // Handle form submit
    const employeeForm = document.getElementById('employeeForm');
    if (employeeForm) {
        employeeForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const formData = new FormData(this);
            const employeeData = Object.fromEntries(formData);

            // Konversi is_active ke integer
            employeeData.is_active = parseInt(employeeData.is_active, 10);

            if (currentModalMode === 'add') {
                // POST tambah karyawan
                try {
                    const res = await fetch(`${API_BASE}/employees`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(employeeData)
                    });

                    if (res.ok) {
                        showToast('Karyawan berhasil ditambahkan');
                        closeModal();
                        fetchEmployees();
                    } else {
                        const err = await res.json();
                        showToast(err.error || 'Gagal menambahkan', 'error');
                    }
                } catch (error) {
                    console.error(error);
                    showToast('Koneksi gagal. Silakan coba lagi.', 'error');
                }
            } else {
                // PUT edit karyawan
                const id = document.getElementById('employeeId').value;
                try {
                    const res = await fetch(`${API_BASE}/employees/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(employeeData)
                    });

                    if (res.ok) {
                        showToast('Karyawan berhasil diperbarui');
                        closeModal();
                        fetchEmployees();
                    } else {
                        const err = await res.json();
                        showToast(err.error || 'Gagal memperbarui', 'error');
                    }
                } catch (error) {
                    console.error(error);
                    showToast('Koneksi gagal. Silakan coba lagi.', 'error');
                }
            }
        });
    }

    // Modal close handlers
    const modal = document.getElementById('employeeModal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeModal();
        });
    }

    // Event listener untuk tab Karyawan
    const employeesLink = document.querySelector('a[href="#employees"]');
    if (employeesLink) {
        employeesLink.addEventListener('click', function () {
            setTimeout(fetchEmployees, 100);
        });
    }

    // Event listener untuk tab Absensi
    const attendanceLink = document.querySelector('a[href="#attendance"]');
    if (attendanceLink) {
        attendanceLink.addEventListener('click', function () {
            const dateEl = document.getElementById('dateFilter');
            if (dateEl && !dateEl.value) {
                const today = new Date().toISOString().slice(0, 10);
                dateEl.value = today;
            }
            setTimeout(loadAttendance, 100);
        });
    }

    // Event listener untuk tab Dashboard
    const dashboardLink = document.querySelector('a[href="#dashboard"]');
    if (dashboardLink) {
        dashboardLink.addEventListener('click', function () {
            setTimeout(fetchDashboardStats, 100);
        });
    }

    // Event listener untuk tab Mesin Absensi
    const devicesLink = document.querySelector('a[href="#devices"]');
    if (devicesLink) {
        devicesLink.addEventListener('click', function () {
            setTimeout(fetchDevices, 100);
        });
    }

    // Load data awal jika di dashboard
    if (!window.location.hash || window.location.hash === '#dashboard') {
        setTimeout(fetchDashboardStats, 500);
    }
});

// --- Dashboard & UI ---
function renderBranchTags() {
    const container = document.getElementById('branchTags');
    if (!container) return;
    container.innerHTML = HRIS_CONFIG.branches.map(b =>
        `<span class="branch-tag ${b.colorClass}">${b.name}</span>`
    ).join('');
}

function renderDashboardCards() {
    const container = document.getElementById('dashboardCards');
    if (!container) return;
    container.innerHTML = HRIS_CONFIG.branches.map(branch => `
        <div class="card card-${branch.colorClass} clickable-card" onclick="viewBranchDetail('${branch.id}')">
            <div class="card-content">
                <p class="card-label">Cabang ${branch.name}</p>
                <h3 class="card-value">0</h3>
                <p class="card-desc">Karyawan Hadir</p>
            </div>
            <div class="card-icon"><i class="fas fa-building"></i></div>
        </div>
    `).join('');
}

function renderReportCards() {
    const container = document.getElementById('reportCards');
    if (!container) return;
    container.innerHTML = HRIS_CONFIG.branches.map(branch => `
        <div class="report-card card-${branch.colorClass}">
            <h3 class="report-title">Cabang ${branch.name}</h3>
            <ul class="report-list">
                <li><span>Total Karyawan:</span> <strong>0</strong></li>
                <li><span>Rata-rata Kehadiran:</span> <strong>0%</strong></li>
                <li><span>Total Lembur (jam):</span> <strong class="overtime-positive">0 jam</strong></li>
                <li><span>Karyawan Telat:</span> <strong class="late-negative">0 orang</strong></li>
            </ul>
            <button class="btn-export">📥 Export CSV</button>
        </div>
    `).join('');
}

function renderBranchFilter() {
    const select = document.getElementById('branchFilter');
    if (!select || typeof HRIS_CONFIG === 'undefined') return;
    const options = HRIS_CONFIG.branches.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    select.innerHTML = '<option value="">Semua Cabang</option>' + options;
}

function setupTabNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');
    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            sections.forEach(s => s.classList.add('hidden'));
            const targetId = this.getAttribute('href').substring(1);
            document.getElementById(targetId)?.classList.remove('hidden');
        });
    });
}

function viewBranchDetail(branchId) {
    const branch = HRIS_CONFIG.branches.find(b => b.id === branchId);
    if (!branch) return;
    showToast(`Fitur detail cabang ${branch.name} sedang kami kembangkan. Pantau terus ya!`, 'info');
}

// ========== MESIN ABSENSI (Monitoring) ==========
let devicesData = [];

async function fetchDevices() {
    try {
        const response = await fetch(`${API_BASE}/attendance-devices`);
        if (!response.ok) {
            if (response.status === 401) return;
            throw new Error('Gagal memuat daftar mesin');
        }
        devicesData = await response.json();
        renderDevicesCards();
        if (typeof HRIS_DOMAIN !== 'undefined') {
            const el = document.getElementById('devicesDomainDisplay');
            if (el) el.textContent = HRIS_DOMAIN;
        }
    } catch (error) {
        console.error('Gagal mengambil data mesin absensi:', error);
        showToast('Tidak bisa memuat daftar mesin. Silakan coba lagi.', 'error');
        renderDevicesCards(); // render empty state
    }
}

function renderDevicesCards() {
    const container = document.getElementById('devicesCards');
    if (!container) return;

    if (!devicesData || devicesData.length === 0) {
        container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">Belum ada mesin absensi terdaftar. Tambahkan di database (template: CKEB223560955).</p>';
        return;
    }

    container.innerHTML = devicesData.map(dev => {
        const status = (dev.status || 'active').toLowerCase() === 'active' ? 'ONLINE' : (dev.status || 'Unknown');
        const statusColor = status === 'ONLINE' ? '#10b981' : 'var(--text-muted)';
        const lastSync = dev.last_sync ? dev.last_sync.replace('T', ' ').slice(0, 19) : '-';
        const branchName = getBranchName(dev.branch_id);
        return `
            <div class="card device-card">
                <div class="card-content">
                    <p class="card-label">${dev.device_name || dev.id} ${dev.serial_no ? '(' + dev.serial_no + ')' : ''}</p>
                    <h3 class="card-value" style="color: ${statusColor};">${status}</h3>
                    <p class="card-desc">Cabang: ${branchName}</p>
                    <p class="card-desc">Last Sync: ${lastSync}</p>
                    ${dev.device_ip ? `<p class="card-desc" style="font-size: 0.8rem;">IP: ${dev.device_ip}</p>` : ''}
                    
                    <div class="device-actions" style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button class="btn-secondary btn-sm" onclick="remoteSyncTime('${dev.id}')" title="Sync Jam Mesin">
                            <i class="fas fa-clock"></i> Sync Time
                        </button>
                        <button class="btn-secondary btn-sm" onclick="remoteRestart('${dev.id}')" title="Restart Mesin">
                            <i class="fas fa-redo"></i> Restart
                        </button>
                        <button class="btn-deactivate btn-sm" onclick="remoteClearLogs('${dev.id}')" title="Hapus Log di Mesin">
                            <i class="fas fa-trash-alt"></i> Clear Logs
                        </button>
                    </div>
                </div>
                <div class="card-icon">
                    <i class="fas fa-fingerprint"></i>
                </div>
            </div>
        `;
    }).join('');
}

// Handler Fitur SOAP (Remote Control)
async function remoteSyncTime(deviceId) {
    showToast('Menyinkronkan waktu...', 'info');
    try {
        const res = await fetch(`${API_BASE}/devices/${deviceId}/soap/sync-time`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) showToast(data.message, 'success');
        else showToast(data.error || 'Gagal sinkron waktu', 'error');
    } catch (e) { showToast('Koneksi gagal', 'error'); }
}

async function remoteRestart(deviceId) {
    const ok = await showConfirm('Apakah Anda yakin ingin merestart mesin ini?');
    if (!ok) return;
    showToast('Mengirim perintah restart...', 'info');
    try {
        const res = await fetch(`${API_BASE}/devices/${deviceId}/soap/restart`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) showToast(data.message, 'success');
        else showToast(data.error || 'Gagal restart', 'error');
    } catch (e) { showToast('Koneksi gagal', 'error'); }
}

async function remoteClearLogs(deviceId) {
    const ok = await showConfirm('PERHATIAN: Ini akan menghapus SEMUA data absensi di mesin (bukan di database). Lanjutkan?');
    if (!ok) return;
    showToast('Menghapus log di mesin...', 'info');
    try {
        const res = await fetch(`${API_BASE}/devices/${deviceId}/soap/clear-logs`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) showToast(data.message, 'success');
        else showToast(data.error || 'Gagal hapus log', 'error');
    } catch (e) { showToast('Koneksi gagal', 'error'); }
}

function syncAllDevices() {
    showToast('Memuat ulang daftar mesin...', 'info');
    fetchDevices();
}

document.addEventListener('DOMContentLoaded', function () {
    // Check Auth first
    checkAuth();

    // Login Form Listener
    const loginForm = document.getElementById('loginForm');
    if (loginForm) loginForm.addEventListener('submit', handleLogin);

    renderBranchTags();
    renderDashboardCards();
    renderReportCards();
    renderBranchFilter();
    setupTabNavigation();

    // Initialize report filters
    populateReportBranchFilter();

    // Event listeners for new filters
    const searchAttendance = document.getElementById('searchAttendance');
    if (searchAttendance) searchAttendance.addEventListener('input', handleAttendanceFilter);

    const searchReport = document.getElementById('searchReport');
    if (searchReport) searchReport.addEventListener('input', handleReportFilter);

    // Initial date overlay set for all date inputs
    document.querySelectorAll('input[type="date"]').forEach(input => {
        handleDateInputDisplay(input);
        input.addEventListener('input', () => handleDateInputDisplay(input));
    });
});