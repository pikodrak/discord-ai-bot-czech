/**
 * Discord AI Bot Admin Panel
 * Main JavaScript application for frontend interactions and API calls
 */

// API Configuration
const API_BASE_URL = window.location.origin;
const API_ENDPOINTS = {
    login: '/api/auth/login',
    config: '/api/config/',
    configReload: '/api/config/reload',
    configValidate: '/api/config/validate',
    botStatus: '/api/bot/status',
    botControl: '/api/bot/control',
    botStats: '/api/bot/stats',
    health: '/health'
};

// Application State
const AppState = {
    token: null,
    username: null,
    refreshInterval: null
};

// Utility Functions
const Utils = {
    /**
     * Show a screen and hide others
     */
    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    },

    /**
     * Show/hide element
     */
    toggleElement(elementId, show) {
        const element = document.getElementById(elementId);
        if (element) {
            if (show) {
                element.classList.remove('hidden');
            } else {
                element.classList.add('hidden');
            }
        }
    },

    /**
     * Set element text
     */
    setText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    },

    /**
     * Format uptime from seconds
     */
    formatUptime(seconds) {
        if (!seconds) return '-';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    },

    /**
     * Get auth headers
     */
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${AppState.token}`,
            'Content-Type': 'application/json'
        };
    }
};

// API Service
const API = {
    /**
     * Make API request
     */
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(API_BASE_URL + endpoint, options);

            if (response.status === 401) {
                Auth.logout();
                throw new Error('Session expired. Please login again.');
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    /**
     * Login
     */
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        return this.request(API_ENDPOINTS.login, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });
    },

    /**
     * Get configuration
     */
    async getConfig() {
        return this.request(API_ENDPOINTS.config, {
            headers: Utils.getAuthHeaders()
        });
    },

    /**
     * Update configuration
     */
    async updateConfig(configData) {
        return this.request(API_ENDPOINTS.config, {
            method: 'PUT',
            headers: Utils.getAuthHeaders(),
            body: JSON.stringify(configData)
        });
    },

    /**
     * Reload configuration
     */
    async reloadConfig() {
        return this.request(API_ENDPOINTS.configReload, {
            method: 'POST',
            headers: Utils.getAuthHeaders()
        });
    },

    /**
     * Validate configuration
     */
    async validateConfig() {
        return this.request(API_ENDPOINTS.configValidate, {
            headers: Utils.getAuthHeaders()
        });
    },

    /**
     * Get bot status
     */
    async getBotStatus() {
        return this.request(API_ENDPOINTS.botStatus, {
            headers: Utils.getAuthHeaders()
        });
    },

    /**
     * Control bot
     */
    async controlBot(action) {
        return this.request(API_ENDPOINTS.botControl, {
            method: 'POST',
            headers: Utils.getAuthHeaders(),
            body: JSON.stringify({ action })
        });
    },

    /**
     * Get bot stats
     */
    async getBotStats() {
        return this.request(API_ENDPOINTS.botStats, {
            headers: Utils.getAuthHeaders()
        });
    },

    /**
     * Get health status
     */
    async getHealth() {
        return this.request(API_ENDPOINTS.health);
    }
};

// Authentication Module
const Auth = {
    /**
     * Initialize auth state from localStorage
     */
    init() {
        const token = localStorage.getItem('auth_token');
        const username = localStorage.getItem('username');

        if (token && username) {
            AppState.token = token;
            AppState.username = username;
            this.showDashboard();
        } else {
            Utils.showScreen('loginScreen');
        }
    },

    /**
     * Handle login
     */
    async login(username, password) {
        try {
            const response = await API.login(username, password);

            // Store auth data
            AppState.token = response.access_token;
            AppState.username = username;
            localStorage.setItem('auth_token', response.access_token);
            localStorage.setItem('username', username);

            // Show dashboard
            this.showDashboard();
        } catch (error) {
            throw error;
        }
    },

    /**
     * Logout
     */
    logout() {
        AppState.token = null;
        AppState.username = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('username');

        // Clear refresh interval
        if (AppState.refreshInterval) {
            clearInterval(AppState.refreshInterval);
            AppState.refreshInterval = null;
        }

        Utils.showScreen('loginScreen');
    },

    /**
     * Show dashboard after successful login
     */
    showDashboard() {
        Utils.showScreen('dashboardScreen');
        Utils.setText('userInfo', `Logged in as: ${AppState.username}`);

        // Load dashboard data
        Dashboard.init();

        // Start auto-refresh
        AppState.refreshInterval = setInterval(() => {
            Dashboard.refreshStatus();
        }, 10000); // Refresh every 10 seconds
    }
};

// Dashboard Module
const Dashboard = {
    /**
     * Initialize dashboard
     */
    async init() {
        await Promise.all([
            this.loadConfig(),
            this.refreshStatus(),
            this.loadHealth()
        ]);
    },

    /**
     * Load configuration
     */
    async loadConfig() {
        try {
            Utils.toggleElement('configLoading', true);
            Utils.toggleElement('configError', false);
            Utils.toggleElement('configForm', false);

            const config = await API.getConfig();

            // Populate form
            document.getElementById('botLanguage').value = config.bot_settings?.language || 'cs';
            document.getElementById('botPersonality').value = config.bot_settings?.personality || 'friendly';
            document.getElementById('responseThreshold').value = config.bot_settings?.response_threshold || 0.6;
            document.getElementById('maxHistory').value = config.bot_settings?.max_history || 50;
            document.getElementById('channelIds').value = config.channels?.join(',') || '';

            // Update info
            Utils.setText('aiProvider', config.ai_provider || 'None');
            Utils.setText('discordConfigured', config.discord_configured ? 'Yes' : 'No');

            Utils.toggleElement('configLoading', false);
            Utils.toggleElement('configForm', true);
        } catch (error) {
            Utils.toggleElement('configLoading', false);
            const errorEl = document.getElementById('configError');
            errorEl.textContent = `Failed to load configuration: ${error.message}`;
            Utils.toggleElement('configError', true);
        }
    },

    /**
     * Update configuration
     */
    async updateConfig(formData) {
        try {
            Utils.toggleElement('configUpdateError', false);
            Utils.toggleElement('configUpdateSuccess', false);

            const configData = {
                bot_language: formData.get('bot_language'),
                bot_personality: formData.get('bot_personality'),
                bot_response_threshold: parseFloat(formData.get('bot_response_threshold')),
                bot_max_history: parseInt(formData.get('bot_max_history')),
                discord_channel_ids: formData.get('discord_channel_ids')
            };

            const response = await API.updateConfig(configData);

            const successEl = document.getElementById('configUpdateSuccess');
            successEl.textContent = response.message || 'Configuration updated successfully';
            Utils.toggleElement('configUpdateSuccess', true);

            // Reload configuration
            setTimeout(() => this.loadConfig(), 1000);
        } catch (error) {
            const errorEl = document.getElementById('configUpdateError');
            errorEl.textContent = `Failed to update configuration: ${error.message}`;
            Utils.toggleElement('configUpdateError', true);
        }
    },

    /**
     * Refresh bot status and stats
     */
    async refreshStatus() {
        try {
            const [status, stats] = await Promise.all([
                API.getBotStatus(),
                API.getBotStats()
            ]);

            // Update status
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');

            if (status.running && status.connected) {
                statusDot.className = 'status-dot online';
                statusText.textContent = 'Running';
            } else if (status.running) {
                statusDot.className = 'status-dot';
                statusText.textContent = 'Starting...';
            } else {
                statusDot.className = 'status-dot offline';
                statusText.textContent = 'Stopped';
            }

            Utils.setText('connectedStatus', status.connected ? 'Yes' : 'No');
            Utils.setText('guildName', status.guild_name || '-');
            Utils.setText('uptime', Utils.formatUptime(status.uptime_seconds));

            // Update stats
            Utils.setText('messagesProcessed', stats.total_messages_processed || 0);
            Utils.setText('responsesSent', stats.total_responses_sent || 0);
            Utils.setText('avgResponseTime', `${stats.average_response_time_ms || 0}ms`);
        } catch (error) {
            console.error('Failed to refresh status:', error);
        }
    },

    /**
     * Control bot
     */
    async controlBot(action) {
        try {
            const response = await API.controlBot(action);
            alert(response.message || `Bot ${action} command executed`);

            // Refresh status after action
            setTimeout(() => this.refreshStatus(), 1000);
        } catch (error) {
            alert(`Failed to ${action} bot: ${error.message}`);
        }
    },

    /**
     * Load health information
     */
    async loadHealth() {
        try {
            const health = await API.getHealth();

            Utils.setText('healthStatus', health.status);
            document.getElementById('healthStatus').className =
                'badge ' + (health.status === 'healthy' ? 'success' : 'danger');

            Utils.setText('apiVersion', health.api_version || '-');

            const discordBadge = document.getElementById('healthDiscord');
            discordBadge.textContent = health.discord_configured ? 'Yes' : 'No';
            discordBadge.className = 'badge ' + (health.discord_configured ? 'success' : 'danger');

            const aiBadge = document.getElementById('healthAI');
            aiBadge.textContent = health.ai_configured ? 'Yes' : 'No';
            aiBadge.className = 'badge ' + (health.ai_configured ? 'success' : 'danger');
        } catch (error) {
            console.error('Failed to load health:', error);
        }
    }
};

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize authentication
    Auth.init();

    // Login form
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('loginError');

        Utils.toggleElement('loginError', false);

        try {
            await Auth.login(username, password);
        } catch (error) {
            errorEl.textContent = error.message || 'Login failed. Please check your credentials.';
            Utils.toggleElement('loginError', true);
        }
    });

    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', () => {
        Auth.logout();
    });

    // Bot control buttons
    document.getElementById('startBtn').addEventListener('click', () => {
        Dashboard.controlBot('start');
    });

    document.getElementById('restartBtn').addEventListener('click', () => {
        Dashboard.controlBot('restart');
    });

    document.getElementById('stopBtn').addEventListener('click', () => {
        Dashboard.controlBot('stop');
    });

    document.getElementById('refreshBtn').addEventListener('click', () => {
        Dashboard.refreshStatus();
    });

    // Configuration form
    document.getElementById('configForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        await Dashboard.updateConfig(formData);
    });

    document.getElementById('reloadConfigBtn').addEventListener('click', async () => {
        try {
            const response = await API.reloadConfig();
            alert(response.message || 'Configuration reloaded successfully');
            await Dashboard.loadConfig();
        } catch (error) {
            alert(`Failed to reload configuration: ${error.message}`);
        }
    });

    document.getElementById('validateConfigBtn').addEventListener('click', async () => {
        try {
            const response = await API.validateConfig();
            alert('Configuration is valid:\n' + JSON.stringify(response, null, 2));
        } catch (error) {
            alert(`Configuration validation failed: ${error.message}`);
        }
    });
});
