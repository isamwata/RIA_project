import { useState, useEffect } from 'react';
import ProposalForm from './components/ProposalForm';
import WorkflowProgress from './components/WorkflowProgress';
import ReviewInterface from './components/ReviewInterface';
import AssessmentHistory from './components/AssessmentHistory';
import { riaApi } from './api';
import './App.css';

// App states
const APP_STATES = {
  PROPOSAL: 'proposal',
  GENERATING: 'generating',
  REVIEW: 'review',
  SUCCESS: 'success',
};

function App() {
  const [appState, setAppState] = useState(APP_STATES.PROPOSAL);
  const [currentAssessment, setCurrentAssessment] = useState(null);
  const [currentReport, setCurrentReport] = useState(null);
  const [workflowStage, setWorkflowStage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [validationError, setValidationError] = useState(null);

  const handleSubmitProposal = async (proposal, metadata) => {
    try {
      setIsLoading(true);
      
      // Create assessment
      const assessment = await riaApi.createAssessment(proposal, metadata);
      setCurrentAssessment(assessment);
      setAppState(APP_STATES.GENERATING);
      setWorkflowStage('ingestion');

      // Start streaming workflow
      await riaApi.streamAssessment(assessment.assessment_id, (eventType, event) => {
        switch (eventType) {
          case 'workflow_start':
            setWorkflowStage(event.stage || 'ingestion');
            break;

          case 'workflow_complete':
            setWorkflowStage('report_ready');
            console.log('Workflow complete event received');
            // Don't set state here - wait for review_required or report event
            break;

          case 'validation_error':
            // Validation failed - show error with examples
            const errorData = event.data;
            setValidationError(errorData);
            setAppState(APP_STATES.PROPOSAL);
            setIsLoading(false);
            break;

          case 'report':
            // Report signal received - fetch the report from API
            // Backend sends only assessment_id, not the full report (to avoid large SSE payloads)
            console.log('Report event received, fetching report...');
            loadAssessmentAndReport(assessment.assessment_id).then(() => {
              setAppState(APP_STATES.REVIEW);
              setIsLoading(false);
            }).catch((error) => {
              console.error('Failed to load report:', error);
              setIsLoading(false);
            });
            break;

          case 'review_required':
            // Workflow complete, load full assessment and report
            console.log('Review required event received, loading assessment and report...');
            // If report is included in event, use it; otherwise fetch
            if (event.data && event.data.report) {
              setCurrentReport(event.data.report);
              setAppState(APP_STATES.REVIEW);
              setIsLoading(false);
            } else {
              // Fetch report from API
              loadAssessmentAndReport(assessment.assessment_id).then(() => {
                setAppState(APP_STATES.REVIEW);
                setIsLoading(false);
              }).catch((error) => {
                console.error('Failed to load report:', error);
                setIsLoading(false);
              });
            }
            break;

          case 'error':
            console.error('Workflow error:', event.message);
            alert(`Error generating assessment: ${event.message}`);
            setIsLoading(false);
            setAppState(APP_STATES.PROPOSAL);
            break;

          case 'stage':
            // Progress update for workflow stages
            if (event.stage) {
              setWorkflowStage(event.stage);
              console.log(`Workflow stage: ${event.stage} (node: ${event.node})`);
            }
            break;

          default:
            // Update workflow stage if provided
            if (event.stage) {
              setWorkflowStage(event.stage);
            }
            console.log(`Unhandled event type: ${eventType}`, event);
        }
      });
    } catch (error) {
      console.error('Failed to create assessment:', error);
      const errorMessage = error.message || 'Unknown error occurred';
      console.error('Error details:', errorMessage);
      alert(`Failed to create assessment: ${errorMessage}\n\nPlease check:\n- Backend is running on http://localhost:8000\n- Network connectivity\n- Browser console for details`);
      setIsLoading(false);
    }
  };

  const loadAssessmentAndReport = async (assessmentId) => {
    try {
      console.log(`Loading assessment and report for: ${assessmentId}`);
      const assessment = await riaApi.getAssessment(assessmentId);
      setCurrentAssessment(assessment);
      
      if (assessment.report) {
        console.log('Report found in assessment object');
        setCurrentReport(assessment.report);
        return assessment.report;
      } else {
        // Try to get report separately
        console.log('Report not in assessment, fetching separately...');
        try {
          const report = await riaApi.getReport(assessmentId);
          console.log('Report fetched successfully');
          setCurrentReport(report);
          return report;
        } catch (e) {
          console.error('Failed to load report:', e);
          throw e;
        }
      }
    } catch (error) {
      console.error('Failed to load assessment:', error);
      throw error;
    }
  };

  const handleReview = async (action, comments) => {
    if (!currentAssessment) return;

    try {
      setIsLoading(true);
      const result = await riaApi.reviewAssessment(
        currentAssessment.assessment_id,
        action,
        comments
      );

      if (action === 'approve') {
        setAppState(APP_STATES.SUCCESS);
        // Reload assessment to get updated status
        await loadAssessmentAndReport(currentAssessment.assessment_id);
      } else if (action === 'reject') {
        // Return to proposal form
        setAppState(APP_STATES.PROPOSAL);
        setCurrentAssessment(null);
        setCurrentReport(null);
      }
      // 'revise' is handled by handleRevise
    } catch (error) {
      console.error('Failed to submit review:', error);
      alert('Failed to submit review. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevise = (assessment) => {
    // Return to proposal form with existing proposal
    setAppState(APP_STATES.PROPOSAL);
    // Could pre-fill the form with existing proposal here
    setCurrentAssessment(null);
    setCurrentReport(null);
  };

  const handleNewAssessment = () => {
    setAppState(APP_STATES.PROPOSAL);
    setCurrentAssessment(null);
    setCurrentReport(null);
    setWorkflowStage(null);
    setValidationError(null);
  };

  const handleSelectAssessment = async (assessmentId) => {
    try {
      await loadAssessmentAndReport(assessmentId);
      setAppState(APP_STATES.REVIEW);
      setShowHistory(false);
    } catch (error) {
      console.error('Failed to load assessment:', error);
      alert('Failed to load assessment.');
    }
  };

  const renderContent = () => {
    switch (appState) {
      case APP_STATES.PROPOSAL:
        return (
          <ProposalForm
            onSubmit={handleSubmitProposal}
            isLoading={isLoading}
            validationError={validationError}
          />
        );

      case APP_STATES.GENERATING:
        return (
          <WorkflowProgress
            currentStage={workflowStage}
            progress={currentAssessment?.workflow_metadata}
          />
        );

      case APP_STATES.REVIEW:
        return (
          <ReviewInterface
            assessment={currentAssessment}
            report={currentReport}
            onReview={handleReview}
            onRevise={handleRevise}
          />
        );

      case APP_STATES.SUCCESS:
        return (
          <div className="success-screen">
            <div className="success-content">
              <div className="success-icon">✓</div>
              <h1>Assessment Approved and Saved</h1>
              <p>Your RIA assessment has been successfully approved and saved.</p>
              <div className="success-actions">
                <button
                  className="action-button primary"
                  onClick={handleNewAssessment}
                >
                  Create New Assessment
                </button>
                <button
                  className="action-button secondary"
                  onClick={() => setShowHistory(true)}
                >
                  View History
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="app">
      <div className="app-header">
        <div className="header-left">
          <div className="government-logo-container">
            <img 
              src="/belgian-government-logo.png" 
              alt="Federal Public Service Policy & Support" 
              className="government-logo"
              onLoad={(e) => {
                // Hide CSS fallback if image loads successfully
                const fallback = e.target.nextElementSibling;
                if (fallback) fallback.style.display = 'none';
              }}
              onError={(e) => {
                // Hide image if not found - CSS fallback will show
                e.target.style.display = 'none';
              }}
            />
            <div className="logo-fallback">
              <div className="logo-letters">
                <span className="logo-bo">BO</span>
                <div className="logo-divider">
                  <span className="dot black"></span>
                  <span className="line yellow"></span>
                  <span className="dot red"></span>
                </div>
                <span className="logo-sa">sa</span>
              </div>
              <div className="logo-text">
                <div>Federal Public Service</div>
                <div>Policy & Support</div>
              </div>
            </div>
          </div>
          <div className="header-title">
            <h1>Belgian RIA Assessment System</h1>
          </div>
        </div>
        <div className="header-actions">
          <button
            className="header-button"
            onClick={() => setShowHistory(!showHistory)}
          >
            {showHistory ? 'Hide' : 'Show'} History
          </button>
          {appState !== APP_STATES.PROPOSAL && (
            <button
              className="header-button"
              onClick={handleNewAssessment}
            >
              New Assessment
            </button>
          )}
        </div>
      </div>

      <div className="app-content">
        {showHistory && (
          <div className="history-sidebar">
            <AssessmentHistory
              onSelectAssessment={handleSelectAssessment}
            />
          </div>
        )}
        
        <div className={`main-content ${showHistory ? 'with-sidebar' : ''}`}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default App;
