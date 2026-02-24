// AI Study System - Frontend JavaScript

class StudySystemApp {
    constructor() {
        this.apiBase = window.location.origin + '/api';
        this.currentTab = 'dashboard';
        this.currentUser = null;
        this.init();
    }

    async checkAuth() {
        const token = localStorage.getItem('authToken');
        if (!token) {
            return false;
        }

        try {
            const response = await fetch(`${this.apiBase}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.currentUser = await response.json();
                this.updateUserDisplay();
                return true;
            }
        } catch (error) {
            console.error('Auth check failed:', error);
        }

        // Clear invalid token
        localStorage.removeItem('authToken');
        return false;
    }

    updateUserDisplay() {
        if (this.currentUser) {
            document.getElementById('userName').textContent = this.currentUser.full_name || this.currentUser.username;
        }
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // User menu
        document.getElementById('userMenuToggle').addEventListener('click', () => {
            this.toggleUserMenu();
        });

        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });

        document.getElementById('groupsBtn').addEventListener('click', () => {
            this.switchTab('groups');
            this.closeUserMenu();
        });

        // Close user menu when clicking outside
        document.addEventListener('click', (e) => {
            const userMenu = document.getElementById('userDropdown');
            const userInfo = document.getElementById('userInfo');
            if (!userInfo.contains(e.target)) {
                userMenu.style.display = 'none';
            }
        });

        // Add Material
        document.getElementById('add-material-btn').addEventListener('click', () => {
            this.showModal('add-material-modal');
        });

        document.getElementById('add-material-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addMaterial();
        });

        // Add Topic
        document.getElementById('add-topic-btn').addEventListener('click', () => {
            this.showModal('add-topic-modal');
        });

        document.getElementById('add-topic-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addTopic();
        });

        // Groups functionality
        document.getElementById('create-group-btn').addEventListener('click', () => {
            this.showModal('create-group-modal');
        });

        document.getElementById('create-group-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createGroup();
        });

        // Group tabs
        document.querySelectorAll('.group-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.groupTab;
                this.switchGroupTab(tabName);
            });
        });

        document.getElementById('search-groups-btn').addEventListener('click', () => {
            this.searchPublicGroups();
        });

        document.getElementById('group-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchPublicGroups();
            }
        });

        // Search
        document.getElementById('search-btn').addEventListener('click', () => {
            this.performSearch();
        });

        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Generate Content
        document.getElementById('generate-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateContent();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideAllModals();
            });
        });

        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideAllModals();
                }
            });
        });
    }

    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        switch (tabName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'materials':
                this.loadMaterials();
                break;
            case 'topics':
                this.loadTopics();
                break;
            case 'groups':
                this.loadGroups();
                break;
        }
    }

    async loadDashboard() {
        try {
            const response = await fetch(`${this.apiBase}/api/stats`);
            const stats = await response.json();

            // Update stats
            document.getElementById('materials-count').textContent = stats.total_documents;
            document.getElementById('pending-reviews').textContent = stats.pending_reviews;
            document.getElementById('topics-count').textContent = stats.total_topics;
            document.getElementById('study-streak').textContent = '0'; // TODO: implement streak tracking

            // Update header stats
            document.getElementById('doc-count').textContent = stats.total_documents;
            document.getElementById('topic-count').textContent = stats.total_topics;

        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.showNotification('Failed to load dashboard data', 'error');
        }
    }

    async loadMaterials() {
        try {
            const response = await fetch(`${this.apiBase}/api/materials`);
            const data = await response.json();

            const container = document.getElementById('materials-list');

            if (data.materials && data.materials.length > 0) {
                container.innerHTML = data.materials.map(material => `
                    <div class="material-card">
                        <h3>${this.escapeHtml(material.title)}</h3>
                        <div class="content-preview">${this.escapeHtml(material.content_preview)}</div>
                        <div class="material-tags">
                            ${material.tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="empty-state">No study materials yet. Add your first material!</p>';
            }

        } catch (error) {
            console.error('Failed to load materials:', error);
            this.showNotification('Failed to load materials', 'error');
        }
    }

    async loadTopics() {
        try {
            const response = await fetch(`${this.apiBase}/api/topics`);
            const data = await response.json();

            const container = document.getElementById('topics-list');

            if (data.topics && data.topics.length > 0) {
                container.innerHTML = data.topics.map(topic => `
                    <div class="topic-card">
                        <h3>${this.escapeHtml(topic.name)}</h3>
                        <p>${this.escapeHtml(topic.description || 'No description')}</p>
                        <div class="topic-stats">
                            <span>${topic.document_count} documents</span>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="empty-state">No topics created yet. Organize your materials!</p>';
            }

        } catch (error) {
            console.error('Failed to load topics:', error);
            this.showNotification('Failed to load topics', 'error');
        }
    }

    async addMaterial() {
        const form = document.getElementById('add-material-form');
        const formData = new FormData(form);

        const materialData = {
            title: formData.get('material-title'),
            content: formData.get('material-content'),
            source_type: formData.get('material-type'),
            tags: formData.get('material-tags').split(',').map(tag => tag.trim()).filter(tag => tag)
        };

        try {
            const response = await fetch(`${this.apiBase}/api/materials`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(materialData)
            });

            if (response.ok) {
                this.hideAllModals();
                form.reset();
                this.showNotification('Material added successfully!', 'success');
                this.loadDashboard();
                if (this.currentTab === 'materials') {
                    this.loadMaterials();
                }
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to add material');
            }

        } catch (error) {
            console.error('Failed to add material:', error);
            this.showNotification(error.message, 'error');
        }
    }

    async addTopic() {
        const form = document.getElementById('add-topic-form');
        const formData = new FormData(form);

        const topicData = {
            name: formData.get('topic-name'),
            description: formData.get('topic-description')
        };

        try {
            const response = await fetch(`${this.apiBase}/api/topics`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(topicData)
            });

            if (response.ok) {
                this.hideAllModals();
                form.reset();
                this.showNotification('Topic added successfully!', 'success');
                this.loadDashboard();
                if (this.currentTab === 'topics') {
                    this.loadTopics();
                }
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to add topic');
            }

        } catch (error) {
            console.error('Failed to add topic:', error);
            this.showNotification(error.message, 'error');
        }
    }

    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        const searchType = document.getElementById('search-type').value;

        if (!query) {
            this.showNotification('Please enter a search query', 'error');
            return;
        }

        try {
            let response;
            if (searchType === 'semantic') {
                response = await fetch(`${this.apiBase}/api/search`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query, limit: 10 })
                });
            } else {
                response = await fetch(`${this.apiBase}/api/search/text?query=${encodeURIComponent(query)}&limit=10`);
            }

            const data = await response.json();

            const results = searchType === 'semantic' ? data : data.results;
            this.displaySearchResults(results, query);

        } catch (error) {
            console.error('Search failed:', error);
            this.showNotification('Search failed', 'error');
        }
    }

    displaySearchResults(results, query) {
        const container = document.getElementById('search-results');

        if (results && results.length > 0) {
            container.innerHTML = results.map(result => `
                <div class="search-result">
                    <h3>${this.escapeHtml(result.title)}</h3>
                    ${result.similarity_score ? `<div class="similarity-score">Similarity: ${(result.similarity_score * 100).toFixed(1)}%</div>` : ''}
                    <div class="content-preview">${this.escapeHtml(result.content_preview || result.content_preview)}</div>
                    ${result.tags ? `<div class="material-tags">${result.tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}</div>` : ''}
                </div>
            `).join('');
        } else {
            container.innerHTML = `<p class="empty-state">No results found for "${query}"</p>`;
        }
    }

    async generateContent() {
        const form = document.getElementById('generate-form');
        const formData = new FormData(form);

        const generateData = {
            topic: formData.get('generate-topic'),
            content_type: formData.get('content-type'),
            difficulty: formData.get('difficulty')
        };

        try {
            const response = await fetch(`${this.apiBase}/api/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(generateData)
            });

            if (response.ok) {
                const result = await response.json();
                this.displayGeneratedContent(result);
                this.showNotification('Content generated successfully!', 'success');
            } else if (response.status === 503) {
                throw new Error('AI content generation not available (OpenAI API key required)');
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to generate content');
            }

        } catch (error) {
            console.error('Content generation failed:', error);
            this.showNotification(error.message, 'error');
        }
    }

    displayGeneratedContent(result) {
        const container = document.getElementById('generated-content');
        const output = document.getElementById('content-output');

        output.textContent = result.content;
        container.classList.remove('hidden');
    }

    showModal(modalId) {
        document.getElementById(modalId).classList.remove('hidden');
    }

    hideAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
    }

    showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');
        const messageEl = document.getElementById('notification-message');

        messageEl.textContent = message;
        notification.className = `notification ${type}`;

        // Remove existing classes and add show class
        notification.classList.remove('hidden');
        setTimeout(() => notification.classList.add('show'), 10);

        // Auto-hide after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.classList.add('hidden'), 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // User menu methods
    toggleUserMenu() {
        const dropdown = document.getElementById('userDropdown');
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    }

    closeUserMenu() {
        document.getElementById('userDropdown').style.display = 'none';
    }

    async logout() {
        try {
            const token = localStorage.getItem('authToken');
            if (token) {
                await fetch(`${this.apiBase}/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        }

        localStorage.removeItem('authToken');
        window.location.href = '/auth.html';
    }

    // Groups methods
    async loadGroups() {
        await Promise.all([
            this.loadMyGroups(),
            this.loadPublicGroups()
        ]);
    }

    async loadMyGroups() {
        try {
            const response = await this.apiRequest('/groups');
            const groups = response;

            const container = document.getElementById('my-groups-list');

            if (groups && groups.length > 0) {
                container.innerHTML = groups.map(group => `
                    <div class="group-card">
                        <h4>${this.escapeHtml(group.name)}</h4>
                        <p>${this.escapeHtml(group.description || 'No description')}</p>
                        <div class="group-meta">
                            <span>${group.member_count} members</span>
                            <span>${group.is_public ? 'Public' : 'Private'}</span>
                        </div>
                        <div class="group-actions">
                            <button class="btn-view" onclick="window.studySystemApp.viewGroup(${group.group_id})">
                                View Details
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="empty-state">You haven\'t joined any groups yet. Create one or join a public group!</p>';
            }
        } catch (error) {
            console.error('Failed to load groups:', error);
            this.showNotification('Failed to load groups', 'error');
        }
    }

    async loadPublicGroups(query = '') {
        try {
            const url = query ? `/groups?include_public=true&search=${encodeURIComponent(query)}` : '/groups?include_public=true';
            const response = await this.apiRequest(url);
            const groups = response.filter(g => g.is_public);

            const container = document.getElementById('public-groups-list');

            if (groups && groups.length > 0) {
                container.innerHTML = groups.map(group => `
                    <div class="group-card">
                        <h4>${this.escapeHtml(group.name)}</h4>
                        <p>${this.escapeHtml(group.description || 'No description')}</p>
                        <div class="group-meta">
                            <span>${group.member_count} members</span>
                            <span>Public</span>
                        </div>
                        <div class="group-actions">
                            <button class="btn-join" onclick="window.studySystemApp.joinGroup(${group.group_id})">
                                Join Group
                            </button>
                            <button class="btn-view" onclick="window.studySystemApp.viewGroup(${group.group_id})">
                                View Details
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="empty-state">No public groups found.</p>';
            }
        } catch (error) {
            console.error('Failed to load public groups:', error);
            this.showNotification('Failed to load public groups', 'error');
        }
    }

    switchGroupTab(tabName) {
        document.querySelectorAll('.group-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-group-tab="${tabName}"]`).classList.add('active');

        document.querySelectorAll('.group-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-section`).classList.add('active');
    }

    async createGroup() {
        const name = document.getElementById('group-name').value;
        const description = document.getElementById('group-description').value;
        const isPublic = document.getElementById('group-public').checked;

        try {
            await this.apiRequest('/groups', {
                method: 'POST',
                body: JSON.stringify({
                    name,
                    description: description || null,
                    is_public: isPublic
                })
            });

            this.hideAllModals();
            this.showNotification('Group created successfully!', 'success');
            this.loadGroups();
        } catch (error) {
            this.showNotification(error.message || 'Failed to create group', 'error');
        }
    }

    async joinGroup(groupId) {
        try {
            await this.apiRequest(`/groups/${groupId}/join`, {
                method: 'POST'
            });

            this.showNotification('Joined group successfully!', 'success');
            this.loadGroups();
        } catch (error) {
            this.showNotification(error.message || 'Failed to join group', 'error');
        }
    }

    async viewGroup(groupId) {
        try {
            const group = await this.apiRequest(`/groups/${groupId}`);
            const members = await this.apiRequest(`/groups/${groupId}/members`);
            const materials = await this.apiRequest(`/groups/${groupId}/materials`);

            // Update modal content
            document.getElementById('group-details-title').textContent = group.name;
            document.getElementById('group-name-display').textContent = group.name;
            document.getElementById('group-description-display').textContent = group.description || 'No description';
            document.getElementById('group-member-count').textContent = `${group.member_count} members`;
            document.getElementById('group-shared-count').textContent = `${materials.length} shared materials`;

            // Members list
            const membersContainer = document.getElementById('group-members-list');
            if (members && members.length > 0) {
                membersContainer.innerHTML = members.map(member => `
                    <div class="member-item">
                        <div class="member-info">
                            <h5>${this.escapeHtml(member.full_name || member.username)}</h5>
                            <p>${this.escapeHtml(member.email)}</p>
                        </div>
                        <span class="member-role">${member.role}</span>
                    </div>
                `).join('');
            } else {
                membersContainer.innerHTML = '<p class="empty-state">No members found.</p>';
            }

            // Materials list
            const materialsContainer = document.getElementById('group-materials-list');
            if (materials && materials.length > 0) {
                materialsContainer.innerHTML = materials.map(material => `
                    <div class="material-item">
                        <div class="material-info">
                            <h5>${this.escapeHtml(material.material_title)}</h5>
                            <p>Shared by ${this.escapeHtml(material.shared_by_username)} • ${material.access_level} access</p>
                        </div>
                        <div class="material-actions">
                            <button class="btn-secondary" onclick="window.studySystemApp.viewMaterial(${material.material_id})">
                                View
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                materialsContainer.innerHTML = '<p class="empty-state">No materials shared yet.</p>';
            }

            this.showModal('group-details-modal');
        } catch (error) {
            this.showNotification(error.message || 'Failed to load group details', 'error');
        }
    }

    searchPublicGroups() {
        const query = document.getElementById('group-search').value;
        this.loadPublicGroups(query);
    }

    // Helper method for authenticated API requests
    async apiRequest(endpoint, options = {}) {
        const token = localStorage.getItem('authToken');
        if (!token) {
            throw new Error('Not authenticated');
        }

        const defaultHeaders = {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };

        const response = await fetch(`${this.apiBase}${endpoint}`, {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.studySystemApp = new StudySystemApp();
});