import agents from "./endpoints/agents"
import alerts from "./endpoints/alerts"
import auth from "./endpoints/auth"
import cases from "./endpoints/cases"
import caseTemplates from "./endpoints/caseTemplates"
import portal from "./endpoints/portal"
import reports from "./endpoints/reports"
import siem from "./endpoints/siem"
import totp from "./endpoints/totp"

export default {
	auth,
	agents,
	alerts,
	cases,
	caseTemplates,
	siem,
	portal,
	reports,
	totp
}
