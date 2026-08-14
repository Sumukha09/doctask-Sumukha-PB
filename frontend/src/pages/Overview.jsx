import { useEffect, useState, useRef } from 'react';
import { getGlobalStats, getRuns, createRun } from '../api';
import { Activity, Clock, FileText, CheckCircle, AlertTriangle, PlayCircle, List } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import FilterTable from '../components/ui/FilterTable';

function StatCard({ title, value, label, icon: Icon, colorClass }) {
  return (
    <div className="rounded-card bg-surface shadow-card p-4 flex flex-col justify-between">
      <div className="flex items-start justify-between">
        <span className="text-sm font-medium text-ink-2">{title}</span>
        <div className={`p-2 rounded-control bg-field ${colorClass}`}>
          <Icon size={16} />
        </div>
      </div>
      <div className="mt-4">
        <div className="text-2xl font-bold text-ink tracking-tight">{value}</div>
        <div className="text-xs text-ink-3 mt-1 uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}

export default function Overview() {
  const [stats, setStats] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const fileInputRef = useRef(null);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, runsData] = await Promise.all([
          getGlobalStats().catch(() => null),
          getRuns().catch(() => [])
        ]);
        if (statsData) setStats(statsData);
        setRuns(runsData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="p-8 h-full flex flex-col">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 bg-field rounded-full animate-pulse" />
          <div className="space-y-2">
            <div className="w-48 h-6 bg-field rounded animate-pulse" />
            <div className="w-32 h-4 bg-field rounded animate-pulse" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
            <div key={i} className="h-32 rounded-card bg-field animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const s = stats || {
    total_runs: 0, active_runs: 0, successful_runs: 0, failed_runs: 0,
    total_documents: 0, total_claims: 0, total_findings: 0, pending_approvals: 0, total_cost_micro: 0
  };

  const tableFilters = [
    { key: "all", label: "All Runs", count: runs.length },
    { key: "running", label: "Running", dot: "var(--accent)", count: runs.filter(r => r.status === 'running' || r.status === 'pending').length },
    { key: "completed", label: "Completed", dot: "var(--green)", count: runs.filter(r => r.status === 'completed').length },
    { key: "failed", label: "Failed", dot: "var(--red)", count: runs.filter(r => r.status === 'failed').length },
  ];

  const tableRows = runs.map(r => {
    const isRunning = r.status === 'running' || r.status === 'pending';
    const isFailed = r.status === 'failed';
    const pillClass = isRunning ? "text-accent bg-accent-tint" : isFailed ? "text-red bg-red/10" : "text-green bg-green/10";
    
    return {
      statusKey: isRunning ? 'running' : r.status,
      cells: [
        <Link key={r.id} to={`/runs/${r.id}`} className="hover:underline text-ink font-mono">{r.id.substring(0, 8)}</Link>,
        <span key="date" className="tabular-nums">{new Date().toLocaleDateString()}</span>, // Fake date until we get it from backend
        <span key="status" className={`inline-flex h-5 items-center rounded-[5px] px-1.5 text-[11px] font-medium uppercase ${pillClass}`}>{r.status}</span>,
        <Link key="action" to={`/runs/${r.id}`} className="text-accent-ink hover:underline">View details</Link>
      ]
    };
  });

  return (
    <div className="p-8 pb-20 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Agentic Workflow Overview</h1>
          <p className="text-sm text-ink-3 mt-1">Real-time metrics and system observability.</p>
        </div>
        <div className="flex gap-2">
           <Link 
             to="/runs/new"
             className="flex items-center gap-2 px-3 py-1.5 rounded-control bg-accent text-white text-sm font-medium shadow-btn hover:bg-accent-ink transition-colors"
           >
              <PlayCircle size={16} /> New Run
           </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Runs" value={s.active_runs} label="Currently Executing" icon={Activity} colorClass="text-accent" />
        <StatCard title="Documents Processed" value={s.total_documents} label="Total Ingested" icon={FileText} colorClass="text-ink" />
        <StatCard title="Claims Extracted" value={s.total_claims} label="Grounded Statements" icon={CheckCircle} colorClass="text-green" />
        <StatCard title="Pending Approvals" value={s.pending_approvals} label="Awaiting Human Review" icon={AlertTriangle} colorClass="text-orange" />
        <StatCard title="Total Findings" value={s.total_findings} label="Detected issues" icon={AlertTriangle} colorClass="text-red" />
        <StatCard title="Total Runs" value={s.total_runs} label="All Time" icon={List} colorClass="text-ink-2" />
        <StatCard title="Cost Observer" value={`$${(s.total_cost_micro / 1000000).toFixed(4)}`} label="LLM API Cost" icon={Activity} colorClass="text-green" />
        
        <div className="rounded-card bg-surface shadow-card p-4 flex flex-col justify-between border-l-4 border-accent">
           <div className="flex items-start justify-between">
              <span className="text-sm font-medium text-ink-2">Rate Limits</span>
              <div className="p-2 rounded-control bg-field text-accent">
                <Clock size={16} />
              </div>
            </div>
            <div className="mt-4">
              <div className="flex justify-between items-end">
                <span className="text-2xl font-bold text-ink">7<span className="text-sm text-ink-3 font-normal"> RPM</span></span>
                <span className="text-xs text-ink-3">Limit: 10 RPM</span>
              </div>
              <div className="w-full bg-field h-1.5 rounded-full mt-2 overflow-hidden">
                 <div className="bg-accent h-full w-[70%]" />
              </div>
            </div>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight text-ink">Recent Runs</h2>
        {runs.length > 0 ? (
          <FilterTable 
            columns={{
              template: '1fr 1fr 1fr 1fr',
              headers: ['Run ID', 'Date', 'Status', 'Actions']
            }}
            filters={tableFilters} 
            rows={tableRows} 
          />
        ) : (
          <div className="p-12 border border-dashed border-line rounded-card flex flex-col items-center justify-center text-ink-3">
            <Activity size={32} className="mb-4 opacity-50" />
            <p className="text-sm">No runs executed yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
