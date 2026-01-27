import { useState } from 'react';
import './ProposalForm.css';

export default function ProposalForm({ onSubmit, isLoading, validationError }) {
  const [proposal, setProposal] = useState('');
  const [jurisdiction, setJurisdiction] = useState('Belgian');
  const [category, setCategory] = useState('');
  const [year, setYear] = useState(new Date().getFullYear().toString());
  const [showExamples, setShowExamples] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (proposal.trim() && !isLoading) {
      const metadata = {
        jurisdiction,
        category: category || undefined,
        year: year || undefined,
        document_type: 'Impact Assessment',
      };
      onSubmit(proposal.trim(), metadata);
    }
  };

  return (
    <div className="proposal-form-container">
      <div className="proposal-form-header">
        <h1>Belgian Regulatory Impact Assessment</h1>
        <p>Enter your regulatory proposal to generate a comprehensive RIA assessment</p>
      </div>

      {validationError && (
        <div className="validation-error-box">
          <div className="error-header">
            <span className="error-icon">⚠️</span>
            <h3>Invalid Proposal Input</h3>
          </div>
          <div className="error-message">{validationError.message}</div>
          {validationError.input_received && (
            <div className="error-input">
              <strong>Input received:</strong> "{validationError.input_received}"
            </div>
          )}
          {validationError.guidance && (
            <div className="error-guidance">
              <strong>Guidance:</strong>
              <pre>{validationError.guidance}</pre>
            </div>
          )}
          {validationError.examples && validationError.examples.length > 0 && (
            <div className="error-examples">
              <button
                type="button"
                className="examples-toggle"
                onClick={() => setShowExamples(!showExamples)}
              >
                {showExamples ? 'Hide' : 'Show'} Example Proposals
              </button>
              {showExamples && (
                <div className="examples-list">
                  {validationError.examples.map((example, idx) => (
                    <div key={idx} className="example-item">
                      <div className="example-label">Example {idx + 1}:</div>
                      <div className="example-text">{example}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <form className="proposal-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="proposal">Regulatory Proposal *</label>
          <textarea
            id="proposal"
            className={`proposal-textarea ${validationError ? 'error' : ''}`}
            placeholder="Enter the regulatory proposal text here. Describe the regulation, its objectives, scope, and key provisions..."
            value={proposal}
            onChange={(e) => setProposal(e.target.value)}
            disabled={isLoading}
            rows={12}
            required
          />
          <div className="char-count">
            {proposal.length} characters | {proposal.split().length} words
            {proposal.split().length < 50 && proposal.length > 0 && (
              <span className="warning"> (minimum 50 words recommended)</span>
            )}
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="jurisdiction">Jurisdiction</label>
            <select
              id="jurisdiction"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              disabled={isLoading}
            >
              <option value="Belgian">Belgian</option>
              <option value="EU">EU</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="category">Category (Optional)</label>
            <input
              id="category"
              type="text"
              placeholder="e.g., Digital, Environment, Health"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="year">Year</label>
            <input
              id="year"
              type="text"
              placeholder="2024"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="submit-button"
            disabled={!proposal.trim() || isLoading}
          >
            {isLoading ? 'Generating...' : 'Generate RIA Assessment'}
          </button>
        </div>
      </form>
    </div>
  );
}
