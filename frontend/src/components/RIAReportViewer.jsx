import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import './RIAReportViewer.css';

// Component to handle pagination for themes section
function ThemesSection({ content, isExpanded, onToggle }) {
  const [currentPage, setCurrentPage] = useState(1);
  const themesPerPage = 10; // Show 10 themes per page (so page 1: 1-10, page 2: 11-21)
  
  // Split content by theme markers [1], [2], etc.
  const themes = useMemo(() => {
    if (!content) return [];
    
    // Split by theme markers [N] where N is 1-21
    const themeRegex = /(\[\d+\][^\[]*?)(?=\[\d+\]|$)/gs;
    const matches = content.match(themeRegex);
    
    if (matches && matches.length > 0) {
      return matches.map((theme, index) => ({
        id: index + 1,
        content: theme.trim()
      }));
    }
    
    // Fallback: if regex doesn't work, return full content as single item
    return [{ id: 1, content: content }];
  }, [content]);
  
  const totalPages = Math.ceil(themes.length / themesPerPage);
  const startIndex = (currentPage - 1) * themesPerPage;
  const endIndex = startIndex + themesPerPage;
  const currentThemes = themes.slice(startIndex, endIndex);
  
  // Reset to page 1 when section is collapsed/expanded
  const handleToggle = () => {
    if (!isExpanded) {
      setCurrentPage(1);
    }
    onToggle();
  };
  
  return (
    <section className="report-section themes-section">
      <div className="section-header" onClick={handleToggle}>
        <h2>
          21 Belgian Impact Themes Assessment
          {themes.length > 0 && (
            <span className="themes-count"> ({themes.length} themes)</span>
          )}
        </h2>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>
      {isExpanded && (
        <div className="section-content">
          {themes.length > themesPerPage ? (
            <>
              <div className="themes-pagination-info">
                Showing themes {startIndex + 1}-{Math.min(endIndex, themes.length)} of {themes.length}
              </div>
              <div className="themes-content">
                {currentThemes.map((theme) => (
                  <div key={theme.id} className="theme-item">
                    <ReactMarkdown>{theme.content}</ReactMarkdown>
                  </div>
                ))}
              </div>
              <div className="themes-pagination">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="pagination-button"
                >
                  ← Previous
                </button>
                <span className="pagination-info">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="pagination-button"
                >
                  Next →
                </button>
              </div>
            </>
          ) : (
            <div className="themes-content">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default function RIAReportViewer({ report }) {
  const [expandedSections, setExpandedSections] = useState({
    background: true,
    executive: true,
    overview: true,
    themes: true,
    summary: true,
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (!report) {
    return (
      <div className="report-viewer">
        <div className="report-empty">No report data available</div>
      </div>
    );
  }

  const sections = report.sections || {};
  const metadata = report.metadata || {};
  const content = report.content || "";
  
  // If sections is empty but we have content, show the full content
  const hasSections = Object.keys(sections).length > 0 && 
                     Object.values(sections).some(v => v && v.trim().length > 0);
  
  if (!hasSections && content) {
    // Fallback: show full content if sections extraction failed
    return (
      <div className="report-viewer">
        <div className="report-header">
          <h1>Belgian Regulatory Impact Assessment Report</h1>
          <div className="report-meta">
            {metadata.generated_at && (
              <span>Generated: {new Date(metadata.generated_at).toLocaleString()}</span>
            )}
            {metadata.model && <span>Model: {metadata.model}</span>}
          </div>
        </div>
        <section className="report-section">
          <div className="section-content">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </section>
      </div>
    );
  }
  
  if (!hasSections) {
    return (
      <div className="report-viewer">
        <div className="report-empty">No report content available</div>
      </div>
    );
  }

  return (
    <div className="report-viewer">
      <div className="report-header">
        <h1>Belgian Regulatory Impact Assessment Report</h1>
        <div className="report-meta">
          {metadata.generated_at && (
            <span>Generated: {new Date(metadata.generated_at).toLocaleString()}</span>
          )}
          {metadata.model && <span>Model: {metadata.model}</span>}
          {metadata.chunks_used && <span>Chunks Used: {metadata.chunks_used}</span>}
        </div>
      </div>

      {/* Background and Problem Definition */}
      {sections['Background and Problem Definition'] && (
        <section className="report-section">
          <div className="section-header" onClick={() => toggleSection('background')}>
            <h2>Background and Problem Definition</h2>
            <span className="toggle-icon">{expandedSections.background ? '▼' : '▶'}</span>
          </div>
          {expandedSections.background && (
            <div className="section-content">
              <ReactMarkdown>{sections['Background and Problem Definition']}</ReactMarkdown>
            </div>
          )}
        </section>
      )}

      {/* Executive Summary */}
      {sections['Executive Summary'] && (
        <section className="report-section">
          <div className="section-header" onClick={() => toggleSection('executive')}>
            <h2>Executive Summary</h2>
            <span className="toggle-icon">{expandedSections.executive ? '▼' : '▶'}</span>
          </div>
          {expandedSections.executive && (
            <div className="section-content">
              <ReactMarkdown>{sections['Executive Summary']}</ReactMarkdown>
            </div>
          )}
        </section>
      )}

      {/* Proposal Overview */}
      {sections['Proposal Overview'] && (
        <section className="report-section">
          <div className="section-header" onClick={() => toggleSection('overview')}>
            <h2>Proposal Overview</h2>
            <span className="toggle-icon">{expandedSections.overview ? '▼' : '▶'}</span>
          </div>
          {expandedSections.overview && (
            <div className="section-content">
              <ReactMarkdown>{sections['Proposal Overview']}</ReactMarkdown>
            </div>
          )}
        </section>
      )}

      {/* 21 Impact Themes */}
      {sections['21 Belgian Impact Themes Assessment'] && (
        <ThemesSection 
          content={sections['21 Belgian Impact Themes Assessment']}
          isExpanded={expandedSections.themes}
          onToggle={() => toggleSection('themes')}
        />
      )}

      {/* Overall Assessment Summary */}
      {sections['Overall Assessment Summary'] && (
        <section className="report-section">
          <div className="section-header" onClick={() => toggleSection('summary')}>
            <h2>Overall Assessment Summary</h2>
            <span className="toggle-icon">{expandedSections.summary ? '▼' : '▶'}</span>
          </div>
          {expandedSections.summary && (
            <div className="section-content">
              <ReactMarkdown>{sections['Overall Assessment Summary']}</ReactMarkdown>
            </div>
          )}
        </section>
      )}


      {/* Sources */}
      {report.sources && report.sources.length > 0 && (
        <section className="report-section sources-section">
          <h2>Sources</h2>
          <div className="sources-list">
            {report.sources.map((source, index) => (
              <div key={index} className="source-item">
                <div className="source-document">{source.document || 'Unknown'}</div>
                <div className="source-meta">
                  {source.jurisdiction && <span>Jurisdiction: {source.jurisdiction}</span>}
                  {source.category && <span>Category: {source.category}</span>}
                  {source.year && <span>Year: {source.year}</span>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
