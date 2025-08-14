// Dashboard JavaScript

// Global error handler to prevent unhandled exceptions from showing alerts
window.addEventListener('error', function(event) {
    console.error('Global error caught:', event.error);
    // Prevent the default browser error handling
    event.preventDefault();
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    // Prevent the default browser error handling
    event.preventDefault();
});

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
        // Load all data in parallel with individual error handling
        const promises = [
            fetch('/api/stats').then(r => {
                if (!r.ok) {
                    throw new Error(`Stats API returned ${r.status}`);
                }
                return r.json();
            }).catch(e => {
                console.warn('Failed to load stats:', e);
                return { 
                    total_documents: 0, 
                    processing_documents: 0, 
                    completed_documents: 0, 
                    failed_documents: 0, 
                    elasticsearch_docs: 0, 
                    qdrant_collections: 0,
                    healthy_services: 0,
                    total_services: 0,
                    pending_documents: 0
                };
            }),
            fetch('/api/health').then(r => {
                if (!r.ok) {
                    throw new Error(`Health API returned ${r.status}`);
                }
                return r.json();
            }).catch(e => {
                console.warn('Failed to load health:', e);
                return { services: [] };
            }),
            fetch('/api/documents').then(r => {
                if (!r.ok) {
                    throw new Error(`Documents API returned ${r.status}`);
                }
                return r.json();
            }).catch(e => {
                console.warn('Failed to load documents:', e);
                return { documents: [] };
            })
        ];
        
        const [stats, health, documents] = await Promise.all(promises);
        
        // Ensure we have valid data structures even if APIs return unexpected formats
        const safeStats = {
            total_documents: stats?.total_documents || 0,
            processing_documents: stats?.processing_documents || 0,
            completed_documents: stats?.completed_documents || 0,
            failed_documents: stats?.failed_documents || 0,
            elasticsearch_docs: stats?.elasticsearch_docs || 0,
            qdrant_collections: stats?.qdrant_collections || 0,
            healthy_services: stats?.healthy_services || 0,
            total_services: stats?.total_services || 0,
            pending_documents: stats?.pending_documents || 0
        };
        
        const safeHealth = {
            services: Array.isArray(health?.services) ? health.services : []
        };
        
        const safeDocuments = {
            documents: Array.isArray(documents?.documents) ? documents.documents : []
        };
        
        updateStatistics(safeStats);
        updateServiceHealthSummary(safeHealth.services);
        updateDocumentsTable(safeDocuments.documents);
        updatePipelineStatus(safeHealth.services);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        // Don't show error for initial load failures - this is expected when services aren't running yet
        // showError('Failed to load dashboard data');
    }
}

function updateStatistics(stats) {
    try {
        // Ensure stats is a valid object
        if (!stats || typeof stats !== 'object') {
            console.warn('Invalid stats object received:', stats);
            stats = {};
        }
        
        const elements = {
            'total-documents': stats.total_documents || 0,
            'processing-documents': stats.processing_documents || 0,
            'completed-documents': stats.completed_documents || 0,
            'failed-documents': stats.failed_documents || 0,
            'es-docs': stats.elasticsearch_docs || 0,
            'qdrant-collections': stats.qdrant_collections || 0
        };
        
        for (const [id, value] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            } else {
                console.warn(`Element with id '${id}' not found in DOM`);
            }
        }
    } catch (error) {
        console.warn('Error updating statistics:', error);
    }
}

function updateServiceHealthSummary(services) {
    try {
        const healthyElement = document.getElementById('healthy-services');
        const unhealthyElement = document.getElementById('unhealthy-services');
        
        if (!healthyElement || !unhealthyElement) {
            console.warn('Service health elements not found');
            return;
        }
        
        // Ensure services is a valid array
        if (!Array.isArray(services)) {
            console.warn('Invalid services array received:', services);
            services = [];
        }
        
        const healthyCount = services.filter(service => 
            service && service.status && (service.status === 'healthy' || service.status === 'running')
        ).length;
        
        const unhealthyCount = services.filter(service => 
            service && service.status && (service.status === 'unhealthy' || service.status === 'stopped' || service.status === 'error')
        ).length;
        
        healthyElement.textContent = healthyCount;
        unhealthyElement.textContent = unhealthyCount;
    } catch (error) {
        console.warn('Error updating service health summary:', error);
    }
}

