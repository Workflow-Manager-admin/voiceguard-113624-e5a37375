import React, { useState, useEffect } from "react";
import "./App.css";

/**
 * PUBLIC_INTERFACE
 * DetectedMatches component fetches active voice matches from the backend
 * and displays them in a clear tabular format, showing user/enrollment,
 * similarity score, chunk/media reference, and timestamp.
 */
function DetectedMatches() {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Fetch matches from backend
  // PUBLIC_INTERFACE
  const fetchMatches = async () => {
    setLoading(true);
    setError("");
    try {
      let apiBase = process.env.REACT_APP_BACKEND_URL;
      if (!apiBase) {
        if (window.location.hostname !== "localhost") {
          apiBase = window.location.origin.replace(/:3000\b/, ":3001");
        } else {
          apiBase = "http://localhost:3001";
        }
      }
      const url = `${apiBase}/matches/active`;
      const response = await fetch(url);
      if (!response.ok) {
        setError("Error fetching detected matches.");
        setMatches([]);
        setLoading(false);
        return;
      }
      const data = await response.json();
      setMatches(Array.isArray(data) ? data : []);
    } catch {
      setError("Could not connect to backend.");
      setMatches([]);
    }
    setLoading(false);
  };

  // Fetch on mount; poll every 15s for live updates
  useEffect(() => {
    fetchMatches();
    const interval = setInterval(fetchMatches, 15000);
    return () => clearInterval(interval);
    // eslint-disable-next-line
  }, []);

  return (
    <section style={{ marginTop: "60px", marginBottom: "60px" }}>
      <div className="subtitle">Detected Matches</div>
      <div className="description">
        Voice matches found in monitored media are listed here. Higher
        similarity scores indicate stronger voice identity match.
      </div>
      {loading && (
        <div className="upload-message uploading">
          Loading detected matches...
        </div>
      )}
      {error && !loading && (
        <div className="upload-message error">{error}</div>
      )}
      {!loading && matches.length === 0 && !error && (
        <div className="upload-message">No active matches found.</div>
      )}
      {!loading && matches.length > 0 && (
        <div
          style={{
            marginTop: "30px",
            background: "rgba(0,255,255,0.04)",
            border: "1px solid var(--border-color)",
            borderRadius: 7,
            padding: 20,
            maxWidth: 730,
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          <table
            style={{
              width: "100%",
              color: "var(--text-color)",
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr style={{ color: "var(--base-light)" }}>
                <th
                  style={{
                    textAlign: "left",
                    paddingBottom: 8,
                    fontWeight: 600,
                  }}
                >
                  User / Enrollment ID
                </th>
                <th
                  style={{ textAlign: "left", paddingBottom: 8, fontWeight: 600 }}
                >
                  Score
                </th>
                <th
                  style={{ textAlign: "left", paddingBottom: 8, fontWeight: 600 }}
                >
                  Media/Chunk
                </th>
                <th
                  style={{ textAlign: "left", paddingBottom: 8, fontWeight: 600 }}
                >
                  Timestamp
                </th>
              </tr>
            </thead>
            <tbody>
              {matches
                .slice() // copy before reverse
                .reverse()
                .map((match, idx) => (
                  <tr
                    key={idx}
                    style={{
                      background:
                        idx % 2 === 0
                          ? "rgba(255,255,255,0.021)"
                          : "rgba(255,255,255,0.05)",
                    }}
                  >
                    <td style={{ padding: "7px 10px 7px 0", fontFamily: "monospace" }}>
                      {match.matched_user_id}
                    </td>
                    <td style={{ padding: "7px 6px" }}>
                      {typeof match.score === "number"
                        ? match.score.toFixed(3)
                        : "N/A"}
                    </td>
                    <td style={{ padding: "7px 6px", fontFamily: "monospace" }}>
                      {match.chunk_filename}
                    </td>
                    <td style={{ padding: "7px 6px" }}>
                      <span
                        style={{
                          fontSize: "0.98rem",
                          fontFamily: "monospace",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {match.timestamp
                          ? new Date(match.timestamp).toLocaleString()
                          : "-"}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          <div
            style={{
              fontSize: "0.97rem",
              color: "var(--text-secondary)",
              marginTop: "11px",
            }}
          >
            Most recent matches appear at the <b>bottom</b>.<br />
            <span style={{ color: "var(--base-light)" }}>
              Score range: 0.0–1.0
            </span>
            &nbsp;— higher is a closer match.
          </div>
        </div>
      )}
    </section>
  );
}

export default DetectedMatches;
