import { execFileSync } from "node:child_process"
import { createServer } from "node:net"
import process from "node:process"
import { fileURLToPath, URL } from "node:url"
import { defineConfig } from "cypress"

/**
 * Browser end-to-end tests for the Customer Portal (#1181). They drive the real portal
 * against a real backend and the disposable e2e MySQL: see cypress/README.md, or just
 * run `pnpm test:e2e`, which starts both servers for you.
 */

const backendDir = fileURLToPath(new URL("../backend", import.meta.url))
const python = process.env.E2E_PYTHON || `${backendDir}/.venv/bin/python`

/** Runs the backend seed shared with tests/e2e/customer_portal_overview_e2e.py. */
function portalSeed(command: "seed" | "cleanup") {
	const output = execFileSync(python, ["tests/e2e/portal_overview_seed.py", command], {
		cwd: backendDir,
		env: { ...process.env, PYTHONPATH: backendDir },
		encoding: "utf8",
		stdio: ["ignore", "pipe", "ignore"]
	})
	return command === "seed" ? JSON.parse(output.trim().split("\n").at(-1) ?? "{}") : null
}

/** An email the backend sent, as the SMTP sink received it. */
interface SinkMessage {
	from: string
	to: string[]
	subject: string
	data: string
}

/**
 * A minimal SMTP server standing in for the deployment's mail relay (#1282): the backend
 * started by scripts/e2e.sh points SMTP_HOST at it, so a spec can check what portal users
 * were emailed. Plain SMTP only (EHLO, MAIL, RCPT, DATA, QUIT): no TLS, no auth.
 */
function startSmtpSink(port: number) {
	const messages: SinkMessage[] = []
	const server = createServer(socket => {
		let buffer = ""
		let inData = false
		let current: SinkMessage = { from: "", to: [], subject: "", data: "" }
		const reply = (line: string) => socket.write(`${line}\r\n`)
		reply("220 e2e-smtp ready")
		socket.on("data", chunk => {
			buffer += chunk.toString("utf8")
			let index = buffer.indexOf("\r\n")
			while (index !== -1) {
				const line = buffer.slice(0, index)
				buffer = buffer.slice(index + 2)
				if (inData) {
					if (line === ".") {
						inData = false
						current.subject = /^Subject: (.*)$/im.exec(current.data)?.[1]?.trim() ?? ""
						messages.push(current)
						current = { from: "", to: [], subject: "", data: "" }
						reply("250 queued")
					} else {
						current.data += `${line.startsWith("..") ? line.slice(1) : line}\n`
					}
				} else {
					const command = line.slice(0, 4).toUpperCase()
					if (command === "EHLO") {
						reply("250-e2e-smtp")
						reply("250 8BITMIME")
					} else if (command === "HELO" || command === "RSET" || command === "NOOP") {
						reply("250 ok")
					} else if (command === "MAIL") {
						current.from = line.slice(10).trim()
						reply("250 ok")
					} else if (command === "RCPT") {
						current.to.push(line.slice(8).trim().replace(/^<|>$/g, ""))
						reply("250 ok")
					} else if (command === "DATA") {
						inData = true
						reply("354 end with .")
					} else if (command === "QUIT") {
						reply("221 bye")
						socket.end()
					} else {
						reply("250 ok")
					}
				}
				index = buffer.indexOf("\r\n")
			}
		})
		socket.on("error", () => {})
	})
	server.listen(port, "127.0.0.1")
	return messages
}

export default defineConfig({
	e2e: {
		baseUrl: process.env.CYPRESS_BASE_URL || "http://localhost:3101",
		specPattern: "cypress/e2e/**/*.cy.ts",
		supportFile: "cypress/support/e2e.ts",
		video: false,
		defaultCommandTimeout: 15000,
		setupNodeEvents(on) {
			const smtp = startSmtpSink(Number(process.env.E2E_SMTP_PORT || 2526))
			on("task", {
				"portal:seed": () => portalSeed("seed"),
				"portal:cleanup": () => portalSeed("cleanup"),
				"smtp:messages": () => [...smtp],
				"smtp:clear": () => {
					smtp.splice(0, smtp.length)
					return null
				}
			})
		}
	}
})
