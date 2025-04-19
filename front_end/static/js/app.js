/**
 * Main JavaScript for Neurodiverse Job Quest
 * Handles UI interaction and application flow
 */

// DOM Elements
const welcomePage = document.getElementById('welcome-page');
const questionnairePage = document.getElementById('questionnaire-page');
const resultsPage = document.getElementById('results-page');
const startBtn = document.getElementById('start-btn');
const questionnaireForm = document.getElementById('questionnaire-form');
const questionsContainer = document.getElementById('questions-container');
const resultsLoading = document.getElementById('results-loading');
const resultsContent = document.getElementById('results-content');
const strengthsList = document.getElementById('strengths-list');
const workStyle = document.getElementById('work-style');
const environment = document.getElementById('environment');
const recommendationsContainer = document.getElementById('recommendations-container');

// State
let currentPage = welcomePage;
let questions = [];
let assessmentId = null;

// Event Listeners
document.addEventListener('DOMContentLoaded', init);
startBtn.addEventListener('click', startQuestionnaire);
questionnaireForm.addEventListener('submit', submitQuestionnaire);

/**
 * Initialize the application
 */
async function init() {
    // Check for assessment ID in URL (for sharing results)
    const urlParams = new URLSearchParams(window.location.search);
    const urlAssessmentId = urlParams.get('assessment_id');
    
    if (urlAssessmentId) {
        assessmentId = urlAssessmentId;
        navigateTo(resultsPage);
        await loadResults(assessmentId);
    }
    
    // Check API health
    try {
        await apiService.checkHealth();
        console.log('API is healthy');
    } catch (error) {
        console.error('API health check failed:', error);
    }
}

/**
 * Start the questionnaire
 */
async function startQuestionnaire() {
    navigateTo(questionnairePage);
    
    try {
        // Fetch questions from API
        const response = await apiService.getQuestionnaire();
        questions = response.questions;
        
        // Render questions
        renderQuestions(questions);
    } catch (error) {
        console.error('Error loading questionnaire:', error);
        questionsContainer.innerHTML = `
            <div class="alert alert-danger" role="alert">
                Error loading questions. Please try again later.
            </div>
        `;
    }
}

/**
 * Render the questionnaire questions
 * @param {Array} questions - The questionnaire questions
 */
function renderQuestions(questions) {
    // Clear loading state
    questionsContainer.innerHTML = '';
    
    // Render each question
    questions.forEach((question, index) => {
        const questionElement = document.createElement('div');
        questionElement.className = 'question';
        questionElement.id = `question-${question.id}`;
        
        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.textContent = `${index + 1}. ${question.text}`;
        
        questionElement.appendChild(questionText);
        
        if (question.type === 'free_response') {
            // Free response (text area)
            const textAreaContainer = document.createElement('div');
            textAreaContainer.className = 'mb-3';
            
            const textArea = document.createElement('textarea');
            textArea.className = 'form-control';
            textArea.name = `q${question.id}`;
            textArea.rows = 4;
            textArea.placeholder = 'Enter your response (optional)';
            
            textAreaContainer.appendChild(textArea);
            questionElement.appendChild(textAreaContainer);
        } else {
            // Multiple choice question
            const optionsContainer = document.createElement('div');
            optionsContainer.className = 'options-container';
            
            question.options.forEach(([value, text]) => {
                const option = document.createElement('div');
                option.className = 'option';
                option.dataset.value = value;
                
                const input = document.createElement('input');
                input.type = 'radio';
                input.className = 'option-radio';
                input.name = `q${question.id}`;
                input.value = value;
                input.id = `q${question.id}-${value}`;
                input.required = !question.optional;
                
                const label = document.createElement('label');
                label.htmlFor = `q${question.id}-${value}`;
                label.textContent = text;
                
                option.appendChild(input);
                option.appendChild(label);
                
                // Make the entire option clickable
                option.addEventListener('click', () => {
                    input.checked = true;
                    
                    // Update selected state for styling
                    optionsContainer.querySelectorAll('.option').forEach(opt => {
                        opt.classList.remove('selected');
                    });
                    option.classList.add('selected');
                });
                
                optionsContainer.appendChild(option);
            });
            
            questionElement.appendChild(optionsContainer);
        }
        
        questionsContainer.appendChild(questionElement);
    });
}

