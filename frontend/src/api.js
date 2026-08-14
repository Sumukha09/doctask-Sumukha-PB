const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export async function createRun(files, complianceRules = null) {
  const payload = {
    files: files.map(f => ({
      file_path: f.path || null,
      file_content_base64: f.base64 || null,
      file_name: f.name || null
    })),
    compliance_rules: complianceRules
  };
    
  const response = await fetch(`${API_BASE_URL}/runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to create run');
  }
  return response.json();
}

export async function addDocumentsToRun(runId, files) {
  const formData = new FormData();
  files.forEach(f => {
    formData.append('files', f);
  });

  const response = await fetch(`${API_BASE_URL}/runs/${runId}/documents`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to add documents');
  }
  return response.json();
}

export async function downloadReport(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/report`, {
    method: 'GET',
  });
  if (!response.ok) {
    throw new Error('Failed to download report');
  }
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = `flowdocs_report_${runId.substring(0,8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function getRunState(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/state`);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to fetch run state');
  }
  return response.json();
}

export async function getRunDetails(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/details`);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to fetch run details');
  }
  return response.json();
}

export async function approveFinding(runId, findingId, decision, editedText, comment) {
  const body = { decision };
  if (editedText) body.edited_text = editedText;
  if (comment) body.comment = comment;

  const response = await fetch(`${API_BASE_URL}/runs/${runId}/findings/${findingId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to submit approval');
  }
  return response.json();
}

export async function commitCleanRun(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/commit_clean`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to commit run');
  }
  return response.json();
}

export async function getRuns() {
  const response = await fetch(`${API_BASE_URL}/runs`);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to fetch runs');
  }
  return response.json();
}

export async function resumeRun(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/resume`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to resume run');
  }
  return response.json();
}

export async function crashServer() {
  await fetch(`${API_BASE_URL}/runs/crash`, {
    method: 'POST',
  });
}

export async function getGlobalStats() {
  const response = await fetch(`${API_BASE_URL}/runs/stats/global`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch global stats');
  }
  return response.json();
}

export async function getRunAudit(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/audit`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch run audit logs');
  }
  return response.json();
}

export async function getRunCost(runId) {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/cost`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch run cost report');
  }
  return response.json();
}
