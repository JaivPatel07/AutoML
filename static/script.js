const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const cleanBtn = document.getElementById('cleanBtn');
const resetBtn = document.getElementById('resetBtn');
const downloadBtn = document.getElementById('downloadBtn');
const predictBtn = document.getElementById('predictBtn');
const userOptionsDiv = document.getElementById('userOptions');
const dropColsInput = document.getElementById('dropCols');
const outlierToggle = document.getElementById('outlierToggle');
const outlierThresh = document.getElementById('outlierThresh');
const numFill = document.getElementById('numFill');
const catFill = document.getElementById('catFill');
const catConst = document.getElementById('catConst');
const progressBarContainer = document.getElementById('progressBarContainer');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const loadingSpinner = document.getElementById('loadingSpinner');
const previewSection = document.getElementById('previewSection');
const resultsSection = document.getElementById('resultsSection');
const errorMessage = document.getElementById('errorMessage');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');

let selectedFile = null;
let missingChart = null;
let retentionChart = null;
let lastReportData = null;

function renderThemeIcon(isDark) {
    if (!themeIcon) return;

    themeIcon.innerHTML = isDark
        ? `
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.8 6.8 0 0 0 21 12.8Z" fill="currentColor"></path>
            </svg>
        `
        : `
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" stroke-width="1.8"></circle>
                <path d="M12 2.5v2.2M12 19.3v2.2M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
            </svg>
        `;
}

// Theme Management
function getChartTheme() {
    const styles = getComputedStyle(document.body);

    return {
        primary: styles.getPropertyValue('--text-color').trim(),
        accent: styles.getPropertyValue('--accent-yellow').trim(),
        grid: styles.getPropertyValue('--grid-color').trim(),
        text: styles.getPropertyValue('--text-color').trim()
    };
}

function updateThemeUI(isDark) {
    document.body.classList.toggle('dark-mode', isDark);
    renderThemeIcon(isDark);
    if (themeToggle) {
        themeToggle.title = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
}

function initTheme() {
    try {
        const savedTheme = localStorage.getItem('theme');
        const isDark = savedTheme === 'dark';
        updateThemeUI(isDark);
    } catch (e) {
        console.warn("Theme initialization suppressed: localStorage is unavailable.");
    }
}

function toggleTheme() {
    try {
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('theme', !isDark ? 'dark' : 'light');
        updateThemeUI(!isDark);
        
        if (lastReportData) {
            renderMissingValuesChart(lastReportData);
            renderDataRetentionChart(lastReportData);
        }
    } catch (e) {
        console.error("Theme toggle failed:", e);
    }
}

if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
}
initTheme();

uploadBox.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    handleFileSelect(e.dataTransfer.files[0]);
});

catFill.addEventListener('change', () => {
    catConst.style.display = catFill.value === 'constant' ? 'block' : 'none';
});

async function handleFileSelect(file) {
    if (!file) return;
    
    const allowedExtensions = ['.csv', '.xlsx', '.xls'];
    if (!allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))) {
        showError('Please upload a CSV or Excel file');
        return;
    }
    
    selectedFile = file;
    dropColsInput.value = '';
    uploadBox.querySelector('p').textContent = `✓ Selected: ${file.name}`;
    uploadBox.style.borderColor = 'var(--primary-black)';
    await loadPreview(file);
    errorMessage.style.display = 'none';
}

async function loadPreview(file) {
    try {
        showLoading(true, 'Generating data preview...');
        document.getElementById('previewSection').style.display = 'none';
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/preview', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Failed to load preview');
        
        const data = await response.json();
        document.getElementById('previewSection').style.display = 'block';
        document.getElementById('previewStats').textContent = `Total Rows: ${data.total_rows.toLocaleString()} | Total Columns: ${data.columns.length}`;
        
        if (data.auto_flagged && Object.keys(data.auto_flagged).length > 0) {
            dropColsInput.value = Object.keys(data.auto_flagged).join(', ');
        }
        
        renderTable('previewTable', data);
        
        userOptionsDiv.style.display = 'flex';
        cleanBtn.style.display = 'block';
        showLoading(false);
    } catch (error) {
        showLoading(false);
        showError('Error generating preview: ' + error.message);
    }
}

async function loadViewData(endpoint, rowElementId, colElementId, tableId) {
    const response = await fetch(endpoint);
    const data = await response.json();
    document.getElementById(rowElementId).textContent = data.total_rows.toLocaleString();
    document.getElementById(colElementId).textContent = data.columns.length;
    renderTable(tableId, data);
}

cleanBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    try {
        showLoading(true, 'Uploading file...');
        errorMessage.style.display = 'none';
        progressBarContainer.style.display = 'flex';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        
        const colsToDrop = dropColsInput.value;
        const dropOutliers = outlierToggle.checked;
        const thresh = outlierThresh.value;
        const numMethod = numFill.value;
        const catMethod = catFill.value;
        const constVal = catConst.value;

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('drop_cols', colsToDrop);
        formData.append('use_outliers', dropOutliers);
        formData.append('outlier_thresh', thresh);
        formData.append('num_fill', numMethod);
        formData.append('cat_fill', catMethod);
        formData.append('categorical_constant', constVal);
        
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/clean', true);

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                progressBar.style.width = `${percent}%`;
                progressText.textContent = `${percent}%`;
            }
        };

        xhr.onload = async () => {
            if (xhr.status === 200) {
                showLoading(true, 'Processing and cleaning data...');
                progressBarContainer.style.display = 'none';

                await Promise.all([
                    loadOriginalData(),
                    loadCleanedData(),
                    loadRemovedData(),
                    loadReport()
                ]);
                
                showLoading(false);
                uploadBox.style.display = 'none';
                cleanBtn.style.display = 'none';
                previewSection.style.display = 'none';
                
                resultsSection.style.display = 'block';
                resetBtn.style.display = 'block';
                downloadBtn.style.display = 'block';
                predictBtn.style.display = 'block';
                userOptionsDiv.style.display = 'none';
            } else {
                showLoading(false);
                progressBarContainer.style.display = 'none';
                const errorData = JSON.parse(xhr.responseText);
                showError('Error cleaning file: ' + (errorData.detail || 'Unknown error'));
                console.error('Error:', xhr.status, xhr.responseText);
            }
        };

        xhr.onerror = () => {
            showLoading(false);
            progressBarContainer.style.display = 'none';
            showError('Network error during file upload or cleaning.');
            console.error('Network error.');
        };

        xhr.send(formData);

    } catch (error) {
        showLoading(false);
        progressBarContainer.style.display = 'none';
        showError('Error cleaning file: ' + error.message);
        console.error(error);
    }
});
async function loadOriginalData() {
    return loadViewData('/view/original', 'originalRows', 'originalCols', 'originalTable');
}

async function loadCleanedData() {
    return loadViewData('/view/cleaned', 'cleanedRows', 'cleanedCols', 'cleanedTable');
}

async function loadRemovedData() {
    return loadViewData('/view/removed', 'removedRows', 'removedCols', 'removedTable');
}

async function loadReport() {
    try {
        const response = await fetch('/report');
        const report = await response.json();
        lastReportData = report;
        const reportContent = document.getElementById('reportContent');

        let html = '<div class="report-view">';

        html += '<div class="report-section"><h3>Summary</h3><ul>';
        html += `<li><strong>Initial Data:</strong> ${report.initial_shape[0]} rows × ${report.initial_shape[1]} columns</li>`;
        html += `<li><strong>Cleaned Data:</strong> ${report.final_shape[0]} rows × ${report.final_shape[1]} columns</li>`;
        html += `<li><strong>Memory Optimized:</strong> ${report.memory_before_mb}MB → ${report.memory_after_mb}MB</li>`;
        html += `<li><strong>Duplicates Removed:</strong> ${report.duplicate_rows_removed.length} rows</li>`;
        html += `<li><strong>Outlier Removal Enabled:</strong> ${report.outlier_removal_enabled ? 'Yes' : 'No'}</li>`;
        html += '</ul></div>';

        html += '<div class="report-section"><h3>Missing Values Comparison</h3><div class="chart-container"><canvas id="missingValuesChart"></canvas></div></div>';

        html += '<div class="report-section"><h3>Data Retention Summary</h3><div class="chart-container"><canvas id="dataRetentionChart"></canvas></div></div>';

        if (report.removed_columns.length > 0) {
            html += '<div class="report-section"><h3>Dropped Columns</h3><ul>';
            report.removed_columns.forEach(col => {
                const reason = report.flagged_reasons && report.flagged_reasons[col] ? ` — <em>${report.flagged_reasons[col]}</em>` : '';
                html += `<li><strong>${col}</strong>${reason}</li>`;
            });
            html += '</ul></div>';
        }

        if (report.replaced_values && report.replaced_values.length > 0) {
            html += '<div class="report-section"><h3>Standardization</h3><ul>';
            report.replaced_values.forEach(item => {
                html += `<li>Column <strong>${item.column}</strong>: Cleaned repetitive/junk value "${item.old_value}"</li>`;
            });
            html += '</ul></div>';
        }

        const filledCols = Object.keys(report.filled_values);
        if (filledCols.length > 0) {
            html += '<div class="report-section"><h3>Data Imputation</h3><ul>';
            filledCols.forEach(col => {
                const info = report.filled_values[col];
                html += `<li><strong>${col}</strong>: Imputed ${info.count} missing cells using <em>${info.method}</em></li>`;
            });
            html += '</ul></div>';
        }

        const outlierCols = Object.keys(report.outliers);
        if (outlierCols.length > 0) {
            html += '<div class="report-section"><h3>Outlier Detection</h3><ul>';
            outlierCols.forEach(col => {
                html += `<li><strong>${col}</strong>: Flagged ${report.outliers[col].count} statistical outliers</li>`;
            });
            html += '</ul></div>';
        }

        if (report.logs && report.logs.length > 0) {
            html += '<div class="report-section"><h3>Full Processing Log</h3><ul class="log-list">';
            report.logs.forEach(log => html += `<li>${log}</li>`);
            html += '</ul></div>';
        }

        html += '</div>';
        reportContent.innerHTML = html;

        renderMissingValuesChart(report);
        renderDataRetentionChart(report);
    } catch (error) {
        console.error('Error rendering report:', error);
    }
}

