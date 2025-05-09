export const techniques = [
	{
		technique_id: "T1071",
		technique_name: "Application Layer Protocol",
		count: 99423,
		last_seen: "2025-05-09T16:02:20.205496Z",
		tactics: [
			{
				id: "x-mitre-tactic--f72804c5-f15a-449e-a5da-2eecd181f813",
				name: "Command and Control",
				short_name: "command-and-control"
			}
		]
	},
	{
		technique_id: "T1565.001",
		technique_name: "Stored Data Manipulation",
		count: 47,
		last_seen: "2025-05-09T16:02:20.205614Z",
		tactics: [
			{
				id: "x-mitre-tactic--5569339b-94c2-49ee-afb3-2222936582c8",
				name: "Impact",
				short_name: "impact"
			}
		]
	},
	{
		technique_id: "T1560",
		technique_name: "Archive Collected Data",
		count: 25,
		last_seen: "2025-05-09T16:02:20.205925Z",
		tactics: [
			{
				id: "x-mitre-tactic--d108ce10-2419-4cf9-a774-46161d6c6cfe",
				name: "Collection",
				short_name: "collection"
			}
		]
	},
	{
		technique_id: "T1078",
		technique_name: "Valid Accounts",
		count: 16,
		last_seen: "2025-05-09T16:02:20.206013Z",
		tactics: [
			{
				id: "x-mitre-tactic--5bc1d813-693e-4823-9961-abf9af4b0e92",
				name: "Persistence",
				short_name: "persistence"
			},
			{
				id: "x-mitre-tactic--5e29b093-294e-49e9-a803-dab3d73b77dd",
				name: "Privilege Escalation",
				short_name: "privilege-escalation"
			},
			{
				id: "x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
				name: "Defense Evasion",
				short_name: "defense-evasion"
			},
			{
				id: "x-mitre-tactic--ffd5bcee-6e16-4dd2-8eca-7b3beedf33ca",
				name: "Initial Access",
				short_name: "initial-access"
			}
		]
	},
	{
		technique_id: "T1222",
		technique_name: "File and Directory Permissions Modification",
		count: 10,
		last_seen: "2025-05-09T16:02:20.206062Z",
		tactics: [
			{
				id: "x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
				name: "Defense Evasion",
				short_name: "defense-evasion"
			}
		]
	},
	{
		technique_id: "T1543",
		technique_name: "Create or Modify System Process",
		count: 9,
		last_seen: "2025-05-09T16:02:20.206100Z",
		tactics: [
			{
				id: "x-mitre-tactic--5bc1d813-693e-4823-9961-abf9af4b0e92",
				name: "Persistence",
				short_name: "persistence"
			},
			{
				id: "x-mitre-tactic--5e29b093-294e-49e9-a803-dab3d73b77dd",
				name: "Privilege Escalation",
				short_name: "privilege-escalation"
			}
		]
	},
	{
		technique_id: "T1078",
		technique_name: "Valid Accounts, Remote Services",
		count: 2,
		last_seen: "2025-05-09T16:02:20.206137Z",
		tactics: [
			{
				id: "x-mitre-tactic--5bc1d813-693e-4823-9961-abf9af4b0e92",
				name: "Persistence",
				short_name: "persistence"
			},
			{
				id: "x-mitre-tactic--5e29b093-294e-49e9-a803-dab3d73b77dd",
				name: "Privilege Escalation",
				short_name: "privilege-escalation"
			},
			{
				id: "x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
				name: "Defense Evasion",
				short_name: "defense-evasion"
			},
			{
				id: "x-mitre-tactic--ffd5bcee-6e16-4dd2-8eca-7b3beedf33ca",
				name: "Initial Access",
				short_name: "initial-access"
			}
		]
	},
	{
		technique_id: "T1021",
		technique_name: "Valid Accounts, Remote Services",
		count: 2,
		last_seen: "2025-05-09T16:02:20.206170Z",
		tactics: [
			{
				id: "x-mitre-tactic--7141578b-e50b-4dcc-bfa4-08a8dd689e9e",
				name: "Lateral Movement",
				short_name: "lateral-movement"
			}
		]
	},
	{
		technique_id: "T1110.001",
		technique_name: "Password Guessing",
		count: 2,
		last_seen: "2025-05-09T16:02:20.206205Z",
		tactics: [
			{
				id: "x-mitre-tactic--2558fd61-8c75-4730-94c4-11926db2a263",
				name: "Credential Access",
				short_name: "credential-access"
			}
		]
	},
	{
		technique_id: "T1562.001",
		technique_name: "Disable or Modify Tools",
		count: 2,
		last_seen: "2025-05-09T16:02:20.206239Z",
		tactics: [
			{
				id: "x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
				name: "Defense Evasion",
				short_name: "defense-evasion"
			}
		]
	},
	{
		technique_id: "T1046",
		technique_name: "Network Service Discovery",
		count: 1,
		last_seen: "2025-05-09T16:02:20.206271Z",
		tactics: [
			{
				id: "x-mitre-tactic--c17c5845-175e-4421-9713-829d0573dbc9",
				name: "Discovery",
				short_name: "discovery"
			}
		]
	},
	{
		technique_id: "T1548.003",
		technique_name: "Sudo and Sudo Caching",
		count: 1,
		last_seen: "2025-05-09T16:02:20.206307Z",
		tactics: [
			{
				id: "x-mitre-tactic--5e29b093-294e-49e9-a803-dab3d73b77dd",
				name: "Privilege Escalation",
				short_name: "privilege-escalation"
			},
			{
				id: "x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
				name: "Defense Evasion",
				short_name: "defense-evasion"
			}
		]
	}
]
