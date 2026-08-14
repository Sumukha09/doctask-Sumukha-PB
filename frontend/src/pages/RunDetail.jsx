import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRunState, getRunDetails, addDocumentsToRun, resumeRun } from '../api';
import TaskRows from '../components/ui/TaskRows';
import LoadingState from '../components/ui/LoadingState';
import { AlertCircle, CheckCircle2, Clock, ChevronRight, Upload, FilePlus } from 'lucide-react';

const STAGES = [
  'ingest',
  'extract',
  'analyze',
  'verify',
  'approval',
  'complete'
];

export default function RunDetail() {
  const { id } = useParams();
  const [state, setState] = useState(null);
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [initialDocIds, setInitialDocIds] = useState(() => {
    const saved = sessionStorage.getItem(`run_${id}_initial_docs`);
    return saved ? JSON.parse(saved) : null;
  });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    
    async function load() {
      try {
        const [s, d] = await Promise.all([
          getRunState(id),
          getRunDetails(id).catch(() => null)
        ]);
        if (mounted) {
          setState(s);
          setDetails(d);
          setLoading(false);
          
          if (d && initialDocIds === null) {
             const ids = d.documents.map(doc => doc.id);
             setInitialDocIds(ids);
             sessionStorage.setItem(`run_${id}_initial_docs`, JSON.stringify(ids));
          }
        }
      } catch (e) {
        console.error(e);
        if (mounted) setLoading(false);
      }
    }
    
    load();
    const interval = setInterval(load, 3000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [id]);

  if (loading) {
    return <div className="p-8"><LoadingState label="Loading workflow state..." variant="Dots" /></div>;
  }

  if (!state) {
    return <div className="p-8 text-red">Failed to load run state.</div>;
  }

  const currentStageIndex = STAGES.indexOf(state.current_stage);
  const isFailed = state.status === 'failed';
  const isCompleted = state.status === 'completed';

  const allDocs = details?.documents || [];
  const existingDocs = initialDocIds ? allDocs.filter(d => initialDocIds.includes(d.id)) : allDocs;
  const newDocs = initialDocIds ? allDocs.filter(d => !initialDocIds.includes(d.id)) : [];

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    
    setIsUploading(true);
    setUploadError(null);
    try {
      await addDocumentsToRun(id, files);
      
      // Fetch updated state immediately instead of waiting for the interval
      const [s, d] = await Promise.all([
        getRunState(id),
        getRunDetails(id).catch(() => null)
      ]);
      setState(s);
      setDetails(d);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };
  const handleResume = async (e) => {
    e.preventDefault();
    try {
      await resumeRun(id);
    } catch (err) {
      console.error(err);
      alert(err.message || "Failed to resume operation");
    }
  };

  const completedStages = state.completed_stages || [];
  let actualFailedIndex = -1;
  if (isFailed) {
    const errString = (state.errors && state.errors.length > 0) ? state.errors[0].toLowerCase() : "";
    if (errString.includes("extract") || errString.includes("chunk")) {
      actualFailedIndex = STAGES.indexOf('extract');
    } else if (errString.includes("analyz") || errString.includes("evidence")) {
      actualFailedIndex = STAGES.indexOf('analyze');
    } else if (errString.includes("verify") || errString.includes("claim")) {
      actualFailedIndex = STAGES.indexOf('verify');
    } else if (errString.includes("ingest")) {
      actualFailedIndex = STAGES.indexOf('ingest');
    } else if (errString.includes("commit") || errString.includes("report")) {
      actualFailedIndex = STAGES.indexOf('complete');
    }

    if (actualFailedIndex === -1) {
      for (let i = 0; i < STAGES.length; i++) {
        if (!completedStages.includes(STAGES[i])) {
          actualFailedIndex = i;
          break;
        }
      }
      if (actualFailedIndex === -1 && currentStageIndex > -1) {
        actualFailedIndex = currentStageIndex;
      }
    }
  }

  const taskRowsData = STAGES.map((stage, idx) => {
    let status = 'pending';
    const isPast = isCompleted || completedStages.includes(stage) || (currentStageIndex > -1 && idx < currentStageIndex);
    const isCurrent = !isCompleted && !isFailed && currentStageIndex === idx;

    if (isFailed) {
      if (actualFailedIndex !== -1 && idx === actualFailedIndex) {
        status = 'failed';
      } else if (actualFailedIndex !== -1 && idx > actualFailedIndex) {
        status = 'pending';
      } else if (completedStages.includes(stage)) {
        status = 'done';
      } else {
        status = 'pending';
      }
    } else {
      if (isPast) status = 'done';
      if (isCurrent) status = 'running';
      if (isCompleted && stage === 'complete') status = 'done';
    }
    
    const stageLabels = {
      ingest: { label: "Ingesting Documents", amount: newDocs.length ? `${newDocs.length} new files` : allDocs.length ? `${allDocs.length} files` : "Pending" },
      extract: { label: "Extracting Claims", amount: newDocs.length && isCurrent ? "Processing new files" : "Processing" },
      analyze: { label: "Analyzing Evidence", amount: newDocs.length && isCurrent ? "Processing new files" : "Processing" },
      verify: { label: "Verifying Compliance", amount: newDocs.length && isCurrent ? "Processing new files" : "Processing" },
      approval: { label: "Human Review", amount: details?.findings?.length ? `${details.findings.length} findings` : "Pending" },
      complete: { label: "Commit Results", amount: "Finalizing" },
    };

    let stageDetails = [{ label: "Status", meta: status }];
    if (stage === 'ingest' && details) {
      const docsToShow = newDocs.length > 0 ? newDocs : allDocs;
      stageDetails = docsToShow.map(d => ({ label: d.name, meta: `${(d.byte_size/1024).toFixed(1)} KB` }));
    } else if (stage === 'approval' && isCurrent) {
      stageDetails = [{ label: "Action required", meta: "Review Findings" }];
    } else if (isFailed && actualFailedIndex === idx) {
      stageDetails = [{ label: "Error", meta: "Execution halted" }];
    }

    let action = null;
    if (stage === 'approval' && isCurrent) {
      action = (
        <Link to={`/runs/${id}/approvals`} className="text-[12.5px] font-medium text-accent hover:underline flex items-center gap-1">
          Open Human Review <ChevronRight size={14} />
        </Link>
      );
    } else if (isFailed && actualFailedIndex === idx) {
      action = (
        <button 
          onClick={handleResume} 
          className="text-[12.5px] font-medium text-accent hover:underline flex items-center gap-1"
        >
          Resume Operation <ChevronRight size={14} />
        </button>
      );
    }

    return {
      key: stage,
      status: status,
      label: stageLabels[stage].label,
      amount: status === 'done' ? "Completed" : stageLabels[stage].amount,
      details: stageDetails,
      action: action
    };
  });

  return (
    <div className="p-8 pb-20 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center text-xs text-ink-3 font-mono mb-2">
          <Link to="/runs" className="hover:text-ink hover:underline">Runs</Link>
          <ChevronRight size={12} className="mx-1" />
          <span>{id}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Workflow Execution</h1>
        
        {isFailed && state.errors && (
          <div className="mt-4 p-4 rounded-card bg-red/10 border border-red/20 text-red flex gap-3 items-start">
            <AlertCircle className="shrink-0 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-sm">Run Failed</p>
              <p className="text-xs mt-1 opacity-90">{state.errors.join(' ')}</p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-sm font-semibold text-ink-3 uppercase tracking-wider">Execution Trace</h2>
          <TaskRows rows={taskRowsData} variant="Capsules" />
        </div>

        <div className="space-y-6">
          <div className="p-4 rounded-card bg-surface shadow-card border border-line">
            <h3 className="text-xs font-semibold text-ink-3 uppercase tracking-wider mb-4">Run Context</h3>
            
            <div className="space-y-4 text-sm">
              <div>
                <span className="text-ink-3 block mb-1">Status</span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase
                  ${isCompleted ? 'bg-green/10 text-green' : isFailed ? 'bg-red/10 text-red' : 'bg-accent/10 text-accent'}`}>
                  {state.status}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 pb-2">
                <div>
                  <span className="text-ink-3 block mb-1">Documents</span>
                  <div className="font-medium text-ink">{allDocs.length} files</div>
                </div>
                <div>
                  <span className="text-ink-3 block mb-1">Findings</span>
                  <div className="font-medium text-ink">{details?.findings?.length || 0} detected</div>
                </div>
              </div>
              
              <div className="pt-3 border-t border-line space-y-3">
                {newDocs.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-accent uppercase block mb-1">New Documents ({newDocs.length})</span>
                    <ul className="text-xs text-ink space-y-1">
                      {newDocs.map(d => <li key={d.id} className="truncate" title={d.name}>• {d.name}</li>)}
                    </ul>
                  </div>
                )}
                
                {existingDocs.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-ink-3 uppercase block mb-1">Existing Documents ({existingDocs.length})</span>
                    <ul className="text-xs text-ink-2 space-y-1">
                      {existingDocs.map(d => <li key={d.id} className="truncate" title={d.name}>• {d.name}</li>)}
                    </ul>
                  </div>
                )}
              </div>
              
              <div className="pt-4 border-t border-line space-y-2">
                <input 
                  type="file" 
                  multiple 
                  accept=".pdf" 
                  ref={fileInputRef} 
                  className="hidden" 
                  onChange={handleUpload} 
                />
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-surface text-ink border border-line rounded-control font-medium text-sm hover:bg-surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? <LoadingState variant="Spinner" size={14} /> : <FilePlus size={14} />}
                  {isUploading ? "Uploading..." : "Add Documents"}
                </button>
                {uploadError && (
                  <p className="text-xs text-red text-center mt-1">{uploadError}</p>
                )}
              </div>
              
              {state.status === 'completed' && (
                <div className="pt-4 border-t border-line">
                  <a href={`http://127.0.0.1:8000/api/v1/runs/${id}/report`} target="_blank" rel="noreferrer" 
                     className="w-full text-center block px-3 py-2 bg-ink text-canvas rounded-control font-medium text-sm hover:bg-ink-2 transition-colors">
                    Download Deliverable
                  </a>
                </div>
              )}
            </div>
          </div>
          
          {/* Recovery context if resumed */}
          {state.errors && state.errors.length > 0 && !isFailed && (
             <div className="p-4 rounded-card bg-orange/10 border border-orange/20">
               <h3 className="text-xs font-semibold text-orange uppercase tracking-wider mb-2">Recovery Info</h3>
               <p className="text-xs text-orange opacity-90">Run was previously interrupted and resumed from checkpoint.</p>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
