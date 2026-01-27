import './WorkflowProgress.css';

const WORKFLOW_STAGES = [
  { id: 'ingestion', label: 'Ingesting Proposal', icon: '📥' },
  { id: 'extraction', label: 'Extracting Features', icon: '🔍' },
  { id: 'retrieval', label: 'Retrieving Context', icon: '🔎' },
  { id: 'synthesis', label: 'Synthesizing Context', icon: '📝' },
  { id: 'council_stage1', label: 'Council Stage 1: Generating Opinions', icon: '🤖' },
  { id: 'council_stage2', label: 'Council Stage 2: Peer Rankings', icon: '📊' },
  { id: 'council_stage3', label: 'Council Stage 3: Final Synthesis', icon: '✨' },
  { id: 'validation', label: 'Validating Output', icon: '✅' },
  { id: 'report_ready', label: 'Report Ready', icon: '📄' },
];

export default function WorkflowProgress({ currentStage, progress }) {
  const getStageIndex = (stageId) => {
    return WORKFLOW_STAGES.findIndex(s => s.id === stageId);
  };

  const currentIndex = currentStage ? getStageIndex(currentStage) : -1;

  return (
    <div className="workflow-progress">
      <h2>Generating RIA Assessment</h2>
      <div className="progress-stages">
        {WORKFLOW_STAGES.map((stage, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex;
          const isPending = index > currentIndex;

          return (
            <div
              key={stage.id}
              className={`progress-stage ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''} ${isPending ? 'pending' : ''}`}
            >
              <div className="stage-icon">
                {isCompleted ? '✓' : isCurrent ? '⟳' : stage.icon}
              </div>
              <div className="stage-label">{stage.label}</div>
              {isCurrent && (
                <div className="stage-spinner">
                  <div className="spinner"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      {progress && (
        <div className="progress-details">
          {progress.chunks && (
            <div className="detail-item">
              <span className="detail-label">Chunks Retrieved:</span>
              <span className="detail-value">{progress.chunks}</span>
            </div>
          )}
          {progress.model && (
            <div className="detail-item">
              <span className="detail-label">Model:</span>
              <span className="detail-value">{progress.model}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
