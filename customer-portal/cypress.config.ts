import { execFileSync } from "node:child_process"
import { createServer as createHttpServer } from "node:http"
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

/** Points the VirusTotal and OpenCTI connectors at the fake below and puts IOCs on an alert of A (#1318). */
function threatIntelSeed(command: "connect" | "disconnect", baseUrl = "") {
	const output = execFileSync(python, ["tests/e2e/portal_threat_intel_seed.py", command, baseUrl], {
		cwd: backendDir,
		env: { ...process.env, PYTHONPATH: backendDir },
		encoding: "utf8",
		stdio: ["ignore", "pipe", "ignore"]
	})
	return command === "connect" ? JSON.parse(output.trim().split("\n").at(-1) ?? "{}") : null
}

/** A request the backend sent to the fake Threat Intel. */
interface ThreatIntelRequest {
	method: string
	path: string
	apiKey: string | null
	/** OpenCTI only: the value it was asked about. */
	value: string | null
}

const KNOWN_IP = "45.155.205.233"

/**
 * VirusTotal's v3 lookups and OpenCTI's GraphQL endpoint on one localhost port (#1318), standing in
 * for the real ones: the backend is pointed at it by `ti:connect`. It knows one address; anything
 * else is not found. Its OpenCTI answer carries a TLP:RED report the portal must never show.
 */
function startThreatIntelFake(port: number) {
	const requests: ThreatIntelRequest[] = []
	const send = (res: import("node:http").ServerResponse, status: number, body: unknown) => {
		res.writeHead(status, { "content-type": "application/json" })
		res.end(JSON.stringify(body))
	}
	const server = createHttpServer((req, res) => {
		let raw = ""
		req.on("data", chunk => {
			raw += chunk
		})
		req.on("end", () => {
			const path = (req.url ?? "").split("?")[0]
			const apiKey = (req.headers["x-apikey"] as string | undefined) ?? (req.headers.authorization ?? null)
			if (path === "/graphql" && req.method === "POST") {
				const value: string = JSON.parse(raw || "{}")?.variables?.filters?.filters?.[0]?.values?.[0] ?? ""
				requests.push({ method: "POST", path, apiKey, value })
				const edges =
					value === KNOWN_IP
						? [
								{
									node: {
										entity_type: "IPv4-Addr",
										observable_value: KNOWN_IP,
										x_opencti_score: 40,
										objectLabel: [{ value: "botnet" }],
										objectMarking: [{ definition: "TLP:GREEN" }],
										indicators: {
											edges: [
												{
													node: {
														name: "Botnet C2 server",
														x_opencti_score: 80,
														valid_until: "2027-01-01T00:00:00.000Z",
														revoked: false,
														objectMarking: [{ definition: "TLP:AMBER" }]
													}
												}
											]
										},
										reports: {
											edges: [
												{ node: { name: "Botnet weekly", published: "2026-10-01T00:00:00.000Z", objectMarking: [] } },
												{
													node: {
														name: "Restricted partner report",
														published: null,
														objectMarking: [{ definition: "TLP:RED" }]
													}
												}
											]
										}
									}
								}
							]
						: []
				return send(res, 200, { data: { stixCyberObservables: { edges } } })
			}
			requests.push({ method: req.method ?? "", path, apiKey, value: null })
			if (req.method === "GET" && path === `/api/v3/ip_addresses/${KNOWN_IP}`) {
				return send(res, 200, {
					data: {
						id: KNOWN_IP,
						type: "ip_address",
						attributes: {
							last_analysis_stats: { malicious: 9, suspicious: 0, harmless: 61, undetected: 24 },
							reputation: -55,
							last_analysis_date: 1761638400,
							tags: ["scanner"],
							country: "NL",
							as_owner: "Example Hosting"
						}
					}
				})
			}
			return send(res, 404, { error: { code: "NotFoundError" } })
		})
	})
	server.listen(port, "127.0.0.1")
	return requests
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
			const threatIntelPort = Number(process.env.E2E_TI_PORT || 2527)
			const threatIntel = startThreatIntelFake(threatIntelPort)
			on("task", {
				"portal:seed": () => portalSeed("seed"),
				"portal:cleanup": () => portalSeed("cleanup"),
				"smtp:messages": () => [...smtp],
				"smtp:clear": () => {
					smtp.splice(0, smtp.length)
					return null
				},
				"ti:connect": () => threatIntelSeed("connect", `http://127.0.0.1:${threatIntelPort}`),
				"ti:disconnect": () => threatIntelSeed("disconnect"),
				"ti:requests": () => [...threatIntel],
				"ti:clear": () => {
					threatIntel.splice(0, threatIntel.length)
					return null
				}
			})
		}
	}
})
