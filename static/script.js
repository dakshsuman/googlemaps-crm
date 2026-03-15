let currentLeads = [];
let currentLeadId = null;
let currentFilter = 'Pending';
let searchQuery = '';

let sortCol = null;
let sortAsc = true;
let colFilters = {};

document.addEventListener('DOMContentLoaded', () => {
    initApp();

    document.getElementById('searchInput').addEventListener('input', (e) => {
        searchQuery = e.target.value;
        fetchLeads();
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.getAttribute('data-filter');
            fetchLeads();
        });
    });

    document.querySelectorAll('.col-filter').forEach(input => {
        input.addEventListener('input', (e) => {
            colFilters[e.target.dataset.col] = e.target.value.toLowerCase();
            renderLeadsTable();
        });
    });
});

function sortTable(col) {
    if (sortCol === col) {
        sortAsc = !sortAsc;
    } else {
        sortCol = col;
        sortAsc = true;
    }

    // Update sort icons visually
    document.querySelectorAll('.th-content.sortable i').forEach(icon => {
        icon.className = 'bi bi-arrow-down-up';
        icon.style.opacity = '0.3';
    });
    
    // Using simple text matching for the function name inside onclick to get the active header
    const activeTh = Array.from(document.querySelectorAll('.th-content.sortable')).find(th => 
        th.getAttribute('onclick') && th.getAttribute('onclick').includes(`'${col}'`)
    );
    if (activeTh) {
        const icon = activeTh.querySelector('i');
        icon.className = sortAsc ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
        icon.style.opacity = '1';
    }

    // Sort the dataset
    currentLeads.sort((a, b) => {
        let valA = a[col];
        let valB = b[col];

        if (valA === null || valA === undefined) valA = '';
        if (valB === null || valB === undefined) valB = '';

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();

        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
    });

    renderLeadsTable();
}

async function initApp() {
    await fetchStats();
    await fetchLeads();
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        
        document.getElementById('stat-total').innerText = `${stats['Total']} Total`;
        document.getElementById('stat-pending').innerText = `${stats['Pending']} Pending`;
    } catch (e) {
        console.error("Failed to fetch stats", e);
    }
}

async function fetchLeads() {
    try {
        const res = await fetch(`/api/leads?status=${encodeURIComponent(currentFilter)}&search=${encodeURIComponent(searchQuery)}`);
        currentLeads = await res.json();
        
        // Re-apply sorting if active
        if (sortCol) {
            const tempSortAsc = sortAsc;
            // Unset temporarily to trick sortTable into keeping same order direction 
            sortAsc = !tempSortAsc;
            sortTable(sortCol);
        } else {
            renderLeadsTable();
        }
    } catch (e) {
        console.error("Failed to fetch leads", e);
    }
}

function renderLeadsTable() {
    const tableBody = document.getElementById('leadsTableBody');
    tableBody.innerHTML = '';
    
    // Apply local column filters
    let displayLeads = currentLeads.filter(lead => {
        for (let col in colFilters) {
            if (colFilters[col]) {
                const val = String(lead[col] || '').toLowerCase();
                if (!val.includes(colFilters[col])) {
                    return false;
                }
            }
        }
        return true;
    });

    if (displayLeads.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" class="empty-table">No leads found.</td></tr>`;
        return;
    }

    displayLeads.forEach(lead => {
        const tr = document.createElement('tr');
        tr.className = `lead-tr ${lead.id === currentLeadId ? 'active-row' : ''}`;
        
        // Status badge formatting
        const badgeClass = 'badge-sm badge status-' + lead.status.toLowerCase().replace(' ', '');
        
        tr.innerHTML = `
            <td><span class="${badgeClass}">${lead.status}</span></td>
            <td class="td-name" title="${lead.name || 'Unknown'}">${lead.name || 'Unknown'}</td>
            <td>${lead.phone || '<span style="color:#6c757d">No Phone</span>'}</td>
            <td class="td-website">${lead.website ? `<a href="${lead.website}" target="_blank">View Site <i class="bi bi-box-arrow-up-right"></i></a>` : '<span style="color:#6c757d">-</span>'}</td>
            <td class="td-category" title="${lead.category || 'N/A'}">${lead.category || 'N/A'}</td>
            <td><i class="bi bi-star-fill text-warning"></i> ${lead.rating || 'N/A'}</td>
            <td>${lead.reviews || '0'}</td>
            <td class="td-address" title="${lead.address || 'N/A'}">${lead.address || 'N/A'}</td>
        `;

        tr.onclick = () => selectLead(lead, tr);
        tableBody.appendChild(tr);
    });
}

