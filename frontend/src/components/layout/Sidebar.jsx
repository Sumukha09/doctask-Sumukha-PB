import { NavLink, useParams } from 'react-router-dom';
import { 
  LayoutDashboard, 
  List, 
  FileText, 
  AlertTriangle, 
  Crosshair, 
  CheckSquare, 
  CheckCircle, 
  History, 
  Activity, 
  Settings,
  Cpu
} from 'lucide-react';

export default function Sidebar() {
  const { id: runId } = useParams();

  const globalLinks = [
    { to: '/', icon: LayoutDashboard, label: 'Overview' },
    { to: '/runs', icon: List, label: 'Runs' },
  ];

  const runLinks = runId ? [
    { to: `/runs/${runId}`, icon: Activity, label: 'Run Timeline' },
    { to: `/runs/${runId}/documents`, icon: FileText, label: 'Documents' },
    { to: `/runs/${runId}/claims`, icon: CheckCircle, label: 'Claims & Evidence' },
    { to: `/runs/${runId}/findings`, icon: AlertTriangle, label: 'Findings & Conflicts' },
    { to: `/runs/${runId}/approvals`, icon: CheckSquare, label: 'Approvals' },
    { to: `/runs/${runId}/deliverable`, icon: FileText, label: 'Deliverable' },
    { to: `/runs/${runId}/audit`, icon: History, label: 'Changelog / Cost' },
  ] : [];

  const systemLinks = [
    { to: '/health', icon: Activity, label: 'System Health' },
    { to: '#', icon: Cpu, label: 'MCP (Offline)' },
    { to: '#', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="w-64 h-full border-r border-line bg-surface flex flex-col">
      <div className="p-4 border-b border-line flex items-center gap-2">
        <div className="size-6 rounded bg-accent text-white flex items-center justify-center font-bold text-xs">F</div>
        <span className="font-semibold tracking-tight text-ink">FlowDocs</span>
      </div>

      <div className="flex-1 overflow-y-auto py-4 px-2 space-y-6">
        <div>
          <div className="px-3 mb-2 text-xs font-semibold text-ink-3 uppercase tracking-wider">Global</div>
          <div className="space-y-0.5">
            {globalLinks.map(link => (
              <NavLink 
                key={link.to} 
                to={link.to}
                className={({ isActive }) => 
                  `flex items-center gap-3 px-3 py-2 text-sm rounded-control transition-colors ${
                    isActive ? 'bg-field text-ink font-medium' : 'text-ink-2 hover:bg-hover hover:text-ink'
                  }`
                }
              >
                <link.icon size={16} />
                {link.label}
              </NavLink>
            ))}
          </div>
        </div>

        {runLinks.length > 0 && (
          <div>
            <div className="px-3 mb-2 text-xs font-semibold text-ink-3 uppercase tracking-wider truncate" title={`Run Context: ${runId}`}>
              Active Run
            </div>
            <div className="space-y-0.5">
              {runLinks.map(link => (
                <NavLink 
                  key={link.to} 
                  to={link.to}
                  end
                  className={({ isActive }) => 
                    `flex items-center gap-3 px-3 py-2 text-sm rounded-control transition-colors ${
                      isActive ? 'bg-field text-ink font-medium' : 'text-ink-2 hover:bg-hover hover:text-ink'
                    }`
                  }
                >
                  <link.icon size={16} />
                  {link.label}
                </NavLink>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="px-3 mb-2 text-xs font-semibold text-ink-3 uppercase tracking-wider">System</div>
          <div className="space-y-0.5">
            {systemLinks.map(link => (
              <NavLink 
                key={link.label} 
                to={link.to}
                className={({ isActive }) => 
                  `flex items-center gap-3 px-3 py-2 text-sm rounded-control transition-colors ${
                    isActive ? 'bg-field text-ink font-medium' : 'text-ink-2 hover:bg-hover hover:text-ink'
                  }`
                }
              >
                <link.icon size={16} />
                {link.label}
              </NavLink>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
