import { useState, useEffect } from 'react';
import { riaApi } from '../api';
import './AssessmentHistory.css';

export default function AssessmentHistory({ onSelectAssessment }) {
  const [assessments, setAssessments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'approved', 'rejected'

  useEffect(() => {
    loadAssessments();
  }, [filter]);

  const loadAssessments = async () => {
    try {
      setIsLoading(true);
      const status = filter === 'all' ? null : filter;
      const data = await riaApi.listAssessments(status);
      setAssessments(data);
    } catch (error) {
      console.error('Failed to load assessments:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      approved: { class: 'status-approved', label: '✓ Approved' },
      rejected: { class: 'status-rejected', label: '✗ Rejected' },
      review_required: { class: 'status-pending', label: '⏳ Review Required' },
      generating: { class: 'status-generating', label: '⟳ Generating' },
      revising: { class: 'status-revising', label: '↻ Revising' },
    };
    return badges[status] || { class: 'status-unknown', label: status };
  };

  return (
    <div className="assessment-history">
      <div className="history-header">
        <h2>Assessment History</h2>
        <div className="filter-buttons">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === 'approved' ? 'active' : ''}
            onClick={() => setFilter('approved')}
          >
            Approved
          </button>
          <button
            className={filter === 'rejected' ? 'active' : ''}
            onClick={() => setFilter('rejected')}
          >
            Rejected
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <span>Loading assessments...</span>
        </div>
      ) : assessments.length === 0 ? (
        <div className="empty-state">
          <p>No assessments found</p>
        </div>
      ) : (
        <div className="assessments-list">
          {assessments.map((assessment) => {
            const statusBadge = getStatusBadge(assessment.status);
            return (
              <div
                key={assessment.assessment_id}
                className="assessment-item"
                onClick={() => onSelectAssessment && onSelectAssessment(assessment.assessment_id)}
              >
                <div className="assessment-header">
                  <div className="assessment-title">
                    {assessment.proposal.length > 100
                      ? assessment.proposal.substring(0, 100) + '...'
                      : assessment.proposal}
                  </div>
                  <span className={`status-badge ${statusBadge.class}`}>
                    {statusBadge.label}
                  </span>
                </div>
                <div className="assessment-meta">
                  <span className="meta-item">
                    {new Date(assessment.created_at).toLocaleDateString()}
                  </span>
                  {assessment.metadata?.jurisdiction && (
                    <span className="meta-item">{assessment.metadata.jurisdiction}</span>
                  )}
                  {assessment.metadata?.category && (
                    <span className="meta-item">{assessment.metadata.category}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
