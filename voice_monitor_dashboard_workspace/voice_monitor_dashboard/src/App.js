import React, { useState } from 'react';
import './App.css';

/**
 * PUBLIC_INTERFACE
 * Main App component with audio file upload (voice enrollment) form integrated.
 */
function App() {
  // State for file, status & messages
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle | uploading | success | error
  const [message, setMessage] = useState('');

  // Handle file selection
  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage('');
    setUploadStatus('idle');
  };

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
      const res = await fetch(
        process.env.REACT_APP_BACKEND_URL
          ? `${process.env.REACT_APP_BACKEND_URL}/enroll/voice`
          : 'http://localhost:3001/enroll/voice',
        {
          method: 'POST',
          body: formData,
        }
      );
      if (res.ok) {
        setUploadStatus('success');
        setMessage('Upload successful! Your voice reference has been enrolled.');
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
        </div>
      </main>
    </div>
  );
}

export default App;