function updateDocumentsTable(documents) {
    try {
        const tbody = document.getElementById('documents-table');
        
        if (!tbody) {
            console.warn('Documents table body element not found');
            return;
        }
        
        // Ensure documents is a valid array
        if (!Array.isArray(documents)) {
            console.warn('Invalid documents array received:', documents);
            documents = [];
        }
        
        if (documents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No documents found</td></tr>';
            return;
        }
        
        // Sort by created_at (newest first)
        documents.sort((a, b) => {
            try {
                return new Date(b.created_at || 0) - new Date(a.created_at || 0);
            } catch (e) {
                return 0;
            }
        });
        
        // Show only the 10 most recent documents
        const recentDocs = documents.slice(0, 10);
        
        const html = recentDocs.map(doc => {
            try {
                const statusClass = getStatusClass(doc.processing_status || 'unknown');
                const statusBadge = getStatusBadge(doc.processing_status || 'unknown');
                const fileSize = formatFileSize(doc.file_size || 0);
                const createdDate = new Date(doc.created_at || Date.now()).toLocaleString();
                
                return `
                    <tr>
                        <td>
                            <div class="fw-medium">${doc.filename || 'Unknown'}</div>
                            <div class="text-muted small">${doc.document_type || 'Unknown'}</div>
                            ${doc.data_source_type ? `<div class="text-muted small"><span class="badge bg-info">${doc.data_source_type}</span></div>` : ''}
                        </td>
                        <td>
                            <span class="source-badge">${doc.source || 'Unknown'}</span>
                            ${doc.original_file_path ? `<div class="text-muted small"><code>${doc.original_file_path.substring(0, 30)}${doc.original_file_path.length > 30 ? '...' : ''}</code></div>` : ''}
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
                            <button class="btn btn-sm btn-outline-primary" onclick="viewDocumentDetails('${doc.id || ''}')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
            } catch (error) {
                console.warn('Error processing document:', error, doc);
                return '';
            }
        }).join('');
        
        tbody.innerHTML = html;
    } catch (error) {
        console.warn('Error updating documents table:', error);
    }
}

function updatePipelineStatus(services) {
    try {
        const container = document.getElementById('pipeline-status');
        
        if (!container) {
            console.warn('Pipeline status container element not found');
            return;
        }
        
        // Ensure services is a valid array
        if (!Array.isArray(services)) {
            console.warn('Invalid services array received for pipeline status:', services);
            services = [];
        }
        
        const pipelineServices = [
            { name: 'text-processor', icon: 'fas fa-file-alt', title: 'Text Extraction' },
            { name: 'metadata-processor', icon: 'fas fa-tags', title: 'Metadata Extraction' },
            { name: 'embedding-processor', icon: 'fas fa-brain', title: 'Embedding Generation' },
            { name: 'entity-processor', icon: 'fas fa-sitemap', title: 'Entity Extraction' },
            { name: 'processing-pipeline', icon: 'fas fa-cogs', title: 'Pipeline Orchestration' }
        ];
        
        const html = pipelineServices.map(service => {
            try {
                const serviceData = services.find(s => s && s.service === service.name);
                const status = serviceData && serviceData.status ? serviceData.status : 'unknown';
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
            } catch (error) {
                console.warn('Error processing pipeline service:', error, service);
                return '';
            }
        }).join('');
        
        container.innerHTML = html;
    } catch (error) {
        console.warn('Error updating pipeline status:', error);
    }
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
                        ${data.document.original_file_path ? `<p><strong>Original Path:</strong> <code class="text-muted">${data.document.original_file_path}</code></p>` : ''}
                        ${data.document.data_source_type ? `<p><strong>Data Source Type:</strong> <span class="badge bg-info">${data.document.data_source_type}</span></p>` : ''}
                        ${data.document.data_source_uri ? `<p><strong>Data Source URI:</strong> <code class="text-muted">${data.document.data_source_uri}</code></p>` : ''}
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

// --- LLM Search Page Logic ---
function showLLMSearchSection() {
    document.querySelectorAll('.container-fluid > .row').forEach(row => {
        if (row.id !== 'llm-search-section') row.style.display = 'none';
    });
    document.getElementById('llm-search-section').style.display = '';
}

function showDashboardSections() {
    document.querySelectorAll('.container-fluid > .row').forEach(row => {
        if (row.id !== 'llm-search-section') row.style.display = '';
    });
    document.getElementById('llm-search-section').style.display = 'none';
}

function handleRouting() {
    if (window.location.pathname === '/llm-search') {
        showLLMSearchSection();
    } else {
        showDashboardSections();
    }
}

window.addEventListener('popstate', handleRouting);
document.addEventListener('DOMContentLoaded', () => {
    handleRouting();
    const llmSearchForm = document.getElementById('llm-search-form');
    if (llmSearchForm) {
        llmSearchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const query = document.getElementById('llm-search-query').value.trim();
            if (!query) return;
            const resultsDiv = document.getElementById('llm-search-results');
            resultsDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Searching...</span></div>';
            try {
                const resp = await fetch('/api/llm-search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });
                if (!resp.ok) throw new Error('Search failed');
                const data = await resp.json();
                renderLLMSearchResults(data, resultsDiv);
            } catch (err) {
                resultsDiv.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
            }
        });
    }
});

function renderLLMSearchResults(data, container) {
    let html = '';
    if (data.llm_response) {
        html += `<div class="alert alert-info"><strong>LLM Answer:</strong><br>${data.llm_response}</div>`;
    }
    if (!data || !data.results || data.results.length === 0) {
        html += '<div class="alert alert-warning">No results found.</div>';
        container.innerHTML = html;
        return;
    }
    html += '<ul class="list-group">';
    data.results.forEach((item, idx) => {
        html += `<li class="list-group-item">
            <strong>Score:</strong> ${item.score?.toFixed(3) ?? '-'}<br>
            <strong>Text:</strong> <pre>${item.text ?? ''}</pre>
            <strong>Metadata:</strong> <code>${JSON.stringify(item.metadata ?? {}, null, 2)}</code>
        </li>`;
    });
    html += '</ul>';
    container.innerHTML = html;
}

// Export functions for global access
window.refreshData = refreshData;
window.viewDocumentDetails = viewDocumentDetails;

// Service status checking function
async function checkServiceStatus() {
    const statusSummary = document.getElementById('service-status-summary');
    if (!statusSummary) return;
    
    statusSummary.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
    
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            throw new Error(`Health API returned ${response.status}`);
        }
        
        const data = await response.json();
        const services = data.services || [];
        
        // Define the services we want to check
        const serviceUrls = {
            'N8N': 'http://localhost:5678',
            'Qdrant UI': 'http://localhost:7070',
            'Kibana': 'http://localhost:5601',
            'Flowise': 'http://localhost:3001'
        };
        
        let healthyCount = 0;
        let totalCount = services.length;
        
        // Count healthy services from the health API
        services.forEach(service => {
            if (service.status === 'healthy') {
                healthyCount++;
            }
        });
        
        // Update the status summary
        if (totalCount === 0) {
            statusSummary.innerHTML = '<span class="text-warning">No services found</span>';
        } else if (healthyCount === totalCount) {
            statusSummary.innerHTML = `<span class="text-success">All ${totalCount} services healthy</span>`;
        } else {
            statusSummary.innerHTML = `<span class="text-warning">${healthyCount}/${totalCount} services healthy</span>`;
        }
        
    } catch (error) {
        console.error('Error checking service status:', error);
        statusSummary.innerHTML = '<span class="text-danger">Error checking status</span>';
    }
}

// Check service status on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initial service status check
    setTimeout(checkServiceStatus, 1000);
    
    // Check service status every 60 seconds
    setInterval(checkServiceStatus, 60000);
});

// Export the function for global access
window.checkServiceStatus = checkServiceStatus; 