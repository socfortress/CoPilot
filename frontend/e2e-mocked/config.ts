import process from "node:process"

/**
 * Port Vite is started on for the mocked suite.
 *
 * Deliberately not 5173: an ordinary `pnpm dev` left over from other work would be
 * reused by Playwright, and on macOS the real-backend suite already fights AirPlay
 * for 5000. A port of its own keeps the two suites from colliding.
 */
export const PORT = Number(process.env.E2E_MOCK_PORT ?? 5273)

export const BASE_URL = process.env.E2E_MOCK_BASE_URL ?? `http://127.0.0.1:${PORT}`
