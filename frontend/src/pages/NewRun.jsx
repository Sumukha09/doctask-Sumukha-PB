import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { createRun } from '../api';
import { FileUp, Loader2, AlertCircle, UploadCloud, FileText, X, ChevronRight, PlayCircle } from 'lucide-react';

export default function NewRun() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [complianceRules, setComplianceRules] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const handleCreateRun = async (e) => {
    if (e) e.preventDefault();
    if (files.length === 0) return;
    
    setIsCreating(true);
    setError(null);
    try {
      const payloadFiles = [];
      for (const f of files) {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.readAsDataURL(f.object);
          reader.onload = () => resolve(reader.result.split(',')[1]);
          reader.onerror = reject;
        });
        payloadFiles.push({ name: f.name, base64 });
      }

      const data = await createRun(payloadFiles, complianceRules.trim() ? complianceRules.trim() : null);
      navigate(`/runs/${data.run_id}`);
    } catch (err) {
      console.error(err);
      setError(err.message);
      setIsCreating(false);
    }
  };

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files).map(file => ({
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        object: file
      }));
      setFiles(prev => [...prev, ...newFiles]);
    }
  }, []);

  return (
    <div className="p-8 pb-20 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center text-xs text-ink-3 font-mono mb-2">
        <Link to="/" className="hover:text-ink hover:underline">Overview</Link>
        <ChevronRight size={12} className="mx-1" />
        <span>New Run</span>
      </div>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Initialize Workflow</h1>
        <p className="text-sm text-ink-3 mt-1">Upload documents and configure compliance rules for analysis.</p>
      </div>

      {error && (
        <div className="p-4 rounded-card bg-red/10 border border-red/20 text-red flex gap-3 items-start">
          <AlertCircle className="shrink-0 mt-0.5" size={16} />
          <div>
            <p className="font-semibold text-sm">Initialization Failed</p>
            <p className="text-xs mt-1 opacity-90">{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleCreateRun} className="space-y-6">
        <div className="rounded-card bg-surface shadow-card border border-line p-6 space-y-6">
           <div>
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4">Source Documents</h2>
              <div 
                className={`relative border-2 border-dashed rounded-card p-10 transition-colors duration-200 text-center flex flex-col items-center justify-center min-h-[160px]
                  ${isDragging ? "border-accent bg-accent-tint" : "border-line bg-inset hover:border-ink-3"}`}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              >
                <UploadCloud size={32} className={`mb-4 transition-colors ${isDragging ? "text-accent" : "text-ink-3"}`} />
                <p className="text-sm text-ink font-medium mb-1">Click to browse or drag and drop</p>
                <p className="text-xs text-ink-3">Supported formats: PDF, TXT, DOCX</p>
                
                <input 
                  type="file" 
                  multiple
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
                  onChange={(e) => {
                    if(e.target.files && e.target.files.length > 0) {
                      const newFiles = Array.from(e.target.files).map(file => ({
                        id: Math.random().toString(36).substr(2, 9),
                        name: file.name,
                        object: file
                      }));
                      setFiles(prev => [...prev, ...newFiles]);
                      e.target.value = null;
                    }
                  }}
                />
              </div>
           </div>

           {files.length > 0 && (
             <div className="space-y-2">
               <h3 className="text-xs font-semibold text-ink-3 uppercase tracking-wider mb-2">Staged Payload</h3>
               {files.map(f => (
                 <div key={f.id} className="flex items-center justify-between bg-canvas border border-line rounded-control p-3">
                   <div className="flex items-center">
                     <FileText size={16} className="text-ink-3 mr-3 shrink-0" />
                     <span className="text-sm text-ink font-medium truncate max-w-[300px]">{f.name}</span>
                   </div>
                   <button 
                     type="button" 
                     onClick={() => setFiles(prev => prev.filter(file => file.id !== f.id))}
                     className="text-ink-3 hover:text-red transition-colors p-1"
                   >
                     <X size={16} />
                   </button>
                 </div>
               ))}
             </div>
           )}
        </div>

        <div className="rounded-card bg-surface shadow-card border border-line p-6">
           <h2 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4">Compliance Configuration</h2>
           <label className="block text-xs font-semibold text-ink-3 uppercase mb-2">
             Custom Rules (Optional)
           </label>
           <textarea
             value={complianceRules}
             onChange={(e) => setComplianceRules(e.target.value)}
             className="w-full bg-inset border border-line rounded-control text-ink p-3 text-sm focus:outline-none focus:border-accent transition-colors resize-y min-h-[120px]"
             placeholder="Enter specific compliance rules or policies to check against..."
           />
        </div>

        <div className="flex justify-end pt-4">
           <button
             type="submit"
             disabled={isCreating || files.length === 0}
             className={`flex items-center gap-2 px-6 py-2.5 rounded-[8px] text-sm font-bold shadow-btn transition-colors
               ${isCreating || files.length === 0 
                 ? "bg-field text-ink-3 cursor-not-allowed" 
                 : "bg-accent text-white hover:bg-accent-ink"}`}
           >
             {isCreating ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />}
             {isCreating ? 'Initializing...' : 'Execute Workflow'}
           </button>
        </div>
      </form>
    </div>
  );
}
