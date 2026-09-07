import process from "node:process"
import "./load-env"

/** Port Playwright starts Vite on (and the one `baseURL` is built from). */
export const PORT = Number(process.env.E2E_PORT ?? 5173)

/** Origin the browser talks to. */
export const BASE_URL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:${PORT}`
