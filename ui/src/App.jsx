import React, { useEffect, useState } from 'react'

export default function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    const fetchPortfolio = async () => {
      try {
        const res = await fetch('/api/portfolio')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (mounted) setData(json)
      } catch (e) {
        if (mounted) setError(e.message)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    fetchPortfolio()

    const interval = setInterval(fetchPortfolio, 5000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  return (
    <div className="container">
      <header>
        <h1>Apex Trading Dashboard (React)</h1>
      </header>

      <main>
        {loading && <p>Loading portfolio...</p>}
        {error && <p className="error">Error: {error}</p>}
        {data && (
          <section className="card">
            <h2>Portfolio</h2>
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </section>
        )}
      </main>

      <footer>
        <small>Polling every 5s • Uses the backend API at <code>/api/</code></small>
      </footer>
    </div>
  )
}
