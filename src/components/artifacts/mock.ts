const collectResult = [
	{
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
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "192.168.200.3",
		"Laddr.Port": 139,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 344,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 3389,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:28Z"
	},
	{
		Pid: 540,
		Name: "wininit.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49664,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:23Z"
	},
	{
		Pid: 1188,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49665,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:28Z"
	},
	{
		Pid: 680,
		Name: "lsass.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49666,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 464,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49667,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:33Z"
	},
	{
		Pid: 464,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49668,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:33Z"
	},
	{
		Pid: 1524,
		Name: "spoolsv.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49670,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:55Z"
	},
	{
		Pid: 660,
		Name: "services.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49676,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:33:00Z"
	},
	{
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
		Pid: 464,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "TCP",
		Status: "ESTAB",
		"Laddr.IP": "192.168.200.3",
		"Laddr.Port": 49964,
		"Raddr.IP": "20.7.1.246",
		"Raddr.Port": 443,
		Timestamp: "2023-11-09T08:38:11Z"
	},
	{
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
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 445,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:58Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 5357,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 5985,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:58Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 47001,
		"Raddr.IP": "0.0.0.0",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:56Z"
	},
	{
		Pid: 928,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 135,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:23Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 445,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:58Z"
	},
	{
		Pid: 344,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 3389,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:28Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 5357,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 5985,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:58Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 47001,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:56Z"
	},
	{
		Pid: 540,
		Name: "wininit.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49664,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:23Z"
	},
	{
		Pid: 1188,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49665,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:28Z"
	},
	{
		Pid: 680,
		Name: "lsass.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49666,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 464,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49667,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:33Z"
	},
	{
		Pid: 464,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49668,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:33Z"
	},
	{
		Pid: 1524,
		Name: "spoolsv.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49670,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:55Z"
	},
	{
		Pid: 660,
		Name: "services.exe",
		Family: "IPv6",
		Type: "TCP",
		Status: "LISTEN",
		"Laddr.IP": "::",
		"Laddr.Port": 49676,
		"Raddr.IP": "::",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:33:00Z"
	},
	{
		Pid: 2140,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 123,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:56Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "192.168.200.3",
		"Laddr.Port": 137,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 4,
		Name: "System",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "192.168.200.3",
		"Laddr.Port": 138,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 344,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 3389,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:28Z"
	},
	{
		Pid: 2384,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 3702,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 2384,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 3702,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 1424,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 5353,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 1424,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 5355,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-13T20:35:42Z"
	},
	{
		Pid: 2384,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "0.0.0.0",
		"Laddr.Port": 49866,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 464,
		Name: "svchost.exe",
		Family: "IPv4",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "127.0.0.1",
		"Laddr.Port": 50471,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:59Z"
	},
	{
		Pid: 2140,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 123,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:56Z"
	},
	{
		Pid: 344,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 3389,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:28Z"
	},
	{
		Pid: 2384,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 3702,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 2384,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 3702,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	},
	{
		Pid: 1424,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 5353,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:31Z"
	},
	{
		Pid: 1424,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 5355,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-13T20:35:42Z"
	},
	{
		Pid: 2384,
		Name: "svchost.exe",
		Family: "IPv6",
		Type: "UDP",
		Status: "",
		"Laddr.IP": "::",
		"Laddr.Port": 49867,
		"Raddr.IP": "",
		"Raddr.Port": 0,
		Timestamp: "2023-11-07T16:32:57Z"
	}
]

