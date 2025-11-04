import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type { Position } from '../types/api'

export function Dashboard() {
  const { data, error, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: apiClient.getPortfolio,
    refetchInterval: 5000, // Poll every 5s
  })

  if (isLoading) {
    return (
      <div className="loading-skeleton">
        <div className="skeleton-row"></div>
        <div className="skeleton-row"></div>
        <div className="skeleton-row"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-message">
        <h3>Error loading portfolio</h3>
        <p>{error instanceof Error ? error.message : 'Unknown error'}</p>
        <button onClick={() => window.location.reload()}>
          Try Again
        </button>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="dashboard">
      <header>
        <h1>Apex Trading Dashboard</h1>
        <div className="portfolio-summary">
          <div className="metric">
            <label>Portfolio Value</label>
            <value>${data.data.total_value.toLocaleString()}</value>
          </div>
          <div className="metric">
            <label>Return</label>
            <value className={data.data.total_return >= 0 ? 'positive' : 'negative'}>
              {data.data.total_return.toFixed(2)}%
            </value>
          </div>
          <div className="metric">
            <label>Drawdown</label>
            <value className="negative">
              {data.data.drawdown_percent.toFixed(2)}%
            </value>
          </div>
        </div>
      </header>

      <section className="positions">
        <h2>Open Positions ({data.data.position_count})</h2>
        <div className="positions-grid">
          {data.data.positions.map((position: Position) => (
            <div key={position.symbol} className="position-card">
              <div className="position-header">
                <span className="symbol">{position.symbol}</span>
                <span className={`side ${position.side.toLowerCase()}`}>
                  {position.side}
                </span>
              </div>
              <div className="position-details">
                <div>Entry: ${position.entry_price.toFixed(2)}</div>
                <div>Current: ${position.current_price.toFixed(2)}</div>
                <div>Size: {position.quantity}</div>
                <div>Leverage: {position.leverage}x</div>
              </div>
              <div className={`pnl ${position.pnl >= 0 ? 'positive' : 'negative'}`}>
                ${position.pnl.toFixed(2)} ({position.pnl_percent.toFixed(2)}%)
              </div>
            </div>
          ))}
        </div>
      </section>

      {data.data.circuit_breaker_level && (
        <div className="circuit-breaker-alert">
          ⚠️ Circuit Breaker Active: Level {data.data.circuit_breaker_level}
        </div>
      )}
    </div>
  )
}