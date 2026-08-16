import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRunDetails, approveFinding } from '../api';
import ApprovalCard from '../components/ui/ApprovalCard';
import LoadingState from '../components/ui/LoadingState';
import { ChevronRight, CheckSquare } from 'lucide-react';

export default function RunApprovals() {
  const { id } = useParams();
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRunDetails(id);
        setDetails(data);
      } catch(e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <div className="p-8"><LoadingState label="Loading findings for review..." /></div>;
  if (!details) return <div className="p-8">Failed to load run details.</div>;

  const pendingFindings = details.findings.filter(f => f.status === 'pending');

  const handleDecision = async (findingId, decision, comment) => {
    if (submitting) return; // Prevent race conditions
    setSubmitting(true);
    try {
      await approveFinding(id, findingId, decision, null, comment);
      
      // Reload details directly from authoritative backend state
      const newData = await getRunDetails(id);
      setDetails(newData);
    } catch(e) {
      console.error(e);
      alert(`Failed to submit decision: ${e.message || e}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center text-xs text-ink-3 font-mono mb-2">
        <Link to="/runs" className="hover:text-ink hover:underline">Runs</Link>
        <ChevronRight size={12} className="mx-1" />
        <Link to={`/runs/${id}`} className="hover:text-ink hover:underline">{id.substring(0,8)}</Link>
        <ChevronRight size={12} className="mx-1" />
        <span>Approvals</span>
      </div>
      
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink flex items-center gap-2">
          <CheckSquare className="text-accent" /> Human Review Gate
        </h1>
        <p className="text-sm text-ink-3 mt-1">Review and action the agent's findings before they are committed.</p>
      </div>

      {pendingFindings.length === 0 ? (
        <div className="p-12 border border-dashed border-line rounded-card flex flex-col items-center justify-center text-ink-3">
          <CheckSquare size={32} className="mb-4 text-green opacity-50" />
          <p className="text-sm mb-4">No pending items require your decision.</p>
          <button 
            onClick={async () => {
              try {
                setSubmitting(true);
                await import('../api').then(m => m.commitCleanRun(id));
                const newData = await getRunDetails(id);
                setDetails(newData);
                alert('Run committed successfully.');
              } catch(e) {
                console.error(e);
                alert('Failed to commit run.');
              } finally {
                setSubmitting(false);
              }
            }}
            disabled={submitting}
            className="px-4 py-2 bg-accent text-white text-sm font-medium rounded shadow-sm hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {submitting ? "Committing..." : "Commit Clean Run"}
          </button>
          <Link to={`/runs/${id}`} className="mt-4 text-ink-3 text-sm hover:underline">Return to Run Timeline</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
           <div className="space-y-4">
              <h2 className="text-sm font-semibold text-ink-3 uppercase tracking-wider">Review Queue ({pendingFindings.length})</h2>
              <ApprovalCard 
                 finding={pendingFindings[0]} 
                 totalPending={pendingFindings.length}
                 onSubmit={handleDecision}
                 isSubmitting={submitting}
              />
           </div>
           <div className="space-y-4">
              <h2 className="text-sm font-semibold text-ink-3 uppercase tracking-wider">Context</h2>
              <div className="p-4 rounded-card bg-inset border border-line text-sm text-ink-2">
                 Please review the items on the left carefully. Your decisions directly affect the final deliverable. Rejected findings will be excluded.
              </div>
           </div>
        </div>
      )}
    </div>
  );
}
