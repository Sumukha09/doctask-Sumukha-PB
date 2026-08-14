import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRunDetails } from '../api';
import LoadingState from '../components/ui/LoadingState';
import { ChevronRight, FileText, CheckCircle } from 'lucide-react';

export default function RunDeliverable() {
  const { id } = useParams();
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeEvidence, setActiveEvidence] = useState(null);

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

  if (loading) return <div className="p-8"><LoadingState label="Loading deliverable..." /></div>;
  if (!details) return <div className="p-8">Failed to load run details.</div>;

  const approvedFindings = details.findings.filter(f => f.status === 'approved');

  return (
    <div className="p-8 max-w-6xl mx-auto flex gap-8 pb-20">
      <div className="flex-1 space-y-8">
         <div className="flex items-center text-xs text-ink-3 font-mono mb-2">
            <Link to="/runs" className="hover:text-ink hover:underline">Runs</Link>
            <ChevronRight size={12} className="mx-1" />
            <Link to={`/runs/${id}`} className="hover:text-ink hover:underline">{id.substring(0,8)}</Link>
            <ChevronRight size={12} className="mx-1" />
            <span>Deliverable</span>
         </div>
         
         <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink flex items-center gap-2">
               <FileText className="text-accent" /> Grounded Deliverable
            </h1>
            <p className="text-sm text-ink-3 mt-1">Final output with full evidence traceability.</p>
         </div>

         <div className="bg-white rounded-card shadow-card border border-line overflow-hidden text-black font-sans leading-relaxed">
            <div className="p-12">
               <h2 className="text-2xl font-bold mb-6 border-b pb-4">Verification Report</h2>
               
               {approvedFindings.length === 0 ? (
                  <p className="text-gray-600">No verified findings to report. The corpus is clean.</p>
               ) : (
                  <div className="space-y-8">
                     {approvedFindings.map(finding => (
                        <div key={finding.id} className="space-y-3">
                           <h3 className="text-lg font-semibold">{finding.title}</h3>
                           <p className="text-gray-700">{finding.summary}</p>
                           
                           <ul className="list-disc pl-5 space-y-2">
                              {finding.claims.map(claim => (
                                 <li key={claim.id} className="text-gray-800">
                                    {claim.statement}
                                    <button 
                                       onClick={() => setActiveEvidence(claim.evidence)}
                                       className="ml-2 inline-flex items-center gap-1 text-[10px] font-mono bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded border border-blue-200 hover:bg-blue-100 transition-colors"
                                    >
                                       [Evidence]
                                    </button>
                                 </li>
                              ))}
                           </ul>
                        </div>
                     ))}
                  </div>
               )}
            </div>
         </div>
      </div>
      
      {/* Evidence Sidebar */}
      <div className="w-80 shrink-0">
         <div className="sticky top-8 bg-surface rounded-card border border-line shadow-card p-4 h-[calc(100vh-120px)] flex flex-col">
            <h3 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-line pb-2 flex items-center gap-2">
               <CheckCircle size={16} className="text-green" /> Traceability
            </h3>
            
            <div className="flex-1 overflow-y-auto">
               {!activeEvidence ? (
                  <p className="text-sm text-ink-3">Click an [Evidence] marker in the document to trace its origin.</p>
               ) : (
                  <div className="space-y-4">
                     {activeEvidence.map((ev, i) => (
                        <div key={ev.id || i} className="space-y-2 bg-inset p-3 rounded-control border border-line">
                           <span className="text-xs font-mono text-accent">Source Document</span>
                           <p className="text-sm font-medium text-ink break-all">{ev.document_name}</p>
                           
                           <span className="text-xs font-mono text-accent block mt-3">Exact Quote</span>
                           <p className="text-sm text-ink-2 italic border-l-2 border-line pl-2">"{ev.snippet}"</p>
                        </div>
                     ))}
                  </div>
               )}
            </div>
         </div>
      </div>
    </div>
  );
}
