import Sidebar from './Sidebar';
import StatusBar from './StatusBar';

export default function Layout({ children }) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-canvas text-ink font-sans">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto relative">
          {children}
        </main>
      </div>
      <StatusBar />
    </div>
  );
}
