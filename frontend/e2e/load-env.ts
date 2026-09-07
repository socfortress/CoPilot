import fs from "node:fs"
import path from "node:path"
import process from "node:process"
import { fileURLToPath } from "node:url"

/**
 * Loads `frontend/.env.e2e` into `process.env`, if it exists.
 *
 * The suite needs an admin credential, and the admin password is generated on the
 * backend's first boot — so without this every run means pasting it on the command
 * line, where it also lands in shell history. The file is gitignored.
 *
 * Values already in the environment WIN, so a one-off
 * `E2E_ADMIN_PASSWORD=… pnpm test:e2e` still overrides the file.
 *
 * Imported for its side effect by both `config.ts` and `seed.ts`: Playwright loads the
 * config in the main process *and* in every worker, and ES modules are cached, so this
 * runs exactly once per process no matter which of them is reached first.
 */
const ENV_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", ".env.e2e")

if (fs.existsSync(ENV_FILE)) {
	for (const line of fs.readFileSync(ENV_FILE, "utf-8").split("\n")) {
		const match = line.match(/^[ \t]*([A-Z0-9_]+)[ \t]*=(.*)$/)
		if (!match) continue

		const [, key, rawValue] = match
		if (process.env[key] !== undefined) continue

		// Strip one layer of matching quotes; a password with a `#` in it must survive,
		// so no comment stripping inside a value.
		process.env[key] = rawValue.trim().replace(/^(["'])([\s\S]*)\1$/, "$2")
	}
}
