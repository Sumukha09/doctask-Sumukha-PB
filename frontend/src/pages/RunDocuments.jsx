import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRunDetails } from '../api';
import LoadingState from '../components/ui/LoadingState';
import { ChevronRight, FileText, Download } from 'lucide-react';

export default function RunDocuments() {
  const { id } = useParams();
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);

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

  if (loading) return <div className="p-8"><LoadingState label="Loading documents..." /></div>;
  if (!details) return <div className="p-8">Failed to load run details.</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 pb-20">
      <div className="flex items-center text-xs text-ink-3 font-mono mb-2">
        <Link to="/runs" className="hover:text-ink hover:underline">Runs</Link>
        <ChevronRight size={12} className="mx-1" />
        <Link to={`/runs/${id}`} className="hover:text-ink hover:underline">{id.substring(0,8)}</Link>
        <ChevronRight size={12} className="mx-1" />
        <span>Documents</span>
      </div>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink flex items-center gap-2">
          <FileText className="text-ink" /> Ingested Documents
        </h1>
        <p className="text-sm text-ink-3 mt-1">Source material processed in this workflow run.</p>
      </div>

      {details.documents.length === 0 ? (
        <div className="p-12 border border-dashed border-line rounded-card flex flex-col items-center justify-center text-ink-3">
          <FileText size={32} className="mb-4 opacity-50" />
          <p className="text-sm">No documents were processed.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {details.documents.map(doc => (
            <div key={doc.id} className="rounded-card bg-surface border border-line shadow-card overflow-hidden flex flex-col">
              <div className="p-6 flex-1 flex flex-col items-center justify-center text-center">
                 <FileText size={48} className="text-ink-2 mb-4" />
                 <h2 className="text-sm font-semibold text-ink break-all">{doc.name}</h2>
                 <p className="text-xs text-ink-3 mt-1">{(doc.byte_size / 1024).toFixed(1)} KB</p>
              </div>
              <div className="p-3 bg-inset border-t border-line flex justify-between items-center">
                 <span className="text-xs text-green font-medium px-2 py-1 bg-green/10 rounded">Processed</span>
                 <a href={`http://127.0.0.1:8000/api/v1/runs/${id}/documents/${doc.id}/content`} target="_blank" rel="noreferrer"
                    className="flex items-center gap-1 text-xs font-medium text-accent hover:underline">
                    Download <Download size={12} />
                 </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