const commandResult = [
	{
		Stdout: "\r\n\r\nAccountType : 512\r\nCaption     : WIN-HFOU106TD7K\\Administrator\r\nDomain      : WIN-HFOU106TD7K\r\nSID         : S-1-5-21-1287727892-3649796646-2502983199-500\r\nFullName    : \r\nName        : Administrator\r\n\r\nAccountType : 512\r\nCaption     : WIN-HFOU106TD7K\\DefaultAccount\r\nDomain      : WIN-HFOU106TD7K\r\nSID         : S-1-5-21-1287727892-3649796646-2502983199-503\r\nFullName    : \r\nName        : DefaultAccount\r\n\r\nAccountType : 512\r\nCaption     : WIN-HFOU106TD7K\\Guest\r\nDomain      : WIN-HFOU106TD7K\r\nSID         : S-1-5-21-1287727892-3649796646-2502983199-501\r\nFullName    : \r\nName        : Guest\r\n\r\nAccountType : 512\r\nCaption     : WIN-HFOU106TD7K\\WDAGUtilityAccount\r\nDomain      : WIN-HFOU106TD7K\r\nSID         : S-1-5-21-1287727892-3649796646-2502983199-504\r\nFullName    : \r\nName        : WDAGUtilityAccount\r\n\r\n\r\n\r\n",
		Stderr: '#< CLIXML\r\n<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj></Objs>',
		ReturnCode: 0,
		Complete: true
	}
]

const quarantineResult = [
	{
		Time: "2023-11-14T21:03:03Z",
		Result: "VelociraptorQuarantine IPSec policy removed."
	},
	{
		Time: "2023-11-14T21:03:03Z",
		Result: "VelociraptorQuarantine IPSec policy created."
	},
	{
		Time: "2023-11-14T21:03:03Z",
		Result: "Entry added: netsh ipsec static add filter filterlist=VelociraptorQuarantine PermitFilterList srcaddr=me srcport=0 dstaddr=velo.socfortress.co dstport=8000 protocol=tcp mirrored=yes description=VelociraptorFrontEnd"
	},
	{
		Time: "2023-11-14T21:03:04Z",
		Result: "Entry added: netsh ipsec static add filter filterlist=VelociraptorQuarantine PermitFilterList srcaddr=me srcport=0 dstaddr=any dstport=53 protocol=udp mirrored=yes description=DNS"
	},
	{
		Time: "2023-11-14T21:03:04Z",
		Result: "Entry added: netsh ipsec static add filter filterlist=VelociraptorQuarantine PermitFilterList srcaddr=me srcport=0 dstaddr=any dstport=53 protocol=tcp mirrored=yes description=DNS TCP"
	},
	{
		Time: "2023-11-14T21:03:04Z",
		Result: "Entry added: netsh ipsec static add filter filterlist=VelociraptorQuarantine PermitFilterList srcaddr=me srcport=68 dstaddr=any dstport=67 protocol=udp mirrored=yes description=DHCP"
	},
	{
		Time: "2023-11-14T21:03:04Z",
		Result: "Entry added: netsh ipsec static add filter filterlist=VelociraptorQuarantine BlockFilterList srcaddr=any dstaddr=any mirrored=yes description=All other traffic"
	},
	{
		Time: "2023-11-14T21:03:04Z",
		Result: "FilterAction added: netsh ipsec static add filteraction name=VelociraptorQuarantine PermitAction action=Permit"
	},
	{
		Time: "2023-11-14T21:03:04Z",
		Result: "FilterAction added: netsh ipsec static add filteraction name=VelociraptorQuarantine BlockAction action=Block"
	},
	{
		Time: "2023-11-14T21:03:05Z",
		Result: "Rule added: netsh ipsec static add rule name=VelociraptorQuarantine PermitRule policy=VelociraptorQuarantine filterlist=VelociraptorQuarantine PermitFilterList filteraction=VelociraptorQuarantine PermitAction"
	},
	{
		Time: "2023-11-14T21:03:05Z",
		Result: "Rule added: netsh ipsec static add rule name=VelociraptorQuarantine BlockRule policy=VelociraptorQuarantine filterlist=VelociraptorQuarantine BlockFilterList filteraction=VelociraptorQuarantine BlockAction"
	},
	{
		Time: "2023-11-14T21:03:05Z",
		Result: "VelociraptorQuarantine IPSec policy applied."
	},
	{
		Time: "2023-11-14T21:03:05Z",
		Result: "VelociraptorQuarantine connection test successful."
	}
]

export { collectResult, commandResult, quarantineResult }
