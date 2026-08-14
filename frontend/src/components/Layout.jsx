import { FileText, Home } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children }) {
  const location = useLocation();

  return (
    <div className="min-h-screen text-slate-100 font-sans selection:bg-brand-500 selection:text-white relative overflow-hidden">
      
      {/* Giant ambient background watermark */}
      <div className="absolute top-20 left-1/2 -translate-x-1/2 text-[15rem] font-black text-white/[0.02] -z-10 pointer-events-none select-none tracking-tighter whitespace-nowrap">
        FLOWDOCS
      </div>

      <header className="glass-panel sticky top-0 z-50 border-b border-[#333333]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-3 text-brand-500 hover:text-brand-400 transition-colors group">
                <FileText className="w-5 h-5 group-hover:scale-110 transition-transform duration-300" />
                <span className="text-xl font-bold tracking-widest uppercase text-white">FLOWDOCS</span>
              </Link>
              
              <nav className="hidden md:flex items-center gap-4 border-l border-[#333333] pl-8">
                <Link 
                  to="/" 
                  className={`flex items-center gap-2 px-3 py-1.5 text-xs tracking-widest uppercase font-bold transition-all duration-300 ${
                    location.pathname === '/' 
                      ? 'text-brand-500' 
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Home className="w-3 h-3" />
                  Console
                </Link>
              </nav>
            </div>
            
            <div className="hidden md:flex items-center gap-4 text-xs tracking-widest text-slate-500 uppercase font-bold">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-brand-500 animate-pulse"></div>
                SYSTEM ONLINE
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
        {children}
      </main>
    </div>
  );
}
