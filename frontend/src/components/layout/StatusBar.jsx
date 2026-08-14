import { Activity, Database, Cpu, BrainCircuit } from 'lucide-react';

export default function StatusBar() {
  return (
    <div className="h-8 border-t border-line bg-inset flex items-center justify-between px-4 text-[11px] font-medium text-ink-3 tracking-wide uppercase">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-1.5">
          <BrainCircuit size={12} className="text-accent" />
          <span>LLM: Gemini</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Activity size={12} className="text-green" />
          <span>API: Healthy</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Database size={12} className="text-green" />
          <span>DB: Connected</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Cpu size={12} className="text-ink-3" />
          <span>MCP: Offline</span>
        </div>
      </div>
      
      <div>
        <span>FlowDocs Agentic Engine v0.1</span>
      </div>
    </div>
  );
}
