import axios from 'axios'
import { PortfolioResponse, PortfolioResponseSchema } from '../types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 5000,
})

export async function getPortfolio(): Promise<PortfolioResponse> {
  const { data } = await api.get<PortfolioResponse>('/portfolio')
  // Validate response at runtime
  return PortfolioResponseSchema.parse(data)
}

// Add more API methods here as needed
export const apiClient = {
  getPortfolio,
}