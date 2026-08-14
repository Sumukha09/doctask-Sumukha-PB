import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRunAudit, getRunCost } from '../api';
import LoadingState from '../components/ui/LoadingState';
import { ChevronRight, History, DollarSign, Clock } from 'lucide-react';

export default function RunAudit() {
  const { id } = useParams();
  const [auditLogs, setAuditLogs] = useState([]);
  const [cost, setCost] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [logsData, costData] = await Promise.all([
          getRunAudit(id).catch(() => []),
          getRunCost(id).catch(() => null)
        ]);
        setAuditLogs(logsData);
        setCost(costData);
      } catch(e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <div className="p-8"><LoadingState label="Loading audit and cost data..." /></div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 pb-20">
      <div className="flex items-center text-xs text-ink-3 font-mono mb-2">
        <Link to="/runs" className="hover:text-ink hover:underline">Runs</Link>
        <ChevronRight size={12} className="mx-1" />
        <Link to={`/runs/${id}`} className="hover:text-ink hover:underline">{id.substring(0,8)}</Link>
        <ChevronRight size={12} className="mx-1" />
        <span>Changelog / Cost</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink flex items-center gap-2">
              <History className="text-ink" /> Living Changelog
            </h1>
            <p className="text-sm text-ink-3 mt-1">Chronological trace of agent and human actions.</p>
          </div>

          <div className="rounded-card bg-surface border border-line shadow-card overflow-hidden">
             {auditLogs.length === 0 ? (
               <div className="p-8 text-center text-ink-3 text-sm">No audit logs available.</div>
             ) : (
               <div className="divide-y divide-line">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="p-4 flex gap-4 hover:bg-hover transition-colors">
                       <div className="shrink-0 mt-0.5">
                          <Clock size={16} className="text-ink-3" />
                       </div>
                       <div>
                          <div className="flex items-baseline gap-2 mb-1">
                             <span className="text-sm font-semibold text-ink">{log.action}</span>
                             <span className="text-xs font-mono text-ink-3">{new Date(log.created_at).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-xs text-ink-2">Actor: <span className="font-mono">{log.actor}</span></p>
                          {log.payload && (
                             <pre className="mt-2 p-2 bg-inset rounded border border-line text-[10px] font-mono text-ink-3 overflow-x-auto">
                                {JSON.stringify(log.payload, null, 2)}
                             </pre>
                          )}
                       </div>
                    </div>
                  ))}
               </div>
             )}
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink flex items-center gap-2">
              <DollarSign className="text-green" /> Cost Observer
            </h1>
            <p className="text-sm text-ink-3 mt-1">LLM token usage and estimated cost.</p>
          </div>

          <div className="rounded-card bg-surface border border-line shadow-card p-6">
             {!cost ? (
                <div className="text-center text-ink-3 text-sm">No cost report generated yet.</div>
             ) : (
                <div className="space-y-6">
                   <div className="text-center">
                      <div className="text-4xl font-bold text-ink tracking-tight mb-1">
                         ${(cost.total_cost_micro / 1000000).toFixed(4)}
                      </div>
                      <div className="text-xs font-medium text-ink-3 uppercase tracking-wider">{cost.currency}</div>
                   </div>
                   
                   <div className="space-y-3 pt-6 border-t border-line">
                      <div className="flex justify-between text-sm">
                         <span className="text-ink-2">Input Tokens</span>
                         <span className="font-mono font-medium text-ink">{cost.breakdown?.input_tokens || 0}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                         <span className="text-ink-2">Output Tokens</span>
                         <span className="font-mono font-medium text-ink">{cost.breakdown?.output_tokens || 0}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                         <span className="text-ink-2">Total Tokens</span>
                         <span className="font-mono font-medium text-ink">{(cost.breakdown?.input_tokens || 0) + (cost.breakdown?.output_tokens || 0)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                         <span className="text-ink-2">Model Calls</span>
                         <span className="font-mono font-medium text-ink">{cost.breakdown?.successful_requests || 0}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                         <span className="text-ink-2">Retries</span>
                         <span className="font-mono font-medium text-orange">{cost.breakdown?.retries || 0}</span>
                      </div>
                   </div>
                </div>
             )}
          </div>
        </div>
      </div>
    </div>
  );
}
