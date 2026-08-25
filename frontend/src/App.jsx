import React, { useState, useEffect } from 'react';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('global'); // 'global' or 'contests'
  const [leaderboardData, setLeaderboardData] = useState({ standings: [], contests: [] });
  const [contestsIndex, setContestsIndex] = useState([]);
  const [selectedContestId, setSelectedContestId] = useState('');
  const [contestData, setContestData] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [darkMode, setDarkMode] = useState(true);

  // Thor's Mjölnir Loading Screen Duration (3.5 seconds)
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 3500);
    return () => clearTimeout(timer);
  }, []);

  // Helper function to strip prefix before '=' in handles safely
  const cleanHandle = (handle) => {
    if (!handle || typeof handle !== 'string') return handle || '';
    const parts = handle.split('=');
    return parts.length > 1 ? parts[1] : handle;
  };

  // Fetch Global Leaderboard and Contest Index on mount
  useEffect(() => {
    Promise.all([
      fetch('/leaderboard.json').then(res => {
        if (!res.ok) throw new Error('Global leaderboard.json not found. Run python scripts/compute_scores.py first.');
        return res.json();
      }),
      fetch('/contests/index.json').then(res => {
        if (!res.ok) throw new Error('Contests index.json not found under data/contests/.');
        return res.json();
      })
    ])
      .then(([lbData, indexData]) => {
        const standingsList = lbData?.standings || lbData?.participants || (Array.isArray(lbData) ? lbData : []);
        const contestsList = lbData?.contests || [];
        
        setLeaderboardData({
          standings: Array.isArray(standingsList) ? standingsList : [],
          contests: Array.isArray(contestsList) ? contestsList : []
        });

        const list = indexData?.contests || indexData || [];
        setContestsIndex(Array.isArray(list) ? list : []);
        if (list.length > 0 && !selectedContestId) {
          setSelectedContestId(list[0].id);
        }
      })
      .catch(err => {
        console.error("Data loading error:", err);
        setError(err.message);
      });
  }, []);

  // Fetch specific contest data when user selects a contest
  useEffect(() => {
    if (!selectedContestId || activeTab !== 'contests') {
      setContestData(null);
      return;
    }
    fetch(`/contests/contest_${selectedContestId}.json`)
      .then(res => {
        if (!res.ok) throw new Error(`Failed to load contest data for ID: ${selectedContestId}`);
        return res.json();
      })
      .then(data => {
        setContestData(data || {});
      })
      .catch(err => {
        console.error("Contest loading error:", err);
        setError(err.message);
      });
  }, [selectedContestId, activeTab]);

  // Filter handles dynamically
  const standingsArray = Array.isArray(leaderboardData.standings) ? leaderboardData.standings : [];
  const filteredLeaderboard = standingsArray.filter(row => {
    const handleStr = cleanHandle(row?.handle);
    return handleStr.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const contestStandingsList = contestData?.standings || contestData?.participants || [];
  const filteredContestStandings = Array.isArray(contestStandingsList) ? contestStandingsList.filter(row => {
    const handleStr = cleanHandle(row?.handle);
    return handleStr.toLowerCase().includes(searchQuery.toLowerCase());
  }) : [];

  // Robustly extract problem list (supports problemResults array like A-G or problems object)
  const sampleParticipant = contestStandingsList[0] || {};
  let detectedProblems = [];
  if (sampleParticipant.problemResults && Array.isArray(sampleParticipant.problemResults)) {
    detectedProblems = sampleParticipant.problemResults.map((p, idx) => ({
      key: p.index || idx,
      label: p.index ? `Problem ${p.index}` : `Problem ${idx + 1}`
    }));
  } else if (sampleParticipant.problems && typeof sampleParticipant.problems === 'object') {
    detectedProblems = Object.keys(sampleParticipant.problems).map((pKey, idx) => ({
      key: pKey,
      label: `Problem ${idx + 1}`
    }));
  }

  // Thor's Hammer Cinematic Loading Screen
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="hammer-container">
          <div className="hammer-icon">
            <div className="hammer-head"></div>
            <div className="hammer-handle"></div>
          </div>
        </div>
        <h2 style={{ marginTop: '2.5rem', color: '#f8fafc', letterSpacing: '0.15em', fontWeight: '800', fontSize: '1.25rem' }}>
          ⚡ SUMMONING MJÖLNIR • LOADING CODEMON HQ...
        </h2>
        <p style={{ marginTop: '0.5rem', color: '#94a3b8', fontSize: '0.85rem' }}>Preparing combat league telemetry</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`app-container ${!darkMode ? 'light-mode' : ''}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem' }}>
        <div className="app-card" style={{ padding: '2rem', maxWidth: '400px', textAlign: 'center', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          <h2 style={{ color: '#ef4444', marginBottom: '0.5rem', fontWeight: 800 }}>Codemon System Notice</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`app-container ${!darkMode ? 'light-mode' : ''}`}>
      
      {/* Top Navbar */}
      <header className="app-header">
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '40px', height: '40px', background: 'linear-gradient(to bottom right, #dc2626, #991b1b)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold', boxShadow: '0 10px 15px -3px rgba(220, 38, 38, 0.3)' }}>
              ⚡
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 800, letterSpacing: '0.05em' }}>CODEMON HQ</h1>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Competitive League Archives</p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <nav style={{ display: 'flex', background: 'var(--bg-color)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <button 
                onClick={() => setActiveTab('global')}
                style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', fontWeight: 600, border: 'none', background: activeTab === 'global' ? '#dc2626' : 'transparent', color: activeTab === 'global' ? '#fff' : 'var(--text-secondary)', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s' }}
              >
                Overall Standings
              </button>
              <button 
                onClick={() => setActiveTab('contests')}
                style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', fontWeight: 600, border: 'none', background: activeTab === 'contests' ? '#dc2626' : 'transparent', color: activeTab === 'contests' ? '#fff' : 'var(--text-secondary)', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s' }}
              >
                Contest Archives
              </button>
            </nav>

            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="app-select"
              style={{ cursor: 'pointer', fontWeight: 600 }}
              title="Toggle Light/Dark Mode"
            >
              {darkMode ? '☀️ Light' : '🌙 Dark'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', margin: '2rem auto 0', padding: '0 1.5rem' }}>
        
        {/* Controls Toolbar */}
        <div className="app-card" style={{ padding: '1.25rem 1.5rem', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 900, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#dc2626', display: 'inline-block' }}></span>
              {activeTab === 'global' ? 'Global Season Leaderboard' : 'Select Competition'}
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {activeTab === 'global' 
                ? 'Aggregated performance across all tracked rounds.' 
                : 'Choose a competition below to unlock tactical participant search.'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%', maxWidth: '450px', flexWrap: 'wrap' }}>
            {activeTab === 'contests' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
                <select
                  value={selectedContestId}
                  onChange={(e) => setSelectedContestId(e.target.value)}
                  className="app-select"
                  style={{ flex: 1, minWidth: '185px' }}
                >
                  <option value="" disabled>-- Choose a Competition --</option>
                  {contestsIndex.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name || `Contest ${c.id}`} {c.date ? `(${c.date})` : ''}
                    </option>
                  ))}
                </select>

                {selectedContestId && (
                  <a
                    href={`/contests/contest_${selectedContestId}.json`}
                    download={`contest_${selectedContestId}.json`}
                    target="_blank"
                    rel="noreferrer"
                    className="app-select"
                    style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '0.625rem 0.875rem' }}
                    title="Download JSON file"
                  >
                    📥 JSON
                  </a>
                )}
              </div>
            )}

            {(activeTab === 'global' || selectedContestId) && (
              <input
                type="text"
                placeholder="Search handle..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="app-input"
                style={{ flex: 1, minWidth: '140px' }}
              />
            )}
          </div>
        </div>

        {/* Centralized Table Container */}
        <div className="app-card" style={{ overflow: 'hidden' }}>
          {activeTab === 'global' ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', background: 'var(--table-header-bg)' }}>
                    <th style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', width: '90px' }}>Rank</th>
                    <th style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', textAlign: 'left' }}>Trainer / Handle</th>
                    <th style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)' }}>Total Score</th>
                    {leaderboardData.contests?.map((contest) => (
                      <th key={contest.id} style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)' }} title={contest.name}>
                        {contest.name || `Codemon Contest ${contest.id}`}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody style={{ fontSize: '0.875rem' }}>
                  {filteredLeaderboard.length > 0 ? (
                    filteredLeaderboard.map((row, index) => {
                      const currentRank = row.rank || index + 1;
                      return (
                        <tr key={row.handle || index} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', fontWeight: 600 }}>
                            {currentRank === 1 ? <span style={{ padding: '2px 8px', background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '6px' }}>1</span> :
                             currentRank === 2 ? <span style={{ padding: '2px 8px', background: 'rgba(203, 213, 225, 0.2)', color: '#e2e8f0', border: '1px solid rgba(203, 213, 225, 0.3)', borderRadius: '6px' }}>2</span> :
                             currentRank === 3 ? <span style={{ padding: '2px 8px', background: 'rgba(180, 83, 9, 0.2)', color: '#f59e0b', border: '1px solid rgba(180, 83, 9, 0.3)', borderRadius: '6px' }}>3</span> :
                             currentRank}
                          </td>
                          <td style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', fontWeight: 'bold', color: 'var(--accent-red)', textAlign: 'left' }}>{cleanHandle(row.handle)}</td>
                          <td style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', fontFamily: 'monospace', fontWeight: 'bold' }}>{row.totalScore ?? row.seasonTotal ?? row.score ?? 0}</td>
                          {leaderboardData.contests?.map((contest) => {
                            const contestRecord = row.perContest?.[contest.id];
                            return (
                              <td key={contest.id} style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', fontFamily: 'monospace' }}>
                                {contestRecord ? (
                                  <span style={{ color: '#10b981', fontWeight: 600 }}>
                                    {contestRecord.finalPoints} pts
                                  </span>
                                ) : (
                                  <span style={{ color: 'var(--text-secondary)' }}>-</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={3 + (leaderboardData.contests?.length || 1)} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        No combatants found matching query.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : !selectedContestId ? (
            <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              Please choose a competition from the dropdown above to view standings and problem telemetry.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', background: 'var(--table-header-bg)' }}>
                    <th style={{ padding: '1rem', borderRight: '1px solid var(--border-color)', width: '80px' }}>Rank</th>
                    <th style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', textAlign: 'left' }}>Handle</th>
                    <th style={{ padding: '1rem', borderRight: '1px solid var(--border-color)' }}>Score</th>
                    <th style={{ padding: '1rem', borderRight: '1px solid var(--border-color)' }}>Solved</th>
                    {detectedProblems.length > 0 ? (
                      detectedProblems.map((prob) => (
                        <th key={prob.key} style={{ padding: '1rem', borderRight: '1px solid var(--border-color)', fontFamily: 'monospace' }}>{prob.label}</th>
                      ))
                    ) : (
                      <th style={{ padding: '1rem' }}>Problems</th>
                    )}
                  </tr>
                </thead>
                <tbody style={{ fontSize: '0.875rem' }}>
                  {filteredContestStandings.length > 0 ? (
                    filteredContestStandings.map((row, index) => (
                      <tr key={row.handle || index} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem', borderRight: '1px solid var(--border-color)', fontWeight: 600 }}>{row.rank || index + 1}</td>
                        <td style={{ padding: '1rem 1.5rem', borderRight: '1px solid var(--border-color)', fontWeight: 'bold', color: 'var(--accent-red)', textAlign: 'left' }}>{cleanHandle(row.handle)}</td>
                        <td style={{ padding: '1rem', borderRight: '1px solid var(--border-color)', fontFamily: 'monospace', fontWeight: 'bold' }}>{row.score ?? 0}</td>
                        <td style={{ padding: '1rem', borderRight: '1px solid var(--border-color)', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{row.problemsSolved ?? '-'}</td>
                        
                        {detectedProblems.length > 0 ? (
                          detectedProblems.map(prob => {
                            // Support both problemResults array and problems object
                            const pData = row.problemResults?.find(p => p.index === prob.key) || row.problems?.[prob.key];
                            const isSolved = pData?.solved || (pData?.score > 0);
                            const entryTime = pData?.bestSubmissionTimeSeconds ?? pData?.time;

                            return (
                              <td key={prob.key} style={{ padding: '1rem', borderRight: '1px solid var(--border-color)', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                {isSolved ? (
                                  <span style={{ color: '#10b981', fontWeight: 600 }}>
                                    {entryTime !== undefined && entryTime !== null ? `${entryTime}s` : '✔'}
                                  </span>
                                ) : (
                                  <span style={{ color: '#ef4444', fontWeight: 'bold', fontSize: '1rem' }} title="Not Solved">❌</span>
                                )}
                              </td>
                            );
                          })
                        ) : (
                          <td style={{ padding: '1rem' }}>-</td>
                        )}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4 + (detectedProblems.length || 1)} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        No standings data available for this round.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}