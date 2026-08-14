import { useEffect, useState } from 'react';
import { getRuns } from '../api';
import FilterTable from '../components/ui/FilterTable';
import LoadingState from '../components/ui/LoadingState';
import { Link } from 'react-router-dom';

export default function RunsList() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRuns();
        setRuns(data);
      } catch(e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="p-8"><LoadingState label="Loading runs..." /></div>;

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
        <Link key={r.id} to={`/runs/${r.id}`} className="hover:underline text-ink font-mono">{r.id.substring(0, 8)}...</Link>,
        <span key="date" className="tabular-nums">{new Date(r.created_at || Date.now()).toLocaleString()}</span>,
        <span key="status" className={`inline-flex h-5 items-center rounded-[5px] px-1.5 text-[11px] font-medium uppercase ${pillClass}`}>{r.status}</span>,
        <Link key="action" to={`/runs/${r.id}`} className="text-accent-ink hover:underline">View details</Link>
      ]
    };
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight text-ink">All Workflow Runs</h1>
      <FilterTable 
        columns={{
          template: '1.2fr 1fr 1fr 1fr',
          headers: ['Run ID', 'Created At', 'Status', 'Actions']
        }}
        filters={tableFilters} 
        rows={tableRows} 
      />
    </div>
  );
}
