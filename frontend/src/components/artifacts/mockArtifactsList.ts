import type { Artifact } from "@/types/artifacts"

export const MOCK_ARTIFACTS_LIST: Artifact[] = [
	{
		name: "Windows.System.Pslist",
		description: "List processes and their basic information including command line and environment.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'windows'",
		parameters: [
			{
				name: "ProcessRegex",
				description: "Regex to filter process names.",
				type: "regex",
				default: "."
			},
			{
				name: "Length",
				description: "Maximum number of results to return.",
				type: "int",
				default: "1024"
			}
		]
	},
	{
		name: "Windows.Network.Netstat",
		description: "Collect network connections using netstat.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'windows'",
		parameters: [
			{
				name: "IPFamily",
				description: "IP family to collect (IPv4, IPv6, or Both).",
				type: "choices",
				default: "Both"
			}
		]
	},
	{
		name: "Windows.Registry.NTUser",
		description: "Collect NTUSER.DAT registry hives for all users.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'windows'"
	},
	{
		name: "Windows.EventLogs.Evtx",
		description: "Collect Windows event logs in Evtx format.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'windows'",
		parameters: [
			{
				name: "VSSAnalysisAge",
				description: "Age in seconds for VSS analysis.",
				type: "int",
				default: "60"
			},
			{
				name: "UploadLogs",
				description: "Upload collected logs to the server.",
				type: "bool",
				default: true
			}
		]
	},
	{
		name: "Linux.Sys.CPUInfo",
		description: "Collect CPU information from /proc/cpuinfo.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'linux'"
	},
	{
		name: "Linux.Network.Netstat",
		description: "Collect network connections on Linux endpoints.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'linux'"
	},
	{
		name: "Generic.Client.Info",
		description: "Collect basic client information including OS, hostname, and agent version.",
		author: "Velociraptor Team",
		precondition: null
	},
	{
		name: "Windows.Memory.ProcessDump",
		description: "Dump process memory for forensic analysis.",
		author: "Mike Cohen",
		precondition: "SELECT OS FROM info() WHERE OS = 'windows'",
		parameters: [
			{
				name: "ProcessRegex",
				description: "Regex to select processes to dump.",
				type: "regex",
				default: "notepad.exe"
			},
			{
				name: "IncludePrivate",
				description: "Include private memory regions.",
				type: "bool",
				default: false
			}
		]
	}
]

export function applyMockArtifactsList(): Artifact[] {
	return MOCK_ARTIFACTS_LIST.map(artifact => ({ ...artifact }))
}
