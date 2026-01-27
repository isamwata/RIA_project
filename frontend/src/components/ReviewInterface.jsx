import { useState } from 'react';
import RIAReportViewer from './RIAReportViewer';
import './ReviewInterface.css';

export default function ReviewInterface({ assessment, report, onReview, onRevise }) {
  const [action, setAction] = useState(null);
  const [comments, setComments] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleReview = async (reviewAction) => {
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    setAction(reviewAction);
    
    try {
      await onReview(reviewAction, comments);
    } catch (error) {
      console.error('Review submission error:', error);
      alert('Failed to submit review. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevise = () => {
    if (onRevise) {
      onRevise(assessment);
    }
  };

  return (
    <div className="review-interface">
      <div className="review-header">
        <h1>Review RIA Assessment</h1>
        <p>Please review the generated assessment and make your decision</p>
      </div>

      <div className="review-content">
        <div className="report-container">
          <RIAReportViewer report={report} />
        </div>

        <div className="review-panel">
          <div className="review-actions">
            <h3>Review Decision</h3>
            
            <div className="action-buttons">
              <button
                className="action-button approve"
                onClick={() => handleReview('approve')}
                disabled={isSubmitting}
              >
                ✓ Approve & Save
              </button>
              
              <button
                className="action-button revise"
                onClick={handleRevise}
                disabled={isSubmitting}
              >
                ↻ Request Revision
              </button>
              
              <button
                className="action-button reject"
                onClick={() => handleReview('reject')}
                disabled={isSubmitting}
              >
                ✗ Reject
              </button>
            </div>

            <div className="comments-section">
              <label htmlFor="review-comments">Comments (Optional)</label>
              <textarea
                id="review-comments"
                className="comments-textarea"
                placeholder="Add any comments or notes about this assessment..."
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                disabled={isSubmitting}
                rows={4}
              />
            </div>

            {isSubmitting && (
              <div className="submitting-indicator">
                <div className="spinner"></div>
                <span>Processing...</span>
              </div>
            )}
          </div>

          {assessment && (
            <div className="assessment-info">
              <h3>Assessment Information</h3>
              <div className="info-item">
                <span className="info-label">Status:</span>
                <span className="info-value">{assessment.status}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Created:</span>
                <span className="info-value">
                  {new Date(assessment.created_at).toLocaleString()}
                </span>
              </div>
              {assessment.metadata && (
                <>
                  {assessment.metadata.jurisdiction && (
                    <div className="info-item">
                      <span className="info-label">Jurisdiction:</span>
                      <span className="info-value">{assessment.metadata.jurisdiction}</span>
                    </div>
                  )}
                  {assessment.metadata.category && (
                    <div className="info-item">
                      <span className="info-label">Category:</span>
                      <span className="info-value">{assessment.metadata.category}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
