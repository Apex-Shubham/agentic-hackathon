import { z } from 'zod'

// Zod schemas for runtime validation
export const PositionSchema = z.object({
  symbol: z.string(),
  side: z.enum(['LONG', 'SHORT']),
  entry_price: z.number(),
  current_price: z.number(),
  quantity: z.number(),
  leverage: z.number(),
  pnl: z.number(),
  pnl_percent: z.number(),
})

export const PortfolioResponseSchema = z.object({
  status: z.enum(['success', 'error']),
  data: z.object({
    total_value: z.number(),
    initial_capital: z.number(),
    total_return: z.number(),
    available_balance: z.number(),
    unrealized_pnl: z.number(),
    drawdown_percent: z.number(),
    position_count: z.number(),
    circuit_breaker_level: z.number().nullable(),
    positions: z.array(PositionSchema),
  }),
})

// TypeScript types inferred from Zod schemas
export type Position = z.infer<typeof PositionSchema>
export type PortfolioResponse = z.infer<typeof PortfolioResponseSchema>

// API error type
export interface ApiError {
  status: 'error'
  message: string
}