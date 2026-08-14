import { useState, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { createRun } from '../api';
import { 
  FileUp, Loader2, AlertCircle, UploadCloud, FileText, X
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [manualPath, setManualPath] = useState('');
  const [complianceRules, setComplianceRules] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const handleCreateRun = async (e) => {
    if (e) e.preventDefault();
    if (files.length === 0 && !manualPath.trim()) {
        return;
    }
    
    setIsCreating(true);
    setError(null);
    try {
      const payloadFiles = [];
      
      for (const f of files) {
        if (f.object) {
          const base64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(f.object);
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
          });
          payloadFiles.push({ name: f.name, base64 });
        } else {
          payloadFiles.push({ path: f.path });
        }
      }
      
      if (manualPath.trim()) {
         payloadFiles.push({ path: manualPath.trim() });
      }

      const data = await createRun(payloadFiles, complianceRules.trim() ? complianceRules.trim() : null);
      console.log("[DEBUG] createRun returned successfully. Data:", data);
      
      console.log("[DEBUG] Navigating to /runs/" + data.run_id);
      navigate(`/runs/${data.run_id}`);
    } catch (err) {
      console.error("[DEBUG] Error caught in handleCreateRun:", err);
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
    <div className="grid grid-cols-1 md:grid-cols-12 gap-8 animate-in fade-in duration-500">
      
      {/* Sidebar Navigation */}
      <div className="col-span-1 md:col-span-2 space-y-3 border-r border-[#333333] pr-6 min-h-[calc(100vh-8rem)]">
        <div className="text-[10px] font-bold text-slate-500 tracking-[0.2em] mb-6 uppercase">System_Nav</div>
        <div className="flex items-center px-4 py-3 text-xs uppercase tracking-wider rounded-none bg-brand-500/10 text-brand-500 border border-brand-500 font-bold clip-corner">
          New_Run
        </div>
        <Link to="/runs" className="flex items-center px-4 py-3 text-xs uppercase tracking-wider rounded-none text-slate-400 border border-transparent hover:border-[#333333] hover:bg-[#121212] transition-colors clip-corner">
          Runs_Log
        </Link>
        <div className="flex items-center px-4 py-3 text-xs uppercase tracking-wider rounded-none text-slate-600 cursor-not-allowed">
          Documents
        </div>
        <div className="flex items-center px-4 py-3 text-xs uppercase tracking-wider rounded-none text-slate-600 cursor-not-allowed">
          Findings
        </div>
      </div>

      <div className="col-span-1 md:col-span-10 flex flex-col items-center justify-center min-h-[60vh]">
        <div className="text-center mb-16 relative w-full max-w-4xl">
          <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-white uppercase mb-6 leading-none">
            Document <br className="hidden md:block"/>Intelligence
          </h1>
          <div className="h-1 w-24 bg-brand-500 mx-auto mb-8"></div>
          <p className="text-slate-400 max-w-xl mx-auto text-sm md:text-base tracking-wide leading-relaxed font-light">
            DRAG AND DROP A DOCUMENT TO AUTOMATICALLY EXTRACT, VERIFY, AND REVIEW ITS CONTENTS IN REAL-TIME.
          </p>
        </div>

        <div className="w-full max-w-2xl relative group">
          <div className="relative glass-panel clip-corner p-10 bg-[#121212]">
            <div className="flex flex-col md:flex-row items-center justify-between mb-8 border-b border-[#333333] pb-6">
              <div className="flex items-center gap-4 mb-4 md:mb-0">
                <div className="w-12 h-12 flex items-center justify-center bg-brand-500 text-[#0A0A0A] clip-corner">
                  <FileUp className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold tracking-wider text-white uppercase">Process_Data</h2>
                  <p className="text-slate-500 text-xs uppercase tracking-widest mt-1">Initialize Pipeline</p>
                </div>
              </div>
              <div className="text-[10px] font-mono text-brand-500 tracking-widest border border-brand-500/30 px-2 py-1 bg-brand-500/10">
                AWAITING_INPUT
              </div>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 clip-corner flex items-start text-red-500 animate-in slide-in-from-top-2">
                <AlertCircle className="w-5 h-5 mr-3 shrink-0" />
                <span className="text-xs uppercase tracking-wide font-bold">{error}</span>
              </div>
            )}

            <form onSubmit={handleCreateRun} className="space-y-8">
              <div 
                className={cn(
                  "relative border-dashed-subtle p-10 transition-all duration-200 text-center flex flex-col items-center justify-center min-h-[180px] bg-[#0A0A0A]",
                  isDragging 
                    ? "border-brand-500 bg-brand-500/5" 
                    : "hover:border-slate-500"
                )}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              >
                <UploadCloud className={cn("w-12 h-12 mb-6 transition-colors", isDragging ? "text-brand-500" : "text-slate-600")} />
                <p className="text-sm text-slate-300 font-bold uppercase tracking-widest mb-2">Click to browse or drag and drop</p>
                <p className="text-[10px] uppercase text-slate-600 tracking-widest font-mono">SUPPORTED: PDF, TXT, DOCX</p>
                
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

              {files.length > 0 && (
                <div className="border border-[#333333] bg-[#0A0A0A] p-5 space-y-3">
                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Staged_Payload</div>
                  {files.map(f => (
                    <div key={f.id} className="flex items-center justify-between bg-[#121212] border border-[#333333] p-3">
                      <div className="flex items-center">
                        <FileText className="w-4 h-4 text-brand-500 mr-4 shrink-0" />
                        <span className="text-xs text-white font-medium tracking-wide truncate max-w-[300px]">{f.name}</span>
                      </div>
                      <button 
                        type="button" 
                        onClick={() => setFiles(prev => prev.filter(file => file.id !== f.id))}
                        className="text-slate-500 hover:text-red-500 transition-colors p-1"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-3">
                    Absolute File Path [OPTIONAL]
                  </label>
                  <input
                    type="text"
                    value={manualPath}
                    onChange={(e) => setManualPath(e.target.value)}
                    className="w-full bg-[#0A0A0A] border border-[#333333] text-white px-4 py-4 text-sm focus:outline-none focus:border-brand-500 transition-colors font-mono tracking-wide"
                    placeholder="E.G. /USERS/DATA/DOCUMENT.PDF"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-3">
                    Compliance Playbook [OPTIONAL]
                  </label>
                  <textarea
                    value={complianceRules}
                    onChange={(e) => setComplianceRules(e.target.value)}
                    className="w-full bg-[#0A0A0A] border border-[#333333] text-white px-4 py-4 text-sm focus:outline-none focus:border-brand-500 transition-colors font-mono tracking-wide h-32 resize-none"
                    placeholder="PASTE COMPLIANCE RULES HERE..."
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isCreating || (files.length === 0 && !manualPath.trim())}
                className={cn(
                  "w-full flex items-center justify-center py-5 px-6 text-sm font-bold uppercase tracking-widest transition-all duration-300 clip-corner mt-4",
                  isCreating 
                    ? "bg-[#333333] text-slate-500 cursor-not-allowed"
                    : (files.length === 0 && !manualPath.trim())
                      ? "bg-[#1A1A1A] text-slate-500 border border-[#333333] cursor-not-allowed"
                      : "bg-brand-500 hover:bg-brand-600 text-[#0A0A0A] shadow-[0_0_20px_rgba(255,107,0,0.2)] hover:shadow-[0_0_30px_rgba(255,107,0,0.4)]"
                )}
              >
                {isCreating ? <Loader2 className="w-5 h-5 animate-spin mr-3" /> : null}
                {isCreating ? 'INITIALIZING...' : 'EXECUTE WORKFLOW'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
