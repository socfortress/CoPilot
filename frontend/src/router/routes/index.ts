import type { RouteRecordRaw } from "vue-router"
import { adminRoutes } from "./admin"
import { agentsRoutes } from "./agents"
import { alertsRoutes } from "./alerts"
import { analystRoutes } from "./analyst"
import { assessmentsRoutes } from "./assessments"
import { authRoutes } from "./auth"
import { connectorsRoutes } from "./connectors"
import { coreRoutes } from "./core"
import { dashboardsRoutes } from "./dashboards"
import { externalServicesRoutes } from "./external-services"
import { fallbackRoutes } from "./fallback"
import { graylogRoutes } from "./graylog"
import { healthcheckRoutes } from "./healthcheck"
import { incidentManagementRoutes } from "./incident-management"
import { indicesRoutes } from "./indices"
import { licenseRoutes } from "./license"
import { reportCreationRoutes } from "./report-creation"
import { settingsRoutes } from "./settings"

export const routes: RouteRecordRaw[] = [
	...coreRoutes,
	...indicesRoutes,
	...connectorsRoutes,
	...agentsRoutes,
	...graylogRoutes,
	...alertsRoutes,
	...dashboardsRoutes,
	...incidentManagementRoutes,
	...analystRoutes,
	...healthcheckRoutes,
	...adminRoutes,
	...externalServicesRoutes,
	...reportCreationRoutes,
	...assessmentsRoutes,
	...licenseRoutes,
	...settingsRoutes,
	...authRoutes,
	...fallbackRoutes
]
