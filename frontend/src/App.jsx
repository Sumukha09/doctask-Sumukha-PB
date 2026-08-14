import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Overview from './pages/Overview';
import RunsList from './pages/RunsList';
import NewRun from './pages/NewRun';
import RunDetail from './pages/RunDetail';
import RunDocuments from './pages/RunDocuments';
import RunClaims from './pages/RunClaims';
import RunFindings from './pages/RunFindings';
import RunApprovals from './pages/RunApprovals';
import RunDeliverable from './pages/RunDeliverable';
import RunAudit from './pages/RunAudit';
import Health from './pages/Health';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/runs" element={<RunsList />} />
          <Route path="/runs/new" element={<NewRun />} />
          <Route path="/runs/:id" element={<RunDetail />} />
          <Route path="/runs/:id/documents" element={<RunDocuments />} />
          <Route path="/runs/:id/claims" element={<RunClaims />} />
          <Route path="/runs/:id/findings" element={<RunFindings />} />
          <Route path="/runs/:id/approvals" element={<RunApprovals />} />
          <Route path="/runs/:id/deliverable" element={<RunDeliverable />} />
          <Route path="/runs/:id/audit" element={<RunAudit />} />
          <Route path="/health" element={<Health />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
