// Dashboard JavaScript

let refreshInterval;
let autoRefreshEnabled = true;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    updateCurrentTime();
    loadDashboardData();
    
    // Set up auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
        if (autoRefreshEnabled) {
            updateCurrentTime();
            loadDashboardData();
        }
    }, 30000);
    
    // Update time every second
    setInterval(updateCurrentTime, 1000);
});

function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleString();
}

async function loadDashboardData() {
    try {
        // Load all data in parallel
        const [stats, health, documents] = await Promise.all([
            fetch('/api/stats').then(r => r.json()),
            fetch('/api/health').then(r => r.json()),
            fetch('/api/documents').then(r => r.json())
        ]);
        
        updateStatistics(stats);
        updateServiceHealth(health.services);
        updateDocumentsTable(documents.documents);
        updatePipelineStatus(health.services);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Failed to load dashboard data');
    }
}

function updateStatistics(stats) {
    document.getElementById('total-documents').textContent = stats.total_documents;
    document.getElementById('processing-documents').textContent = stats.processing_documents;
    document.getElementById('completed-documents').textContent = stats.completed_documents;
    document.getElementById('failed-documents').textContent = stats.failed_documents;
    document.getElementById('es-docs').textContent = stats.elasticsearch_docs;
    document.getElementById('qdrant-collections').textContent = stats.qdrant_collections;
}

