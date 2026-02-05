import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import { h } from "vue"
import { RouterLink } from "vue-router"
import IncidentManagementIcon from "@/assets/icons/alert-settings-icon.svg"

import { renderIcon } from "@/utils"

const OverviewIcon = "carbon:dashboard"
const IndiciesIcon = "ph:list-magnifying-glass"
const AgentsIcon = "carbon:network-3"
const ConnectorsIcon = "carbon:hybrid-networking"
const GraylogIcon = "majesticons:pulse-line"
const AlertsIcon = "carbon:warning-hex"
const ArtifactsIcon = "carbon:document-multiple-01"
// const SocIcon = "carbon:security"
const HealthcheckIcon = "ph:heartbeat"
const CustomersIcon = "carbon:user-multiple"
const ExternalServicesIcon = "carbon:ibm-cloud-direct-link-2-dedicated"
const ReportCreationIcon = "carbon:report-data"
const SchedulerIcon = "material-symbols:autoplay"
const CustomerPortalIcon = "streamline-ultimate:coding-apps-website-apps-browser"

export default function getItems(): MenuMixedOption[] {
    return [
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "Overview"
                        }
                    },
                    { default: () => "Overview" }
                ),
            key: "Overview",
            icon: renderIcon(OverviewIcon)
        },
        {
            label: "Incident Management",
            key: "IncidentManagement",
            icon: renderIcon(IncidentManagementIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "IncidentManagement-Sources"
                                }
                            },
                            { default: () => "Sources" }
                        ),
                    key: "IncidentManagement-Sources"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "IncidentManagement-Alerts"
                                }
                            },
                            { default: () => "Alerts" }
                        ),
                    key: "IncidentManagement-Alerts"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "IncidentManagement-Cases"
                                }
                            },
                            { default: () => "Cases" }
                        ),
                    key: "IncidentManagement-Cases"
                }
                /*
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "IncidentManagement-Sigma"
                                }
                            },
                            { default: () => "SIGMA" }
                        ),
                    key: "IncidentManagement-Sigma"
                }
                */
            ]
        },
        {
            label: "Alerts",
            key: "Alerts",
            icon: renderIcon(AlertsIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Alerts-SIEM"
                                }
                            },
                            { default: () => "SIEM" }
                        ),
                    key: "Alerts-SIEM"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Alerts-Mitre"
                                }
                            },
                            { default: () => "MITRE ATT&CK" }
                        ),
                    key: "Alerts-Mitre"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Alerts-AtomicRedTeam"
                                }
                            },
                            { default: () => "Atomic Red Team" }
                        ),
                    key: "Alerts-AtomicRedTeam"
                }
            ]
        },
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "Artifacts"
                        }
                    },
                    { default: () => "Artifacts" }
                ),
            key: "Artifacts",
            icon: renderIcon(ArtifactsIcon)
        },
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "Customers"
                        }
                    },
                    { default: () => "Customers" }
                ),
            key: "Customers",
            icon: renderIcon(CustomersIcon)
        },
        {
            label: "Agents",
            key: "Agents",
            icon: renderIcon(AgentsIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Agents"
                                }
                            },
                            { default: () => "Agents list" }
                        ),
                    key: "Agents"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Groups"
                                }
                            },
                            { default: () => "Groups" }
                        ),
                    key: "Groups"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "SysmonConfig"
                                }
                            },
                            { default: () => "Sysmon Config" }
                        ),
                    key: "SysmonConfig"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "DetectionRules"
                                }
                            },
                            { default: () => "Detection Rules" }
                        ),
                    key: "DetectionRules"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "CopilotActions"
                                }
                            },
                            { default: () => "CoPilot Actions" }
                        ),
                    key: "CopilotActions"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "VulnerabilityOverview"
                                }
                            },
                            { default: () => "Vulnerability Overview" }
                        ),
                    key: "VulnerabilityOverview"
                },
				{
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "PatchTuesday"
                                }
                            },
                            { default: () => "Patch Tuesday" }
                        ),
                    key: "PatchTuesday"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "ScaOverview"
                                }
                            },
                            { default: () => "SCA Overview" }
                        ),
                    key: "ScaOverview"
                }
            ]
        },
        {
            label: "Report Creation",
            key: "ReportCreation",
            icon: renderIcon(ReportCreationIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "ReportCreation"
                                }
                            },
                            { default: () => "General Reports" }
                        ),
                    key: "ReportCreation"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "VulnerabilityReports"
                                }
                            },
                            { default: () => "Vulnerability Reports" }
                        ),
                    key: "VulnerabilityReports"
                },
				{
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "SCAReports"
                                }
                            },
                            { default: () => "SCA Reports" }
                        ),
                    key: "SCAReports"
                }
            ]
        },
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "Healthcheck"
                        }
                    },
                    { default: () => "Healthcheck" }
                ),
            key: "Healthcheck",
            icon: renderIcon(HealthcheckIcon)
        },
        {
            label: "Indices",
            key: "IndicesMenu",
            icon: renderIcon(IndiciesIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Indices"
                                }
                            },
                            { default: () => "Index Management" }
                        ),
                    key: "Indices"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Snapshots"
                                }
                            },
                            { default: () => "Snapshot & Restore" }
                        ),
                    key: "Snapshots"
                }
            ]
        },
        {
            label: "Graylog",
            key: "Graylog",
            icon: renderIcon(GraylogIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Graylog-Management"
                                }
                            },
                            { default: () => "Management" }
                        ),
                    key: "Graylog-Management"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Graylog-Metrics"
                                }
                            },
                            { default: () => "Metrics" }
                        ),
                    key: "Graylog-Metrics"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "Graylog-Pipelines"
                                }
                            },
                            { default: () => "Pipelines" }
                        ),
                    key: "Graylog-Pipelines"
                }
            ]
        },
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "Connectors"
                        }
                    },
                    { default: () => "Connectors" }
                ),
            key: "Connectors",
            icon: renderIcon(ConnectorsIcon)
        },
        {
            label: "External Services",
            key: "ExternalServices",
            icon: renderIcon(ExternalServicesIcon),
            children: [
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "ExternalServices-ThirdPartyIntegrations"
                                }
                            },
                            { default: () => "3rd Party Integrations" }
                        ),
                    key: "ExternalServices-ThirdPartyIntegrations"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "ExternalServices-NetworkConnectors"
                                }
                            },
                            { default: () => "Network Connectors" }
                        ),
                    key: "ExternalServices-NetworkConnectors"
                },
                {
                    label: () =>
                        h(
                            RouterLink,
                            {
                                to: {
                                    name: "ExternalServices-SingulAppAuth"
                                }
                            },
                            { default: () => "Singul App Auth" }
                        ),
                    key: "ExternalServices-SingulAppAuth"
                }
            ]
        },
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "Scheduler"
                        }
                    },
                    { default: () => "Scheduler" }
                ),
            key: "Scheduler",
            icon: renderIcon(SchedulerIcon)
        },
        {
            label: () =>
                h(
                    RouterLink,
                    {
                        to: {
                            name: "CustomerPortal"
                        }
                    },
                    { default: () => "Customer Portal" }
                ),
            key: "CustomerPortal",
            icon: renderIcon(CustomerPortalIcon)
        }
    ]
}