function selectLead(lead) {
    currentLeadId = lead.id;
    
    // Highlight correct row
    document.querySelectorAll('.lead-tr').forEach(row => row.classList.remove('active-row'));
    renderLeadsTable(); // Re-render highlights active row
    
    // Show top panel
    document.getElementById('lead-details').classList.remove('hidden');

    document.getElementById('l-category').innerText = lead.category || 'N/A';
    document.getElementById('l-name').innerText = lead.name || 'Unknown';
    document.getElementById('l-rating').innerText = lead.rating || '0.0';
    document.getElementById('l-reviews').innerText = lead.reviews || '0';
    
    const phoneEl = document.getElementById('l-phone');
    if (lead.phone) {
        document.getElementById('l-phone-text').innerText = lead.phone;
        phoneEl.href = `tel:${lead.phone}`;
        phoneEl.style.pointerEvents = 'auto';
    } else {
        document.getElementById('l-phone-text').innerText = 'No Phone';
        phoneEl.href = '#';
        phoneEl.style.pointerEvents = 'none';
        phoneEl.style.color = '#adb5bd';
    }

    const webEl = document.getElementById('l-website');
    if (lead.website) {
        webEl.style.display = 'flex';
        webEl.href = lead.website;
        webEl.style.color = '';
    } else {
        webEl.style.display = 'none';
    }

    document.getElementById('l-address').innerText = lead.address || 'N/A';
    document.getElementById('lead-notes').value = lead.notes || '';

    // Status Badge Update
    const badgeEl = document.getElementById('l-status-badge');
    badgeEl.innerText = lead.status;
    badgeEl.className = 'badge badge-sm status-' + lead.status.toLowerCase().replace(' ', '');
}

function closeLead() {
    currentLeadId = null;
    document.getElementById('lead-details').classList.add('hidden');
    renderLeadsTable(); // update highlights
}

async function updateStatus(newStatus) {
    if (!currentLeadId) return;

    try {
        await fetch(`/api/leads/${currentLeadId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        // Remove from list if filter doesn't match anymore
        if (currentFilter !== 'All' && currentFilter !== newStatus) {
            currentLeads = currentLeads.filter(l => l.id !== currentLeadId);
            closeLead();
        } else {
            // Update in place
            const updated = currentLeads.find(l => l.id === currentLeadId);
            if(updated) updated.status = newStatus;
            
            // Update badge UI
            const badgeEl = document.getElementById('l-status-badge');
            badgeEl.innerText = newStatus;
            badgeEl.className = 'badge badge-sm status-' + newStatus.toLowerCase().replace(' ', '');
        }
        
        renderLeadsTable();
        fetchStats();
    } catch (e) {
        alert("Failed to update status");
    }
}

async function saveNotes() {
    if (!currentLeadId) return;
    const notes = document.getElementById('lead-notes').value;

    const btn = document.querySelector('.btn-save');
    const ogText = btn.innerText;
    btn.innerText = 'Saving...';
    
    try {
        await fetch(`/api/leads/${currentLeadId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });
        
        const updated = currentLeads.find(l => l.id === currentLeadId);
        if(updated) updated.notes = notes;
        
        btn.innerText = 'Saved!';
        setTimeout(() => btn.innerText = ogText, 2000);
    } catch (e) {
        alert("Failed to save notes");
        btn.innerText = ogText;
    }
}
