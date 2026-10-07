/**
 * One UBA alert and its entity, as SOCFortress UBA returns them through CoPilot's /uba routes.
 * Captured from a lab UBA (customer renamed to the mock's ACME), trimmed to what the pages read.
 */

export const UBA_ALERT_ID = "72cdf138-8f0a-57c6-a066-6832e03dfc98"
export const UBA_ENTITY_KEY = "eb936d60-d268-49bf-9149-1c8bcdf05ef3"
export const UBA_ENTITY_NAME = "CONTOSO\\Administrator"

export const UBA_ALERT = {
	success: true,
	message: "ok",
	alert: {
		id: "72cdf138-8f0a-57c6-a066-6832e03dfc98",
		tenant_id: "ACME",
		entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
		entity_type: "actor",
		entity_name: "CONTOSO\\Administrator",
		opened_at: "2026-10-06T14:14:58.737785Z",
		risk: 107.19756839319372,
		reason: "accumulated risk 107 >= 100",
		rules: ["auth.failed_logons_known_account"],
		update_count: 1,
		last_update_at: "2026-10-06T14:14:58.737785Z",
		verdict: "TRUE_POSITIVE",
		verdict_reason: null,
		verdict_note: null,
		verdict_by: "analyst1 via copilot",
		verdict_at: "2026-10-06T20:53:17.644584Z",
		copilot_alert_id: null
	},
	signals: [
		{
			id: "36363b76-7fd3-4bbf-be05-56d2701f615e",
			rule_id: "wazuh:60154",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T13:36:08.456438Z",
			score: 35.0,
			effective_score: 35.0,
			explanation: "Administrators Group Changed",
			event_class: "security_alert",
			mitre: [],
			evidence: ["6edecdc86ff7493faf2bbeb95bd79baa"],
			native: true,
			suppressed: false
		},
		{
			id: "27999aea-fa14-45bd-926a-bb92194192fb",
			rule_id: "wazuh:60109",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T13:40:08.456438Z",
			score: 10.0,
			effective_score: 10.0,
			explanation: "User account enabled or created",
			event_class: "security_alert",
			mitre: [],
			evidence: ["5390d11689534f00a14ae21284cdab33"],
			native: true,
			suppressed: false
		},
		{
			id: "d215cc83-1efc-4665-9da1-4fef6563f0b9",
			rule_id: "wazuh:60111",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:00:08.456438Z",
			score: 10.0,
			effective_score: 10.0,
			explanation: "User account deleted",
			event_class: "security_alert",
			mitre: [],
			evidence: ["9a0e37adc1a5469e9925747d3bcbc61e"],
			native: true,
			suppressed: false
		},
		{
			id: "002fc24a-83f6-4e16-a0f3-a710043853b4",
			rule_id: "wazuh:60115",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:08:08.456438Z",
			score: 10.0,
			effective_score: 5.0,
			explanation: "User account locked out",
			event_class: "security_alert",
			mitre: [],
			evidence: ["2890bf85917f4e1f995b99e1a898b347"],
			native: true,
			suppressed: false
		},
		{
			id: "6785b519-b0db-4101-8fad-da6af4bc11df",
			rule_id: "auth.failed_logons_known_account",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:14:58.737785Z",
			score: 10.0,
			effective_score: 10.0,
			explanation: "34 failed logons as CONTOSO\\Administrator from 185.220.101.47 on SRV-FIN-01 in 5 minutes",
			event_class: "auth",
			mitre: ["T1110.001"],
			evidence: ["93cfb25707034402b404d9a81f9654ac"],
			native: false,
			suppressed: false
		},
		{
			id: "9f9ee174-89a7-4147-a357-0763fceb7485",
			rule_id: "auth.brute_force_known_account",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:14:58.737785Z",
			score: 25.0,
			effective_score: 25.0,
			explanation:
				"34 failed logons as CONTOSO\\Administrator from 185.220.101.47 on SRV-FIN-01 in 5 minutes: password guessing",
			event_class: "auth",
			mitre: ["T1110.001"],
			evidence: ["93cfb25707034402b404d9a81f9654ac"],
			native: false,
			suppressed: false
		},
		{
			id: "136edddd-8e11-49f2-9060-7f6fab15473a",
			rule_id: "auth.failures_then_success",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:14:58.737785Z",
			score: 50.0,
			effective_score: 50.0,
			explanation:
				"CONTOSO\\Administrator logged on from 185.220.101.47 on SRV-FIN-01 right after 34 failed attempts from the same source",
			event_class: "auth",
			mitre: ["T1078", "T1110.001"],
			evidence: ["93cfb25707034402b404d9a81f9654ac"],
			native: false,
			suppressed: false
		}
	],
	updates: [
		{
			risk: 182.2,
			time: "2026-10-06T14:14:58.737785+00:00",
			rule_id: "auth.failures_then_success",
			effective: 50.0,
			explanation:
				"CONTOSO\\Administrator logged on from 185.220.101.47 on SRV-FIN-01 right after 34 failed attempts from the same source"
		}
	]
}