/**
 * Submit the questionnaire
 * @param {Event} event - The form submission event
 */
async function submitQuestionnaire(event) {
    event.preventDefault();
    
    // Get form data
    const formData = new FormData(questionnaireForm);
    const answers = {};
    
    for (const [name, value] of formData.entries()) {
        answers[name] = value;
    }
    
    try {
        // Submit answers to API
        const response = await apiService.submitQuestionnaire(answers);
        assessmentId = response.assessment_id;
        
        // Navigate to results page
        navigateTo(resultsPage);
        
        // Load results
        await loadResults(assessmentId);
        
        // Update URL for sharing
        window.history.pushState({}, '', `?assessment_id=${assessmentId}`);
    } catch (error) {
        console.error('Error submitting questionnaire:', error);
        questionsContainer.innerHTML += `
            <div class="alert alert-danger mt-3" role="alert">
                Error submitting your answers. Please try again.
            </div>
        `;
    }
}

/**
 * Load results from the API
 * @param {string} assessmentId - The assessment ID
 */
async function loadResults(assessmentId) {
    // Show loading state
    resultsLoading.style.display = 'block';
    resultsContent.style.display = 'none';
    
    try {
        // Fetch results from API
        const results = await apiService.getResults(assessmentId);
        
        // Render profile
        renderProfile(results.profile);
        
        // Render recommendations
        renderRecommendations(results.recommendations);
        
        // Hide loading state, show results
        resultsLoading.style.display = 'none';
        resultsContent.style.display = 'block';
    } catch (error) {
        console.error('Error loading results:', error);
        resultsLoading.style.display = 'none';
        resultsPage.querySelector('.card-body').innerHTML += `
            <div class="alert alert-danger" role="alert">
                Error loading your results. Please try again later.
            </div>
        `;
    }
}

/**
 * Render the user profile
 * @param {Object} profile - The user profile data
 */
function renderProfile(profile) {
    // Clear existing content
    strengthsList.innerHTML = '';
    
    // Add strengths to list
    profile.strengths.forEach(strength => {
        const li = document.createElement('li');
        li.textContent = strength;
        strengthsList.appendChild(li);
    });
    
    // Set work style and environment
    workStyle.textContent = profile.work_style;
    environment.textContent = profile.environment;
}

/**
 * Render job recommendations
 * @param {Array} recommendations - The job recommendations
 */
function renderRecommendations(recommendations) {
    // Clear existing content
    recommendationsContainer.innerHTML = '';
    
    // Add each recommendation
    recommendations.forEach(job => {
        const jobCard = document.createElement('div');
        jobCard.className = 'job-card';
        
        // Format fit score as percentage
        const fitScore = Math.round(job.fit_score * 100);
        
        jobCard.innerHTML = `
            <div class="job-title">${job.title}</div>
            <div class="fit-score">${fitScore}% Match</div>
            <div class="job-description">${job.description}</div>
            
            <div class="strengths-match">
                <h5>Matching Strengths:</h5>
                <ul>
                    ${job.strengths_match.map(strength => `<li>${strength}</li>`).join('')}
                </ul>
            </div>
            
            ${job.considerations ? `
                <div class="considerations">
                    <h5>Considerations:</h5>
                    <ul>
                        ${job.considerations.map(consideration => `<li>${consideration}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
        
        recommendationsContainer.appendChild(jobCard);
    });
}

/**
 * Navigate to a new page
 * @param {HTMLElement} targetPage - The page to navigate to
 */
function navigateTo(targetPage) {
    // Hide current page
    currentPage.classList.remove('active');
    
    // Show target page
    targetPage.classList.add('active');
    
    // Update current page
    currentPage = targetPage;
    
    // Scroll to top
    window.scrollTo(0, 0);
} 