function updateServiceHealth(services) {
    const container = document.getElementById('services-health');
    
    if (!services || services.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No services available</div>';
        return;
    }
    
    const html = services.map(service => {
        const statusClass = getStatusClass(service.status);
        const statusIcon = getStatusIcon(service.status);
        
        return `
            <div class="service-status">
                <div class="d-flex align-items-center">
                    <span class="status-indicator ${statusClass}"></span>
                    <a href="/service/${service.service}" class="service-name text-decoration-none">
                        ${formatServiceName(service.service)}
                        <i class="fas fa-external-link-alt ms-1 text-muted" style="font-size: 0.8em;"></i>
                    </a>
                </div>
                <div class="text-end">
                    <div class="status-text ${service.status}">${service.status}</div>
                    <div class="response-time">${service.response_time.toFixed(2)}s</div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function updateDocumentsTable(documents) {
    const tbody = document.getElementById('documents-table');
    
    if (!documents || documents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No documents found</td></tr>';
        return;
    }
    
    // Sort by created_at (newest first)
    documents.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    // Show only the 10 most recent documents
    const recentDocs = documents.slice(0, 10);
    
    const html = recentDocs.map(doc => {
        const statusClass = getStatusClass(doc.processing_status);
        const statusBadge = getStatusBadge(doc.processing_status);
        const fileSize = formatFileSize(doc.file_size);
        const createdDate = new Date(doc.created_at).toLocaleString();
        
        return `
            <tr>
                <td>
                    <div class="fw-medium">${doc.filename}</div>
                    <div class="text-muted small">${doc.document_type}</div>
                </td>
                <td>
                    <span class="source-badge">${doc.source}</span>
                </td>
                <td>
                    <span class="status-badge ${statusClass}">${statusBadge}</span>
                </td>
                <td>
                    <span class="file-size">${fileSize}</span>
                </td>
                <td>
                    <div class="small">${createdDate}</div>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewDocumentDetails('${doc.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    tbody.innerHTML = html;
}

function updatePipelineStatus(services) {
    const container = document.getElementById('pipeline-status');
    
    const pipelineServices = [
        { name: 'text-processor', icon: 'fas fa-file-alt', title: 'Text Extraction' },
        { name: 'metadata-processor', icon: 'fas fa-tags', title: 'Metadata Extraction' },
        { name: 'embedding-processor', icon: 'fas fa-brain', title: 'Embedding Generation' },
        { name: 'entity-processor', icon: 'fas fa-sitemap', title: 'Entity Extraction' },
        { name: 'processing-pipeline', icon: 'fas fa-cogs', title: 'Pipeline Orchestration' }
    ];
    
    const html = pipelineServices.map(service => {
        const serviceData = services.find(s => s.service === service.name);
        const status = serviceData ? serviceData.status : 'unknown';
        const statusClass = getStatusClass(status);
        const statusIcon = getStatusIcon(status);
        
        return `
            <div class="pipeline-step ${statusClass}">
                <div class="pipeline-icon">
                    <i class="${service.icon}"></i>
                </div>
                <div class="pipeline-text">
                    <div class="fw-medium">${service.title}</div>
                    <div class="small text-muted">${service.name}</div>
                </div>
                <div class="pipeline-time">
                    <i class="${statusIcon}"></i>
                    ${status}
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

async function viewDocumentDetails(documentId) {
    try {
        const response = await fetch(`/api/documents/${documentId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch document details');
        }
        
        const data = await response.json();
        const modal = new bootstrap.Modal(document.getElementById('documentModal'));
        
        const content = `
            <div class="row">
                <div class="col-md-6">
                    <div class="document-detail">
                        <h6>Document Information</h6>
                        <p><strong>ID:</strong> ${data.document.id}</p>
                        <p><strong>Filename:</strong> ${data.document.filename}</p>
                        <p><strong>Type:</strong> ${data.document.document_type}</p>
                        <p><strong>Size:</strong> ${formatFileSize(data.document.file_size)}</p>
                        <p><strong>Source:</strong> ${data.document.source}</p>
                        <p><strong>Status:</strong> ${data.document.processing_status}</p>
                    </div>
                    
                    <div class="document-detail">
                        <h6>Timestamps</h6>
                        <p><strong>Created:</strong> ${new Date(data.document.created_at).toLocaleString()}</p>
                        <p><strong>Updated:</strong> ${new Date(data.document.updated_at).toLocaleString()}</p>
                        ${data.document.processed_at ? `<p><strong>Processed:</strong> ${new Date(data.document.processed_at).toLocaleString()}</p>` : ''}
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="document-detail">
                        <h6>Processing Status</h6>
                        ${data.processing_status ? `
                            <div class="mb-2">
                                <strong>Overall Status:</strong> ${data.processing_status.processing_status}
                            </div>
                            ${data.processing_status.processing_jobs ? `
                                <div>
                                    <strong>Jobs:</strong>
                                    <ul class="list-unstyled mt-1">
                                        ${data.processing_status.processing_jobs.map(job => `
                                            <li class="small">
                                                <i class="fas fa-circle ${getStatusClass(job.status)}"></i>
                                                ${job.job_type}: ${job.status}
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        ` : '<p class="text-muted">No processing status available</p>'}
                    </div>
                    
                    ${data.document.metadata ? `
                        <div class="document-detail">
                            <h6>Metadata</h6>
                            <div class="json-viewer">${JSON.stringify(data.document.metadata, null, 2)}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
            
            ${data.elasticsearch_data ? `
                <div class="mt-3">
                    <h6>Elasticsearch Data</h6>
                    <div class="json-viewer">${JSON.stringify(data.elasticsearch_data, null, 2)}</div>
                </div>
            ` : ''}
        `;
        
        document.getElementById('document-modal-content').innerHTML = content;
        modal.show();
        
    } catch (error) {
        console.error('Error fetching document details:', error);
        showError('Failed to load document details');
    }
}

function refreshData() {
    loadDashboardData();
}

function getStatusClass(status) {
    switch (status) {
        case 'healthy':
        case 'completed':
            return 'status-healthy';
        case 'unhealthy':
        case 'failed':
            return 'status-unhealthy';
        case 'error':
        case 'processing':
            return 'status-error';
        default:
            return 'status-error';
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'healthy':
        case 'completed':
            return 'fas fa-check-circle text-success';
        case 'unhealthy':
        case 'failed':
            return 'fas fa-times-circle text-danger';
        case 'error':
            return 'fas fa-exclamation-triangle text-warning';
        case 'processing':
            return 'fas fa-spinner fa-spin text-warning';
        default:
            return 'fas fa-question-circle text-muted';
    }
}

function getStatusBadge(status) {
    switch (status) {
        case 'processing':
            return 'Processing';
        case 'completed':
            return 'Completed';
        case 'failed':
            return 'Failed';
        case 'pending':
            return 'Pending';
        default:
            return status;
    }
}

function formatServiceName(service) {
    return service.split('-').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showError(message) {
    // Create a simple error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    errorDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(errorDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

// Export functions for global access
window.refreshData = refreshData;
window.viewDocumentDetails = viewDocumentDetails; 