export const UBA_ENTITY = {
	success: true,
	message: "ok",
	tenant: "ACME",
	entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
	entity_type: "target",
	entity_name: "CONTOSO\\Administrator",
	risk: 148.68,
	risk_by_rule: [
		{
			rule_id: "auth.failures_then_success",
			signals: 1,
			risk: 40.80021418354045,
			last_signal: "2026-10-06T14:14:58.737785Z",
			native: false
		},
		{
			rule_id: "account.privileged_password_reset",
			signals: 1,
			risk: 30.60780957964215,
			last_signal: "2026-10-06T14:16:32.199323Z",
			native: false
		},
		{
			rule_id: "wazuh:60154",
			signals: 1,
			risk: 28.38272818774215,
			last_signal: "2026-10-06T13:36:08.456438Z",
			native: true
		},
		{
			rule_id: "auth.brute_force_known_account",
			signals: 1,
			risk: 20.400107091770224,
			last_signal: "2026-10-06T14:14:58.737785Z",
			native: false
		},
		{
			rule_id: "auth.failed_logons_known_account",
			signals: 1,
			risk: 8.160042836708088,
			last_signal: "2026-10-06T14:14:58.737785Z",
			native: false
		},
		{
			rule_id: "wazuh:60111",
			signals: 1,
			risk: 8.140638745771652,
			last_signal: "2026-10-06T14:00:08.456438Z",
			native: true
		},
		{
			rule_id: "wazuh:60109",
			signals: 1,
			risk: 8.114557186602617,
			last_signal: "2026-10-06T13:40:08.456438Z",
			native: true
		},
		{
			rule_id: "wazuh:60115",
			signals: 1,
			risk: 4.0755474134607494,
			last_signal: "2026-10-06T14:08:08.456438Z",
			native: true
		}
	],
	identity: {
		id: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
		kind: "human",
		display_name: "CONTOSO\\Administrator",
		privileged: true,
		privileged_reasons: ["observed:privileged_hint"],
		shadow: true,
		tags: [],
		created_at: "2026-10-06T14:28:08.606749Z",
		enabled: null,
		account_created_at: null,
		deleted_at: null,
		attr_source: {},
		aliases: [
			{
				type: "netbios_sam",
				value: "CONTOSO\\administrator",
				source: "observed",
				confidence: 1.0,
				last_seen: "2026-10-06T14:29:13.852778Z"
			},
			{
				type: "sid",
				value: "S-1-5-21-3623811015-3361044348-30300820-500",
				source: "observed",
				confidence: 1.0,
				last_seen: "2026-10-06T14:29:13.852775Z"
			}
		],
		memberships: []
	},
	host: null,
	alerts: [
		{
			id: "72cdf138-8f0a-57c6-a066-6832e03dfc98",
			tenant_id: "ACME",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_type: "actor",
			entity_name: "CONTOSO\\Administrator",
			opened_at: "2026-10-06T14:14:58.737785Z",
			risk: 107.19756839319372,
			reason: "accumulated risk 107 >= 100",
			rules: ["auth.failed_logons_known_account"],
			update_count: 1,
			last_update_at: "2026-10-06T14:14:58.737785Z",
			verdict: "TRUE_POSITIVE",
			verdict_reason: null,
			verdict_note: null,
			verdict_by: "analyst1 via copilot",
			verdict_at: "2026-10-06T20:53:17.644584Z",
			copilot_alert_id: null
		}
	],
	suppressions: [
		{
			tenant_id: "ACME",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			rule_id: "auth.failures_then_success",
			until: "2026-11-05T20:25:47.054955Z",
			reason: "added by analyst1 via copilot",
			source: "api:analyst1 via copilot",
			created_at: "2026-10-06T20:25:47.085375Z",
			active: true
		}
	]
}

