// English is the source language: its files define every key (`MessageSchema`), and the other
// languages must carry exactly the same ones (`lang/__tests__/locales.spec.ts`). A new area adds
// its file here and in every language's folder.
import activity from "./activity.json" with { type: "json" }
import agents from "./agents.json" with { type: "json" }
import alerts from "./alerts.json" with { type: "json" }
import audit from "./audit.json" with { type: "json" }
import auth from "./auth.json" with { type: "json" }
import cases from "./cases.json" with { type: "json" }
import common from "./common.json" with { type: "json" }
import dashboards from "./dashboards.json" with { type: "json" }
import eventSearch from "./eventSearch.json" with { type: "json" }
import exposure from "./exposure.json" with { type: "json" }
import navigation from "./navigation.json" with { type: "json" }
import notifications from "./notifications.json" with { type: "json" }
import overview from "./overview.json" with { type: "json" }
import profile from "./profile.json" with { type: "json" }
import reports from "./reports.json" with { type: "json" }
import sla from "./sla.json" with { type: "json" }
import users from "./users.json" with { type: "json" }

export default {
	common,
	navigation,
	auth,
	overview,
	alerts,
	cases,
	agents,
	reports,
	eventSearch,
	dashboards,
	exposure,
	activity,
	sla,
	profile,
	users,
	audit,
	notifications
}
