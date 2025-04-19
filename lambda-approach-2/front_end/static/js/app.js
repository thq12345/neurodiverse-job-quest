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
        
        // Generate HTML from the JSON profile and render it
        renderProfileFromJSON(results.profile);
        
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
 * Generate HTML from profile data and render it
 * @param {Object} profile - The profile object containing analysis data
 */
function renderProfileFromJSON(profile) {
    // Create the HTML content from profile data
    let profileHTML = `<div class='analysis-section'>`;
    
    // Format sections based on what's available in the profile
    if (profile.work_style) {
        const description = typeof profile.work_style === 'object' ? 
            profile.work_style.description : profile.work_style;
        const explanation = typeof profile.work_style === 'object' ? 
            profile.work_style.explanation || '' : '';
            
        profileHTML += `
            <h3>Work Style</h3>
            <p class="mb-2"><strong>${description}</strong></p>
            <p class="text-muted mb-4">${explanation}</p>
        `;
    }
    
    if (profile.environment) {
        const description = typeof profile.environment === 'object' ? 
            profile.environment.description : profile.environment;
        const explanation = typeof profile.environment === 'object' ? 
            profile.environment.explanation || '' : '';
            
        profileHTML += `
            <h3>Ideal Environment</h3>
            <p class="mb-2"><strong>${description}</strong></p>
            <p class="text-muted mb-4">${explanation}</p>
        `;
    }
    
    if (profile.interaction_level) {
        const description = typeof profile.interaction_level === 'object' ? 
            profile.interaction_level.description : profile.interaction_level;
        const explanation = typeof profile.interaction_level === 'object' ? 
            profile.interaction_level.explanation || '' : '';
            
        profileHTML += `
            <h3>Interaction Level</h3>
            <p class="mb-2"><strong>${description}</strong></p>
            <p class="text-muted mb-4">${explanation}</p>
        `;
    }
    
    if (profile.task_preference) {
        const description = typeof profile.task_preference === 'object' ? 
            profile.task_preference.description : profile.task_preference;
        const explanation = typeof profile.task_preference === 'object' ? 
            profile.task_preference.explanation || '' : '';
            
        profileHTML += `
            <h3>Task Preferences</h3>
            <p class="mb-2"><strong>${description}</strong></p>
            <p class="text-muted mb-4">${explanation}</p>
        `;
    }
    
    if (profile.additional_insights) {
        const description = typeof profile.additional_insights === 'object' ? 
            profile.additional_insights.description : profile.additional_insights;
        const explanation = typeof profile.additional_insights === 'object' ? 
            profile.additional_insights.explanation || '' : '';
            
        profileHTML += `
            <h3>Additional Insights</h3>
            <p class="mb-2"><strong>${description || 'No additional insights'}</strong></p>
            <p class="text-muted mb-4">${explanation}</p>
        `;
    }
    
    profileHTML += `</div>`;
    
    // Get the profile section
    const profileSection = document.querySelector('#results-content .row:first-child .col-md-12 .card-body');
    
    // Replace the existing content with the HTML
    if (profileSection) {
        profileSection.innerHTML = profileHTML;
    } else {
        // If the expected structure isn't found, create a container for the profile
        const profileContainer = document.createElement('div');
        profileContainer.className = 'profile-container';
        profileContainer.innerHTML = profileHTML;
        
        // Clear existing content in case it was filled by the legacy method
        if (strengthsList) strengthsList.innerHTML = '';
        if (workStyle) workStyle.textContent = '';
        if (environment) environment.textContent = '';
        
        // Append the new container to the parent of these elements
        if (strengthsList && strengthsList.parentElement) {
            const parentElement = strengthsList.parentElement.parentElement;
            parentElement.appendChild(profileContainer);
        } else {
            // Fallback in case the DOM structure is different
            const resultsDiv = document.getElementById('results-content');
            if (resultsDiv) {
                resultsDiv.innerHTML = profileHTML + resultsDiv.innerHTML;
            }
        }
    }
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
        
        // Format score as percentage - handle different property names
        const score = job.match_score || job.fit_score || 0;
        const displayScore = typeof score === 'number' ? Math.round(score) : Math.round(parseFloat(score) * 100);
        
        // Handle different property structures in job objects
        const title = job.title || '';
        const description = job.description || job.reasoning || '';
        const company = job.company ? `<div class="job-company">${job.company}</div>` : '';
        const location = job.location ? `<div class="job-location">${job.location}</div>` : '';
        
        // Create basic job card HTML
        let cardHTML = `
            <div class="job-title">${title}</div>
            <div class="match-score">${displayScore}% Match</div>
            ${company}
            ${location}
            <div class="job-description">${description}</div>
        `;
        
        // Add key traits if available
        if (job.key_traits) {
            const traits = job.key_traits || [];
            if (traits.length > 0) {
                cardHTML += `
                    <div class="key-traits">
                        <h5>Key Traits:</h5>
                        <ul>
                            ${traits.map(trait => `<li>${trait}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        }
        
        // Add environment if available
        if (job.environment) {
            cardHTML += `
                <div class="environment">
                    <h5>Work Environment:</h5>
                    <p>${job.environment}</p>
                </div>
            `;
        }
        
        // Add considerations if available
        if (job.considerations && job.considerations.length > 0) {
            cardHTML += `
                <div class="considerations">
                    <h5>Considerations:</h5>
                    <ul>
                        ${job.considerations.map(consideration => `<li>${consideration}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Add link if available
        if (job.url) {
            cardHTML += `
                <div class="job-link">
                    <a href="${job.url}" target="_blank" class="btn btn-primary btn-sm">Learn More</a>
                </div>
            `;
        }
        
        jobCard.innerHTML = cardHTML;
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