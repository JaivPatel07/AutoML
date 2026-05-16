// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const cleanBtn = document.getElementById('cleanBtn');
const resetBtn = document.getElementById('resetBtn');
const downloadBtn = document.getElementById('downloadBtn');
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

let selectedFile = null;

// File Upload Handlers
uploadBox.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

// Drag and drop
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

// Toggle categorical constant input visibility
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
    uploadBox.style.borderColor = '#ffffff';
    // Generate Preview before cleaning
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

// Clean File
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
                progressBarContainer.style.display = 'none'; // Hide progress bar after upload

                // Load the data
                await Promise.all([
                    loadOriginalData(),
                    loadCleanedData(),
                    loadRemovedData(),
                    loadReport()
                ]);
                
                showLoading(false);
                // Hide only the upload interaction elements, not the whole section
                uploadBox.style.display = 'none';
                cleanBtn.style.display = 'none';
                previewSection.style.display = 'none';
                
                resultsSection.style.display = 'block';
                resetBtn.style.display = 'block';
                downloadBtn.style.display = 'block';
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
// Load Original Data
async function loadOriginalData() {
    const response = await fetch('/view/original');
    const data = await response.json();
    document.getElementById('originalRows').textContent = data.total_rows.toLocaleString();
    document.getElementById('originalCols').textContent = data.columns.length;
    renderTable('originalTable', data);
}

// Load Cleaned Data
async function loadCleanedData() {
    const response = await fetch('/view/cleaned');
    const data = await response.json();
    document.getElementById('cleanedRows').textContent = data.total_rows.toLocaleString();
    document.getElementById('cleanedCols').textContent = data.columns.length;
    renderTable('cleanedTable', data);
}

// Load Removed Data
async function loadRemovedData() {
    const response = await fetch('/view/removed');
    const data = await response.json();
    document.getElementById('removedRows').textContent = data.total_rows.toLocaleString();
    document.getElementById('removedCols').textContent = data.columns.length;
    renderTable('removedTable', data);
}

// Load Report
async function loadReport() {
    try {
        const response = await fetch('/report');
        const report = await response.json();
        const reportContent = document.getElementById('reportContent');

        let html = '<div class="report-view">';

        // 1. Executive Summary
        html += '<div class="report-section"><h3>Summary</h3><ul>';
        html += `<li><strong>Initial Data:</strong> ${report.initial_shape[0]} rows × ${report.initial_shape[1]} columns</li>`;
        html += `<li><strong>Cleaned Data:</strong> ${report.final_shape[0]} rows × ${report.final_shape[1]} columns</li>`;
        html += `<li><strong>Memory Optimized:</strong> ${report.memory_before_mb}MB → ${report.memory_after_mb}MB</li>`;
        html += `<li><strong>Duplicates Removed:</strong> ${report.duplicate_rows_removed.length} rows</li>`;
        html += `<li><strong>Outlier Removal Enabled:</strong> ${report.outlier_removal_enabled ? 'Yes' : 'No'}</li>`;
        html += '</ul></div>';

        // 2. Structural Changes
        if (report.removed_columns.length > 0) {
            html += '<div class="report-section"><h3>Dropped Columns</h3><ul>';
            report.removed_columns.forEach(col => {
                const reason = report.flagged_reasons && report.flagged_reasons[col] ? ` — <em>${report.flagged_reasons[col]}</em>` : '';
                html += `<li><strong>${col}</strong>${reason}</li>`;
            });
            html += '</ul></div>';
        }

        // 3. Standardization (Junk removal)
        if (report.replaced_values && report.replaced_values.length > 0) {
            html += '<div class="report-section"><h3>Standardization</h3><ul>';
            report.replaced_values.forEach(item => {
                html += `<li>Column <strong>${item.column}</strong>: Cleaned repetitive/junk value "${item.old_value}"</li>`;
            });
            html += '</ul></div>';
        }

        // 4. Missing Values (Imputation)
        const filledCols = Object.keys(report.filled_values);
        if (filledCols.length > 0) {
            html += '<div class="report-section"><h3>Data Imputation</h3><ul>';
            filledCols.forEach(col => {
                const info = report.filled_values[col];
                html += `<li><strong>${col}</strong>: Imputed ${info.count} missing cells using <em>${info.method}</em></li>`;
            });
            html += '</ul></div>';
        }

        // 5. Outliers
        const outlierCols = Object.keys(report.outliers);
        if (outlierCols.length > 0) {
            html += '<div class="report-section"><h3>Outlier Detection</h3><ul>';
            outlierCols.forEach(col => {
                html += `<li><strong>${col}</strong>: Flagged ${report.outliers[col].count} statistical outliers</li>`;
            });
            html += '</ul></div>';
        }

        // 6. Detailed Processing Logs
        if (report.logs && report.logs.length > 0) {
            html += '<div class="report-section"><h3>Full Processing Log</h3><ul class="log-list">';
            report.logs.forEach(log => html += `<li>${log}</li>`);
            html += '</ul></div>';
        }

        html += '</div>';
        reportContent.innerHTML = html;
    } catch (error) {
        console.error('Error rendering report:', error);
    }
}
// Render Table Helper
function renderTable(tableId, data) {
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    
    if (data.data.length === 0) return;
    
    // Header
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
    // Rows
    data.data.slice(0, 50).forEach((row, rowIndex) => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            const val = row[col];
            td.textContent = val === null ? 'Missing' : String(val).substring(0, 50);
            
            // Highlight outliers
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
// Tab Navigation
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

// Download Function
downloadBtn.addEventListener('click', () => {
    window.location.href = '/download';
});

// Reset Function
resetBtn.addEventListener('click', () => {
    location.reload();
});

// Utility Functions
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
