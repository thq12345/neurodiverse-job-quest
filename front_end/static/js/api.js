/**
 * API Service for Neurodiverse Job Quest
 * Handles communication with the Lambda functions via API Gateway
 */

class ApiService {
    constructor() {
        // Replace with your API Gateway URL after deployment
        this.apiBaseUrl = 'https://your-api-id.execute-api.your-region.amazonaws.com/prod';
        
        // For local testing, you can use this environment variable
        if (window.API_GATEWAY_URL) {
            this.apiBaseUrl = window.API_GATEWAY_URL;
        }
    }

    /**
     * Set the API base URL
     * @param {string} url - The API Gateway URL
     */
    setApiBaseUrl(url) {
        this.apiBaseUrl = url;
    }

    /**
     * Handle API errors
     * @param {Response} response - The fetch response object
     * @returns {Promise} - A promise that resolves to the response data or rejects with an error
     */
    async handleResponse(response) {
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const error = new Error(errorData.detail || response.statusText || 'API Error');
            error.status = response.status;
            error.data = errorData;
            throw error;
        }
        return response.json();
    }

    /**
     * Fetch the questionnaire questions
     * @returns {Promise<Object>} - A promise that resolves to the questionnaire data
     */
    async getQuestionnaire() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/questionnaire`);
            return this.handleResponse(response);
        } catch (error) {
            console.error('Error fetching questionnaire:', error);
            throw error;
        }
    }

    /**
     * Submit questionnaire answers
     * @param {Object} answers - The questionnaire answers
     * @returns {Promise<Object>} - A promise that resolves to the submission response
     */
    async submitQuestionnaire(answers) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/submit_questionnaire`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(answers),
            });
            return this.handleResponse(response);
        } catch (error) {
            console.error('Error submitting questionnaire:', error);
            throw error;
        }
    }

    /**
     * Get analysis results by assessment ID
     * @param {string} assessmentId - The assessment ID
     * @returns {Promise<Object>} - A promise that resolves to the analysis results
     */
    async getResults(assessmentId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/results/${assessmentId}`);
            return this.handleResponse(response);
        } catch (error) {
            console.error('Error fetching results:', error);
            throw error;
        }
    }

    /**
     * Check health status of the API
     * @returns {Promise<Object>} - A promise that resolves to the health status
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            return this.handleResponse(response);
        } catch (error) {
            console.error('Error checking API health:', error);
            throw error;
        }
    }
}

// Create a singleton instance of the API service
const apiService = new ApiService();

// If running locally with a custom API URL, you can set it here:
// window.API_GATEWAY_URL = 'http://localhost:3000'; 