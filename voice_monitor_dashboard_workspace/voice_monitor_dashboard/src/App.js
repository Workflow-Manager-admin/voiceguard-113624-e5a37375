import React, { useState, useEffect } from 'react';
import './App.css';
import VoiceTest from './VoiceTest';

/**
 * PUBLIC_INTERFACE
 * Main App component with audio file upload (voice enrollment) form integrated.
 */
function App() {
  // State for file, status & messages
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle | uploading | success | error
  const [message, setMessage] = useState('');

  // Enrollment status states
  const [enrollmentStatus, setEnrollmentStatus] = useState(null); // null | true | false
  const [enrollmentLoading, setEnrollmentLoading] = useState(true);
  const [enrollmentError, setEnrollmentError] = useState('');

  // For demo, a static user id is used
  const USER_ID = 'demo_user';

  // Handle file selection
  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage('');
    setUploadStatus('idle');
  };

  // Fetch enrollment status from backend
  // PUBLIC_INTERFACE
  async function fetchEnrollmentStatus() {
    setEnrollmentLoading(true);
    setEnrollmentError('');
    setEnrollmentStatus(null);
    try {
      const url = process.env.REACT_APP_BACKEND_URL
        ? `${process.env.REACT_APP_BACKEND_URL}/enroll/status?user_id=${encodeURIComponent(USER_ID)}`
        : `http://localhost:3001/enroll/status?user_id=${encodeURIComponent(USER_ID)}`;
      const res = await fetch(url);
      if (!res.ok) {
        setEnrollmentError('Error fetching status.');
        setEnrollmentStatus(null);
      } else {
        const data = await res.json();
        // Accepts: { enrolled: true } or { enrolled: false }
        setEnrollmentStatus(data && typeof data.enrolled === 'boolean' ? data.enrolled : null);
      }
    } catch (error) {
      setEnrollmentError('Could not connect to backend.');
      setEnrollmentStatus(null);
    }
    setEnrollmentLoading(false);
  }

  // Fetch on mount
  useEffect(() => {
    fetchEnrollmentStatus();
    // eslint-disable-next-line
  }, []);

  // PUBLIC_INTERFACE
  // Handles the form submission to upload audio for enrollment.
  const handleSubmit = async (event) => {
    event.preventDefault();
    setUploadStatus('uploading');
    setMessage('');
    if (!selectedFile) {
      setUploadStatus('error');
      setMessage('Please select an audio file.');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Upload to backend (adjust /enroll/voice if proxy not set up)
      const url = process.env.REACT_APP_BACKEND_URL
        ? `${process.env.REACT_APP_BACKEND_URL}/enroll/voice?user_id=${encodeURIComponent(USER_ID)}`
        : `http://localhost:3001/enroll/voice?user_id=${encodeURIComponent(USER_ID)}`;
      const res = await fetch(
        url,
        {
          method: 'POST',
          body: formData,
        }
      );
      if (res.ok) {
        setUploadStatus('success');
        setMessage('Upload successful! Your voice reference has been enrolled.');
        // Re-fetch enrollment status so the UI updates
        fetchEnrollmentStatus();
      } else {
        setUploadStatus('error');
        const data = await res.json().catch(() => ({}));
        setMessage(data && data.detail ? data.detail : 'Upload failed. Please try again.');
      }
    } catch (err) {
      setUploadStatus('error');
      setMessage('Error uploading file. Please try again.');
    }
  };

  return (
    <div className="app">
      <nav className="navbar">
        <div className="container">
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <div className="logo">
              <span className="logo-symbol">*</span> KAVIA AI
            </div>
            <button className="btn">Template Button</button>
          </div>
        </div>
      </nav>

      <main>
        <div className="container">
          <div className="hero">
            <div className="subtitle">Voice Reference Enrollment</div>
            <h1 className="title">voice_monitor_dashboard</h1>
            <div className="description">
              Upload your reference audio file so the system can monitor media for matches to your voice.
            </div>

            {/* Enrollment status visual indicator */}
            <div style={{ margin: '18px 0' }}>
              {enrollmentLoading && (
                <div className="upload-message uploading">Checking enrollment status...</div>
              )}
              {enrollmentError && (
                <div className="upload-message error">Status: {enrollmentError}</div>
              )}
              {!enrollmentLoading && enrollmentStatus === true && (
                <div className="upload-message success">
                  <span style={{ marginRight: 10, fontWeight: 700 }}>ENROLLED</span> Your voice reference is active.
                </div>
              )}
              {!enrollmentLoading && enrollmentStatus === false && (
                <div className="upload-message error">
                  <span style={{ marginRight: 10, fontWeight: 700 }}>NOT ENROLLED</span> No voice profile found.
                </div>
              )}
            </div>

            {/* Audio upload form */}
            <form className="voice-upload-form" onSubmit={handleSubmit}>
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                disabled={uploadStatus === 'uploading'}
                className="voice-upload-input"
              />
              <button
                type="submit"
                className="btn btn-large"
                disabled={uploadStatus === 'uploading' || !selectedFile}
                style={{ marginLeft: 8 }}
              >
                {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload Audio'}
              </button>
            </form>
            {/* Status/message */}
            {uploadStatus === 'success' && (
              <div className="upload-message success">{message}</div>
            )}
            {uploadStatus === 'error' && (
              <div className="upload-message error">{message}</div>
            )}
            {uploadStatus === 'uploading' && (
              <div className="upload-message uploading">Uploading audio... Please wait.</div>
            )}
            {uploadStatus === 'idle' && message && (
              <div className="upload-message">{message}</div>
            )}
          </div>
          <VoiceTest />
        </div>
      </main>
    </div>
  );
}

export default App;
