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
        
        // This allows local testing without setting up environment variables
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.log('Running in local development mode');
            // Use API Gateway stage URL if available, otherwise fall back to mock data
            if (!window.API_GATEWAY_URL) {
                this.useMockData = true;
                console.log('Using mock data for local development');
            }
        }
    }

    /**
     * Set the API base URL
     * @param {string} url - The API Gateway URL
     */
    setApiBaseUrl(url) {
        this.apiBaseUrl = url;
        this.useMockData = false;
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
            // For local development without API
            if (this.useMockData) {
                return this.getMockQuestions();
            }
            
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
            // For local development without API
            if (this.useMockData) {
                return this.getMockResults(answers);
            }
            
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
            // For local development without API
            if (this.useMockData) {
                return this.getMockResults();
            }
            
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
            // For local development without API
            if (this.useMockData) {
                return { status: 'healthy', mode: 'mock' };
            }
            
            const response = await fetch(`${this.apiBaseUrl}/health`);
            return this.handleResponse(response);
        } catch (error) {
            console.error('Error checking API health:', error);
            throw error;
        }
    }
    
    /**
     * Get mock questions for local development
     * @returns {Promise<Object>} - A promise that resolves to mock questionnaire data
     */
    async getMockQuestions() {
        return {
            questions: [
                {
                    id: 1,
                    text: "How do you prefer to structure your workday?",
                    options: [
                        ["A", "I thrive with a structured schedule"],
                        ["B", "I prefer flexibility in my work hours"]
                    ]
                },
                {
                    id: 2,
                    text: "What type of workspace do you find most comfortable?",
                    options: [
                        ["A", "Quiet and private spaces"],
                        ["B", "Collaborative and open spaces"]
                    ]
                },
                {
                    id: 3,
                    text: "How comfortable are you with frequent interactions with colleagues?",
                    options: [
                        ["A", "Prefer minimal interactions"],
                        ["B", "Comfortable with regular teamwork"],
                        ["C", "Enjoy leading or coordinating teams"]
                    ]
                },
                {
                    id: 4,
                    text: "Do you prefer tasks that are:",
                    options: [
                        ["A", "Highly detailed and focused"],
                        ["B", "Creative and innovative"],
                        ["C", "A balance of both"]
                    ]
                },
                {
                    id: 5,
                    text: "Is there anything else we should know about you? (Optional)",
                    type: "free_response",
                    optional: true
                }
            ]
        };
    }
    
    /**
     * Get mock results for local development
     * @returns {Promise<Object>} - A promise that resolves to mock results data
     */
    async getMockResults(answers = {}) {
        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Mock JSON profile structure
        const mockProfile = {
            work_style: {
                description: "You thrive with a structured schedule",
                explanation: "You prefer clear guidelines and consistent routines."
            },
            environment: {
                description: "You prefer quiet and private spaces",
                explanation: "You work best in environments with minimal distractions."
            },
            interaction_level: {
                description: "You prefer minimal interactions",
                explanation: "You tend to focus better when working independently."
            },
            task_preference: {
                description: "You prefer highly detailed and focused tasks",
                explanation: "You excel at work requiring precision and careful attention."
            },
            additional_insights: {
                description: "No additional insights",
                explanation: ""
            }
        };
        
        return {
            assessment_id: "mock-" + Math.random().toString(36).substring(2, 10),
            profile: mockProfile,
            recommendations: [
                {
                    title: "Software Developer",
                    match_score: 92,
                    description: "Write, modify, and test code and scripts that allow computer applications to run.",
                    key_traits: ["Problem-solving", "Attention to detail", "Logical thinking"],
                    environment: "Typically quiet offices or remote work opportunities with flexible hours"
                },
                {
                    title: "Data Analyst",
                    match_score: 89,
                    description: "Analyze data to help companies make better business decisions.",
                    key_traits: ["Pattern recognition", "Statistical knowledge", "Detail-oriented"],
                    environment: "Structured environment with clear deadlines and expectations"
                },
                {
                    title: "Quality Assurance Specialist",
                    match_score: 85,
                    description: "Test software applications to ensure they work as expected.",
                    key_traits: ["Methodical approach", "Attention to detail", "Problem identification"],
                    environment: "Process-oriented workplaces with predictable workflows"
                }
            ]
        };
    }
}

// Create a singleton instance of the API service
const apiService = new ApiService();

// If running locally with a custom API URL, you can set it here:
// window.API_GATEWAY_URL = 'http://localhost:3000'; 