export const UBA_RISK_HISTORY = {
	success: true,
	message: "ok",
	entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
	step: "1h",
	alert_threshold: 100.0,
	points: [
		{
			time: "2026-10-05T13:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T14:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T15:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T16:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T17:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T18:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T19:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T20:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T21:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T22:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-05T23:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T00:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T01:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T02:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T03:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T04:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T05:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T06:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T07:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T08:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T09:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T10:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T11:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T12:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T13:00:00Z",
			risk: 0.0,
			native: 0.0
		},
		{
			time: "2026-10-06T14:00:00Z",
			risk: 44.83,
			native: 44.83
		},
		{
			time: "2026-10-06T15:00:00Z",
			risk: 180.9,
			native: 59.27
		},
		{
			time: "2026-10-06T16:00:00Z",
			risk: 179.16,
			native: 58.7
		},
		{
			time: "2026-10-06T17:00:00Z",
			risk: 177.45,
			native: 58.14
		},
		{
			time: "2026-10-06T18:00:00Z",
			risk: 175.75,
			native: 57.58
		},
		{
			time: "2026-10-06T19:00:00Z",
			risk: 174.06,
			native: 57.03
		},
		{
			time: "2026-10-06T20:00:00Z",
			risk: 172.39,
			native: 56.48
		},
		{
			time: "2026-10-06T21:00:00Z",
			risk: 170.74,
			native: 55.94
		},
		{
			time: "2026-10-06T22:00:00Z",
			risk: 169.11,
			native: 55.41
		},
		{
			time: "2026-10-06T23:00:00Z",
			risk: 167.49,
			native: 54.87
		},
		{
			time: "2026-10-07T00:00:00Z",
			risk: 165.88,
			native: 54.35
		},
		{
			time: "2026-10-07T01:00:00Z",
			risk: 164.29,
			native: 53.83
		},
		{
			time: "2026-10-07T02:00:00Z",
			risk: 162.72,
			native: 53.31
		},
		{
			time: "2026-10-07T03:00:00Z",
			risk: 161.16,
			native: 52.8
		},
		{
			time: "2026-10-07T04:00:00Z",
			risk: 159.62,
			native: 52.3
		},
		{
			time: "2026-10-07T05:00:00Z",
			risk: 158.09,
			native: 51.79
		},
		{
			time: "2026-10-07T06:00:00Z",
			risk: 156.57,
			native: 51.3
		},
		{
			time: "2026-10-07T07:00:00Z",
			risk: 155.07,
			native: 50.81
		},
		{
			time: "2026-10-07T08:00:00Z",
			risk: 153.59,
			native: 50.32
		},
		{
			time: "2026-10-07T09:00:00Z",
			risk: 152.11,
			native: 49.84
		},
		{
			time: "2026-10-07T10:00:00Z",
			risk: 150.66,
			native: 49.36
		},
		{
			time: "2026-10-07T11:00:00Z",
			risk: 149.21,
			native: 48.89
		},
		{
			time: "2026-10-07T11:22:15.476000Z",
			risk: 148.68,
			native: 48.71
		}
	],
	findings: [
		{
			id: "36363b76-7fd3-4bbf-be05-56d2701f615e",
			time: "2026-10-06T13:36:08.456438Z",
			rule_id: "wazuh:60154",
			effective_score: 35.0,
			native: true,
			explanation: "Administrators Group Changed"
		},
		{
			id: "27999aea-fa14-45bd-926a-bb92194192fb",
			time: "2026-10-06T13:40:08.456438Z",
			rule_id: "wazuh:60109",
			effective_score: 10.0,
			native: true,
			explanation: "User account enabled or created"
		},
		{
			id: "d215cc83-1efc-4665-9da1-4fef6563f0b9",
			time: "2026-10-06T14:00:08.456438Z",
			rule_id: "wazuh:60111",
			effective_score: 10.0,
			native: true,
			explanation: "User account deleted"
		},
		{
			id: "002fc24a-83f6-4e16-a0f3-a710043853b4",
			time: "2026-10-06T14:08:08.456438Z",
			rule_id: "wazuh:60115",
			effective_score: 5.0,
			native: true,
			explanation: "User account locked out"
		},
		{
			id: "136edddd-8e11-49f2-9060-7f6fab15473a",
			time: "2026-10-06T14:14:58.737785Z",
			rule_id: "auth.failures_then_success",
			effective_score: 50.0,
			native: false,
			explanation:
				"CONTOSO\\Administrator logged on from 185.220.101.47 on SRV-FIN-01 right after 34 failed attempts from the same source"
		},
		{
			id: "9f9ee174-89a7-4147-a357-0763fceb7485",
			time: "2026-10-06T14:14:58.737785Z",
			rule_id: "auth.brute_force_known_account",
			effective_score: 25.0,
			native: false,
			explanation:
				"34 failed logons as CONTOSO\\Administrator from 185.220.101.47 on SRV-FIN-01 in 5 minutes: password guessing"
		},
		{
			id: "6785b519-b0db-4101-8fad-da6af4bc11df",
			time: "2026-10-06T14:14:58.737785Z",
			rule_id: "auth.failed_logons_known_account",
			effective_score: 10.0,
			native: false,
			explanation: "34 failed logons as CONTOSO\\Administrator from 185.220.101.47 on SRV-FIN-01 in 5 minutes"
		},
		{
			id: "a1296645-c8c3-442c-b6bb-0d7580810977",
			time: "2026-10-06T14:16:32.199323Z",
			rule_id: "account.privileged_password_reset",
			effective_score: 37.5,
			native: false,
			explanation: "CONTOSO\\jdoe reset the password of privileged account CONTOSO\\Administrator"
		}
	],
	alerts: [
		{
			id: "72cdf138-8f0a-57c6-a066-6832e03dfc98",
			opened_at: "2026-10-06T14:14:58.737785Z",
			risk: 107.19756839319372
		}
	]
}

