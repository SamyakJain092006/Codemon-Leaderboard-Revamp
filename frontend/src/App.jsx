import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [contests, setContests] = useState([])
  const [selectedContest, setSelectedContest] = useState(null)
  const [standings, setStandings] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchContests()
  }, [])

  const fetchContests = async () => {
    try {
      const res = await fetch('/data/contests/index.json')
      if (!res.ok) throw new Error('Failed to fetch contests')
      const data = await res.json()
      setContests(data.contests || [])
    } catch (err) {
      setError(err.message)
    }
  }

  const fetchStandings = async (contestId) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/data/contests/contest_${contestId}.json`)
      if (!res.ok) throw new Error('Failed to fetch standings')
      const data = await res.json()
      setStandings(data.standings || [])
      setSelectedContest(contestId)
    } catch (err) {
      setError(err.message)
      setStandings([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Codemon Leaderboard</h1>
      </header>
      <main className="main">
        <section className="contests-panel">
          <h2>Contests</h2>
          {error && <div className="error">{error}</div>}
          <ul className="contests-list">
            {contests.map((contest) => (
              <li
                key={contest.id}
                className={selectedContest === contest.id ? 'selected' : ''}
                onClick={() => fetchStandings(contest.id)}
              >
                <span className="contest-name">{contest.name}</span>
                <span className="contest-date">{contest.date}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="standings-panel">
          {selectedContest ? (
            <>
              <div className="standings-header">
                <h2>Standings for Contest {selectedContest}</h2>
                <button onClick={() => setSelectedContest(null)}>Back to Contests</button>
              </div>
              {loading ? (
                <div className="loading">Loading standings...</div>
              ) : (
                <table className="standings-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Handle</th>
                      <th>Score</th>
                      <th>Problems Solved</th>
                    </tr>
                  </thead>
                  <tbody>
                    {standings.map((entry, idx) => (
                      <tr key={entry.handle || idx}>
                        <td>{entry.rank || idx + 1}</td>
                        <td>{entry.handle}</td>
                        <td>{entry.score}</td>
                        <td>{entry.problemsSolved}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          ) : (
            <div className="placeholder">Select a contest to view standings</div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App