import type { MitreTechniqueDetails } from "@/types/mitre.d"

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

export const techniqueResultDetails: MitreTechniqueDetails = {
	description:
		"Adversaries may obtain and abuse credentials of existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion. Compromised credentials may be used to bypass access controls placed on various resources on systems within the network and may even be used for persistent access to remote systems and externally available services, such as VPNs, Outlook Web Access, network devices, and remote desktop.(Citation: volexity_0day_sophos_FW) Compromised credentials may also grant an adversary increased privilege to specific systems or access to restricted areas of the network. Adversaries may choose not to use malware or tools in conjunction with the legitimate access those credentials provide to make it harder to detect their presence.\n\nIn some cases, adversaries may abuse inactive accounts: for example, those belonging to individuals who are no longer part of an organization. Using these accounts may allow the adversary to evade detection, as the original account user will not be present to identify any anomalous activity taking place on their account.(Citation: CISA MFA PrintNightmare)\n\nThe overlap of permissions for local, domain, and cloud accounts across a network of systems is of concern because the adversary may be able to pivot across accounts and systems to reach a high level of access (i.e., domain or enterprise administrator) to bypass access controls set within the enterprise.(Citation: TechNet Credential Theft)",
	name: "Valid Accounts",
	id: "attack-pattern--b17a1a56-e99c-403c-8948-561df0cffe81",
	modified_time: new Date("2023-03-30T21:01:51.631000Z"),
	created_time: new Date("2017-05-31T21:31:00.645000Z"),
	tactics: [
		"x-mitre-tactic--5bc1d813-693e-4823-9961-abf9af4b0e92",
		"x-mitre-tactic--5e29b093-294e-49e9-a803-dab3d73b77dd",
		"x-mitre-tactic--78b23412-0651-46d7-a540-170a1ce8bd5a",
		"x-mitre-tactic--ffd5bcee-6e16-4dd2-8eca-7b3beedf33ca"
	],
	url: "https://attack.mitre.org/techniques/T1078",
	source: "mitre-attack",
	external_id: "T1078",
	references: [
		{
			url: "https://www.cisa.gov/uscert/ncas/alerts/aa22-074a",
			description:
				"Cybersecurity and Infrastructure Security Agency. (2022, March 15). Russian State-Sponsored Cyber Actors Gain Network Access by Exploiting Default Multifactor Authentication Protocols and “PrintNightmare” Vulnerability. Retrieved March 16, 2022.",
			source: "CISA MFA PrintNightmare"
		},
		{
			url: "https://technet.microsoft.com/en-us/library/dn487457.aspx",
			description: "Microsoft. (2016, April 15). Audit Policy Recommendations. Retrieved June 3, 2016.",
			source: "TechNet Audit Policy"
		},
		{
			url: "https://technet.microsoft.com/en-us/library/dn535501.aspx",
			description:
				"Microsoft. (2016, April 15). Attractive Accounts for Credential Theft. Retrieved June 3, 2016.",
			source: "TechNet Credential Theft"
		},
		{
			url: "https://www.volexity.com/blog/2022/06/15/driftingcloud-zero-day-sophos-firewall-exploitation-and-an-insidious-breach/",
			description:
				"Adair, S., Lancaster, T., Volexity Threat Research. (2022, June 15). DriftingCloud: Zero-Day Sophos Firewall Exploitation and an Insidious Breach. Retrieved July 1, 2022.",
			source: "volexity_0day_sophos_FW"
		}
	],
	mitigations: [
		"course-of-action--25dc1ce8-eb55-4333-ae30-a7cb4f5894a1",
		"course-of-action--2a4f6c11-a4a7-4cb9-b0ef-6ae1bb3a718a",
		"course-of-action--90c218c3-fbf8-4830-98a7-e8cfb7eaa485",
		"course-of-action--93e7968a-9074-4eac-8ae9-9f5200ec3317",
		"course-of-action--9bb9e696-bff8-4ae1-9454-961fc7d91d5f",
		"course-of-action--e3388c78-2a8d-47c2-8422-c1398b324462",
		"course-of-action--f9f9e6ef-bc0a-41ad-ba11-0924e5e84c4c"
	],
	subtechnique_of: null,
	techniques: null,
	groups: [
		"intrusion-set--06a11b7e-2a36-47fe-8d3e-82c265df3258",
		"intrusion-set--18854f55-ac7c-4634-bd9a-352dd07613b7",
		"intrusion-set--1c63d4ec-0a75-4daa-b1df-0d11af3d3cc1",
		"intrusion-set--222fbd21-fc4f-4b7e-9f85-0e6e3a76c33f",
		"intrusion-set--2a7914cf-dff3-428d-ab0f-1014d1c28aeb",
		"intrusion-set--3753cc21-2dae-4dfb-8481-d004e74502cc",
		"intrusion-set--381fcf73-60f6-4ab2-9991-6af3cbc35192",
		"intrusion-set--38fd6a28-3353-4f2b-bb2b-459fecd5c648",
		"intrusion-set--44e43fad-ffcb-4210-abcf-eaaed9735f80",
		"intrusion-set--4ca1929c-7d64-4aab-b849-badbfc0c760d",
		"intrusion-set--55033a4d-3ffe-46b2-99b4-2c1541e9ce1c",
		"intrusion-set--5cbe0d3b-6fb1-471f-b591-4b192915116d",
		"intrusion-set--5f3d0238-d058-44a9-8812-3dd1b6741a8c",
		"intrusion-set--6713ab67-e25b-49cc-808d-2b36d4fbc35c",
		"intrusion-set--7113eaa5-ba79-4fb3-b68a-398ee9cd698e",
		"intrusion-set--85403903-15e0-4f9f-9be4-a259ecad4022",
		"intrusion-set--899ce53f-13a0-479b-a0e4-67d46e241542",
		"intrusion-set--8c1f0187-0826-4320-bddc-5f326cfcfe2c",
		"intrusion-set--90784c1e-4aba-40eb-9adf-7556235e6384",
		"intrusion-set--9538b1a4-4120-4e2d-bf59-3b11fcab05a4",
		"intrusion-set--a0cb9370-e39b-44d5-9f50-ef78e412b973",
		"intrusion-set--bef4c620-0787-42a8-a96d-b7eb6e85917c",
		"intrusion-set--c21dd6f1-1364-4a70-a1f7-783080ec34ee",
		"intrusion-set--c93fccb1-e8e8-42cf-ae33-2ad1d183913a",
		"intrusion-set--d0b3393b-3bec-4ba3-bda9-199d30db47b6",
		"intrusion-set--d13c8a7f-740b-4efa-a232-de7d6bb05321",
		"intrusion-set--d8bc9788-4f7d-41a9-9e9d-ee1ea18a8cf7",
		"intrusion-set--dd2d9ca6-505b-4860-a604-233685b802c7",
		"intrusion-set--fb366179-766c-4a4a-afa1-52bff1fd601c",
		"intrusion-set--fbd29c89-18ba-4c2d-b792-51c0adee049f",
		"intrusion-set--fbe9387f-34e6-4828-ac28-3080020c597b",
		"intrusion-set--fd19bd82-1b14-49a1-a176-6cdc46b8a826",
		"intrusion-set--fe98767f-9df8-42b9-83c9-004b1dec8647"
	],
	software: [
		"malware--0efefea5-78da-4022-92bc-d726139e8883",
		"malware--67e6d66b-1b82-4699-b47a-e2efb6268d14",
		"malware--68dca94f-c11d-421e-9287-7c501108e18c",
		"malware--d6e55656-e43f-411f-a7af-45df650471c5",
		"malware--e401d4fe-f0c9-44f0-98e6-f93487678808",
		"malware--f8774023-8021-4ece-9aca-383ac89d2759"
	],
	mitre_detection:
		"Configure robust, consistent account activity audit policies across the enterprise and with externally accessible services.(Citation: TechNet Audit Policy) Look for suspicious account behavior across systems that share accounts, either user, admin, or service accounts. Examples: one account logged into multiple systems simultaneously; multiple accounts logged into the same machine simultaneously; accounts logged in at odd times or outside of business hours. Activity may be from interactive login sessions or process ownership from accounts being used to execute binaries on a remote system as a particular account. Correlate other security systems with login information (e.g., a user has an active login session but has not entered the building or does not have VPN access).\n\nPerform regular audits of domain and local system accounts to detect accounts that may have been created by an adversary for persistence. Checks on these accounts could also include whether default accounts such as Guest have been activated. These audits should also include checks on any appliances and applications for default credentials or SSH keys, and if any are discovered, they should be updated immediately.",
	mitre_version: "2.6",
	deprecated: 1,
	remote_support: 1,
	network_requirements: 1,
	platforms: ["macos", "linux"],
	data_sources: [],
	is_subtechnique: true
}