function renderMissingValuesChart(report) {
    const ctx = document.getElementById('missingValuesChart');
    if (!ctx) return;

    if (missingChart) missingChart.destroy();

    const theme = getChartTheme();
    const labels = Object.keys(report.missing_before);
    const beforeData = labels.map(label => report.missing_before[label]);
    const afterData = labels.map(label => report.missing_after[label] || 0);

    missingChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Before Cleaning',
                    data: beforeData,
                    backgroundColor: theme.primary,
                    borderColor: theme.primary,
                    borderWidth: 1
                },
                {
                    label: 'After Cleaning',
                    data: afterData,
                    backgroundColor: theme.accent,
                    borderColor: theme.primary,
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { 
                    beginAtZero: true, 
                    ticks: { precision: 0, color: theme.text },
                    grid: { color: theme.grid }
                },
                x: {
                    ticks: { color: theme.text },
                    grid: { color: theme.grid }
                }
            },
            plugins: { legend: { position: 'top', labels: { color: theme.text } } }
        }
    });
}

function renderDataRetentionChart(report) {
    const ctx = document.getElementById('dataRetentionChart');
    if (!ctx) return;

    if (retentionChart) retentionChart.destroy();

    const theme = getChartTheme();
    const kept = report.final_shape[0];
    const initial = report.initial_shape[0];
    const removed = initial - kept;

    retentionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Rows Kept', 'Rows Removed'],
            datasets: [{
                data: [kept, removed],
                backgroundColor: [theme.primary, theme.accent],
                borderColor: theme.primary,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: theme.text }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = initial;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${value.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderTable(tableId, data) {
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    
    if (data.data.length === 0) return;
    
    const headerRow = document.createElement('tr');
    const maxCols = 50;
    const columns = data.columns.slice(0, maxCols);
    
    columns.forEach(col => {
        const th = document.createElement('th');
        
        if (tableId === 'previewTable') {
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'center';
            wrapper.style.gap = '8px';
            
            const flaggedReason = data.auto_flagged ? data.auto_flagged[col] : null;
            const isAutoRemoved = !!flaggedReason;
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = !isAutoRemoved;
            cb.title = isAutoRemoved ? `Suggested removal: ${flaggedReason}` : "Uncheck to drop column";
            
            if (isAutoRemoved) {
                th.classList.add('flagged-header');
            }

            cb.addEventListener('change', () => {
                let current = dropColsInput.value
                    .split(',')
                    .map(s => s.trim())
                    .filter(s => s !== "");
                
                if (!cb.checked) {
                    if (!current.includes(col)) current.push(col);
                } else {
                    current = current.filter(c => c !== col);
                }
                dropColsInput.value = current.join(', ');
            });

            const label = document.createElement('span');
            label.textContent = col;

            wrapper.appendChild(cb);
            wrapper.appendChild(label);
            
            if (isAutoRemoved) {
                const tag = document.createElement('span');
                tag.className = 'auto-tag';
                tag.textContent = 'AUTO';
                tag.title = flaggedReason;
                wrapper.appendChild(tag);
            }
            
            th.appendChild(wrapper);
        } else {
            th.textContent = col;
        }
        headerRow.appendChild(th);
    });
    if (data.columns.length > maxCols) {
        const thDots = document.createElement('th');
        thDots.textContent = '...';
        headerRow.appendChild(thDots);
    }
    tbody.appendChild(headerRow);
    data.data.slice(0, 50).forEach((row, rowIndex) => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            const val = row[col];
            td.textContent = val === null ? 'Missing' : String(val).substring(0, 50);
            
            if (data.outliers_found && data.outliers_found[rowIndex] && data.outliers_found[rowIndex].includes(col)) {
                td.classList.add('outlier-cell');
                td.title = "Statistical Outlier";
            }

            tr.appendChild(td);
        });
        if (data.columns.length > maxCols) {
            const tdDots = document.createElement('td');
            tdDots.textContent = '...';
            tr.appendChild(tdDots);
        }
        tbody.appendChild(tr);
    });
}
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

downloadBtn.addEventListener('click', () => {
    window.location.href = '/download';
});

predictBtn.addEventListener('click', () => {
    alert('Prediction feature placeholder: The cleaned data is now ready for model training or inference!');
});

resetBtn.addEventListener('click', () => {
    location.reload();
});

function showLoading(show, message = '') {
    loadingSpinner.style.display = show ? 'block' : 'none';
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.style.display = show ? 'block' : 'none';
    statusMessage.textContent = message;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}
