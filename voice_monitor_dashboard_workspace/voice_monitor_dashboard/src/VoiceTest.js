import React, { useState } from 'react';
import './App.css';

/**
 * PUBLIC_INTERFACE
 * VoiceTest component allows users to upload a test audio file, submits it to the backend `/test/voice`
 * endpoint, and displays similarity match results for all enrolled voices.
 */
function VoiceTest() {
  // State for file selection, submission status, feedback message, and test results
  const [selectedFile, setSelectedFile] = useState(null);
  const [testStatus, setTestStatus] = useState('idle'); // idle | loading | success | error
  const [message, setMessage] = useState('');
  const [results, setResults] = useState([]);
  const [backendError, setBackendError] = useState('');

  // Handles file changes
  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage('');
    setTestStatus('idle');
    setResults([]);
    setBackendError('');
  };

  // Handles form submission and API call
  // PUBLIC_INTERFACE
  const handleSubmit = async (event) => {
    event.preventDefault();
    setTestStatus('loading');
    setBackendError('');
    setMessage('');
    setResults([]);

    if (!selectedFile) {
      setTestStatus('error');
      setMessage('Please select an audio file.');
      return;
    }
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      // The backend is assumed to have /test/voice accepting (multipart) files and returning results
      let apiBase = process.env.REACT_APP_BACKEND_URL;
      if (!apiBase) {
        if (window.location.hostname !== "localhost") {
          apiBase = window.location.origin.replace(/:3000\b/, ":3001");
        } else {
          apiBase = "http://localhost:3001";
        }
      }
      const url = `${apiBase}/test/voice`;
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        setTestStatus('error');
        let backendMsg = 'Voice test failed. Please try again.';
        // Try to read error message from backend
        try {
          const errorData = await response.json();
          if (errorData.detail) backendMsg = errorData.detail;
        } catch { }
        setBackendError(backendMsg);
        setMessage('');
        return;
      }

      // API expected to return: { matches: [ {enrollment_id: str, similarity: float}, ... ] }
      const data = await response.json();
      if (data && Array.isArray(data.matches)) {
        setResults(data.matches);
        setTestStatus('success');
        setMessage('Test complete.');
      } else {
        setTestStatus('error');
        setMessage('Received unexpected response from server.');
        setResults([]);
      }
    } catch (err) {
      setTestStatus('error');
      setBackendError('Could not connect to backend. Please try again.');
      setResults([]);
      setMessage('');
    }
  };

  return (
    <section style={{ marginTop: '60px', marginBottom: '60px' }}>
      <div className="subtitle">Voice Testing</div>
      <div className="description">
        Upload an audio sample to test similarity against all enrolled voice profiles.<br />
        Results will show the matched enrollments and similarity scores.
      </div>

      {/* Voice test form */}
      <form className="voice-upload-form" onSubmit={handleSubmit}>
        <input
          type="file"
          accept="audio/*"
          onChange={handleFileChange}
          disabled={testStatus === 'loading'}
          className="voice-upload-input"
        />
        <button
          type="submit"
          className="btn btn-large"
          disabled={testStatus === 'loading' || !selectedFile}
          style={{ marginLeft: 8 }}
        >
          {testStatus === 'loading' ? 'Testing...' : 'Test Voice'}
        </button>
      </form>

      {/* Feedback/status messages */}
      {testStatus === 'error' && (message || backendError) && (
        <div className="upload-message error">{message || backendError}</div>
      )}
      {testStatus === 'loading' && (
        <div className="upload-message uploading">Testing... Please wait.</div>
      )}
      {testStatus === 'success' && message && (
        <div className="upload-message success">{message}</div>
      )}

      {/* Show results if present */}
      {testStatus === 'success' && Array.isArray(results) && results.length > 0 && (
        <div style={{ marginTop: '32px' }}>
          <div
            style={{
              background: 'rgba(0,255,255,0.05)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '18px',
              maxWidth: '500px',
              margin: '0 auto'
            }}
          >
            <div style={{ fontWeight: 600, fontSize: '1.15rem', marginBottom: '14px' }}>
              <span role="img" aria-label="Microphone" style={{ marginRight: 9 }}>🎤</span>
              Match Results
            </div>
            <table style={{ width: '100%', color: 'var(--text-color)' }}>
              <thead>
                <tr style={{ color: 'var(--base-light)' }}>
                  <th style={{ textAlign: 'left', paddingBottom: 6 }}>Enrollment ID</th>
                  <th style={{ textAlign: 'left', paddingBottom: 6 }}>Similarity (%)</th>
                </tr>
              </thead>
              <tbody>
                {results
                  .sort((a, b) => (b.similarity || 0) - (a.similarity || 0))
                  .map((row, idx) => (
                  <tr key={idx} style={{ background: idx % 2 ? 'rgba(255,255,255,0.02)' : 'transparent'}}>
                    <td style={{ padding: '6px 10px 6px 0', fontFamily: 'monospace' }}>
                      {row.enrollment_id}
                    </td>
                    <td style={{ padding: '6px 0' }}>
                      {typeof row.similarity === 'number'
                        ? `${(row.similarity * 100).toFixed(1)}%`
                        : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ fontSize: '0.97rem', color: 'var(--text-secondary)', marginTop: '9px' }}>
              Higher similarity (%) values indicate stronger match.
            </div>
          </div>
        </div>
      )}

      {/* No matches found */}
      {testStatus === 'success' && Array.isArray(results) && results.length === 0 && (
        <div className="upload-message" style={{ marginTop: 16 }}>
          No enrolled voices were matched to your test audio file.
        </div>
      )}
    </section>
  );
}

export default VoiceTest;
