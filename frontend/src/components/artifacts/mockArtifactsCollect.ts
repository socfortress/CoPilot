import type { ArtifactParameter, CollectResult } from "@/types/artifacts.d"

export const MOCK_SELECTED_ARTIFACT_PARAMETERS: ArtifactParameter[] = [
	{
		name: "ProcessRegex",
		description: "Regex to filter process names (e.g. ^svchost$). Leave as '.' for all processes.",
		type: "regex",
		default: "."
	},
	{
		name: "Length",
		description: "Maximum number of results to return per collection.",
		type: "int",
		default: "1024"
	},
	{
		name: "KeyPath",
		description: "Registry key path to enumerate (Windows paths use backslashes).",
		type: "string",
		default: "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
	},
	{
		name: "IncludePrivate",
		description: "Include private memory regions when dumping process memory.",
		type: "bool",
		default: false
	}
]

export const MOCK_PARAMETER_VALUES: Record<string, string> = {
	ProcessRegex: ".",
	Length: "1024",
	KeyPath: "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
}

export const MOCK_COLLECT_LIST: CollectResult[] = [
	{
		___id: "mock-collect-netstat-1",
		Pid: 4312,
		Name: "Velociraptor.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "ESTAB",
		"Laddr.IP": "192.168.200.3",
		"Laddr.Port": 49876,
		"Raddr.IP": "5.161.59.220",
		"Raddr.Port": 8000,
		Timestamp: "2023-11-08T06:27:07Z"
	},
	{
		___id: "mock-collect-netstat-2",
		Pid: 2172,
		Name: "wazuh-agent.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "ESTAB",
		"Laddr.IP": "192.168.200.3",
		"Laddr.Port": 50109,
		"Raddr.IP": "5.161.59.220",
		"Raddr.Port": 1514,
		Timestamp: "2023-11-10T17:58:50Z"
	},
	{
		___id: "mock-collect-netstat-3",
		Pid: 928,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 135,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:23Z"
	},
	{
		___id: "mock-collect-pslist-1",
		Name: "winlogon.exe",
		PebBaseAddress: "0xff437be000",
		Pid: 580,
		ImagePathName: "C:\\Windows\\system32\\winlogon.exe",
		CommandLine: "winlogon.exe",
		CurrentDirectory: "C:\\Windows\\system32\\",
		Env: {
			COMPUTERNAME: "WIN-HFOU106TD7K",
			USERNAME: "SYSTEM",
			windir: "C:\\Windows"
		}
	},
	{
		___id: "mock-collect-pslist-2",
		Name: "lsass.exe",
		PebBaseAddress: "0xc168a3a000",
		Pid: 680,
		ImagePathName: "C:\\Windows\\system32\\lsass.exe",
		CommandLine: "C:\\Windows\\system32\\lsass.exe",
		CurrentDirectory: "C:\\Windows\\system32\\",
		Env: {
			COMPUTERNAME: "WIN-HFOU106TD7K",
			USERNAME: "SYSTEM",
			windir: "C:\\Windows"
		}
	}
]

export function applyMockArtifactParameters(): {
	parameters: ArtifactParameter[]
	parameterValues: Record<string, string>
} {
	return {
		parameters: MOCK_SELECTED_ARTIFACT_PARAMETERS,
		parameterValues: { ...MOCK_PARAMETER_VALUES }
	}
}

export function applyMockCollectList(): CollectResult[] {
	return MOCK_COLLECT_LIST.map(item => ({ ...item }))
}