export const UBA_TIMELINE = {
	success: true,
	message: "ok",
	total: 8,
	page: 1,
	page_size: 100,
	signals: [
		{
			id: "a1296645-c8c3-442c-b6bb-0d7580810977",
			rule_id: "account.privileged_password_reset",
			entity_type: "target",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:16:32.199323Z",
			score: 25.0,
			effective_score: 37.5,
			explanation: "CONTOSO\\jdoe reset the password of privileged account CONTOSO\\Administrator",
			event_class: "account_change",
			mitre: ["T1098"],
			evidence: ["1fb5640a084b43249161e48c285f9293"],
			native: false,
			suppressed: false
		},
		{
			id: "6785b519-b0db-4101-8fad-da6af4bc11df",
			rule_id: "auth.failed_logons_known_account",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:14:58.737785Z",
			score: 10.0,
			effective_score: 10.0,
			explanation: "34 failed logons as CONTOSO\\Administrator from 185.220.101.47 on SRV-FIN-01 in 5 minutes",
			event_class: "auth",
			mitre: ["T1110.001"],
			evidence: ["93cfb25707034402b404d9a81f9654ac"],
			native: false,
			suppressed: false
		},
		{
			id: "9f9ee174-89a7-4147-a357-0763fceb7485",
			rule_id: "auth.brute_force_known_account",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:14:58.737785Z",
			score: 25.0,
			effective_score: 25.0,
			explanation:
				"34 failed logons as CONTOSO\\Administrator from 185.220.101.47 on SRV-FIN-01 in 5 minutes: password guessing",
			event_class: "auth",
			mitre: ["T1110.001"],
			evidence: ["93cfb25707034402b404d9a81f9654ac"],
			native: false,
			suppressed: false
		},
		{
			id: "136edddd-8e11-49f2-9060-7f6fab15473a",
			rule_id: "auth.failures_then_success",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:14:58.737785Z",
			score: 50.0,
			effective_score: 50.0,
			explanation:
				"CONTOSO\\Administrator logged on from 185.220.101.47 on SRV-FIN-01 right after 34 failed attempts from the same source",
			event_class: "auth",
			mitre: ["T1078", "T1110.001"],
			evidence: ["93cfb25707034402b404d9a81f9654ac"],
			native: false,
			suppressed: false
		},
		{
			id: "002fc24a-83f6-4e16-a0f3-a710043853b4",
			rule_id: "wazuh:60115",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:08:08.456438Z",
			score: 10.0,
			effective_score: 5.0,
			explanation: "User account locked out",
			event_class: "security_alert",
			mitre: [],
			evidence: ["2890bf85917f4e1f995b99e1a898b347"],
			native: true,
			suppressed: false
		},
		{
			id: "d215cc83-1efc-4665-9da1-4fef6563f0b9",
			rule_id: "wazuh:60111",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T14:00:08.456438Z",
			score: 10.0,
			effective_score: 10.0,
			explanation: "User account deleted",
			event_class: "security_alert",
			mitre: [],
			evidence: ["9a0e37adc1a5469e9925747d3bcbc61e"],
			native: true,
			suppressed: false
		},
		{
			id: "27999aea-fa14-45bd-926a-bb92194192fb",
			rule_id: "wazuh:60109",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T13:40:08.456438Z",
			score: 10.0,
			effective_score: 10.0,
			explanation: "User account enabled or created",
			event_class: "security_alert",
			mitre: [],
			evidence: ["5390d11689534f00a14ae21284cdab33"],
			native: true,
			suppressed: false
		},
		{
			id: "36363b76-7fd3-4bbf-be05-56d2701f615e",
			rule_id: "wazuh:60154",
			entity_type: "actor",
			entity_key: "eb936d60-d268-49bf-9149-1c8bcdf05ef3",
			entity_name: "CONTOSO\\Administrator",
			time: "2026-10-06T13:36:08.456438Z",
			score: 35.0,
			effective_score: 35.0,
			explanation: "Administrators Group Changed",
			event_class: "security_alert",
			mitre: [],
			evidence: ["6edecdc86ff7493faf2bbeb95bd79baa"],
			native: true,
			suppressed: false
		}
	]
}
