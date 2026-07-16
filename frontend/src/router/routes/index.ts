import type { RouteRecordRaw } from "vue-router"
import { adminRoutes } from "./admin"
import { agentsRoutes } from "./agents"
import { alertsRoutes } from "./alerts"
import { analystRoutes } from "./analyst"
import { assessmentsRoutes } from "./assessments"
import { authRoutes } from "./auth"
import { connectorsRoutes } from "./connectors"
import { coreRoutes } from "./core"
import { customersRoutes } from "./customers"
import { dashboardsRoutes } from "./dashboards"
import { detectionCatalogRoutes } from "./detection-catalog"
import { eventSearchRoutes } from "./event-search"
import { externalServicesRoutes } from "./external-services"
import { fallbackRoutes } from "./fallback"
import { graylogRoutes } from "./graylog"
import { healthcheckRoutes } from "./healthcheck"
import { incidentManagementRoutes } from "./incident-management"
import { indicesRoutes } from "./indices"
import { licenseRoutes } from "./license"
import { reportCreationRoutes } from "./report-creation"
import { schedulerRoutes } from "./scheduler"
import { settingsRoutes } from "./settings"
import { usersRoutes } from "./users"

export const routes: RouteRecordRaw[] = [
	...coreRoutes,
	...indicesRoutes,
	...connectorsRoutes,
	...agentsRoutes,
	...graylogRoutes,
	...alertsRoutes,
	...eventSearchRoutes,
	...dashboardsRoutes,
	...incidentManagementRoutes,
	...analystRoutes,
	...detectionCatalogRoutes,
	...healthcheckRoutes,
	...customersRoutes,
	...adminRoutes,
	...usersRoutes,
	...schedulerRoutes,
	...externalServicesRoutes,
	...reportCreationRoutes,
	...assessmentsRoutes,
	...licenseRoutes,
	...settingsRoutes,
	...authRoutes,
	...fallbackRoutes
]
