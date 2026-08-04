/**
 * Runtime configuration, read by the app at boot before the bundle loads.
 *
 * In a container this file is regenerated from environment variables on every start by
 * build/docker-entrypoint.d/91-copilot-runtime-config.sh, which is what lets an operator running
 * the prebuilt image retarget the user-menu links without rebuilding the frontend.
 *
 * This checked-in copy is the no-override default: it ships with the bundle so `pnpm dev` and any
 * non-Docker deployment serve a real file instead of a 404. Keep it empty — the actual defaults
 * live in src/utils/index.ts, next to the code that consumes them.
 */
window.__COPILOT_CONFIG__ = {}
