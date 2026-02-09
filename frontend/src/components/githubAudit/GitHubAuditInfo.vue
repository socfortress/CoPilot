<template>
	<n-drawer v-model:show="showDrawer" :width="700" placement="right">
		<n-drawer-content closable>
			<template #header>
				<div class="flex items-center gap-3">
					<n-icon size="24">
						<Icon :name="InfoIcon" />
					</n-icon>
					<span>GitHub Audit Reference Guide</span>
				</div>
			</template>

			<div class="space-y-6">
				<!-- Status Legend -->
				<n-card size="small" title="Interpreting Results">
					<div class="grid grid-cols-2 gap-3">
						<div class="flex items-center gap-2">
							<n-tag type="success" size="small">PASS</n-tag>
							<span class="text-sm">Control meets baseline</span>
						</div>
						<div class="flex items-center gap-2">
							<n-tag type="error" size="small">FAIL</n-tag>
							<span class="text-sm">Remediation recommended</span>
						</div>
						<div class="flex items-center gap-2">
							<n-tag type="warning" size="small">WARN</n-tag>
							<span class="text-sm">Attention required</span>
						</div>
						<div class="flex items-center gap-2">
							<n-tag type="default" size="small">SKIP</n-tag>
							<span class="text-sm">Cannot evaluate</span>
						</div>
					</div>
					<n-divider />
					<div class="text-sm text-gray-500">
						<p class="mb-2"><strong>Skip Reasons:</strong></p>
						<ul class="list-disc list-inside space-y-1">
							<li><code>not_authorized</code> — Token/user missing permission</li>
							<li><code>not_supported</code> — Plan/feature not available</li>
							<li><code>error</code> — Transient/API error; retry or inspect details</li>
						</ul>
					</div>
				</n-card>

				<!-- Controls Coverage -->
				<n-collapse>
					<n-collapse-item title="Controls Coverage" name="controls">
						<template #header-extra>
							<n-tag size="small" type="info">What We Check</n-tag>
						</template>

						<n-card size="small" title="Organization-Level (Governance)" class="mb-3">
							<n-list>
								<n-list-item v-for="control in orgControls" :key="control.id">
									<template #prefix>
										<n-icon :color="control.critical ? '#e88080' : '#63e2b7'">
											<Icon :name="control.critical ? 'ion:alert-circle' : 'ion:checkmark-circle'" />
										</n-icon>
									</template>
									<div>
										<div class="font-medium">{{ control.name }}</div>
										<div class="text-sm text-gray-500">{{ control.description }}</div>
									</div>
								</n-list-item>
							</n-list>
						</n-card>

						<n-card size="small" title="Repository-Level (Posture)">
							<n-list>
								<n-list-item v-for="control in repoControls" :key="control.id">
									<template #prefix>
										<n-icon :color="control.critical ? '#e88080' : '#63e2b7'">
											<Icon :name="control.critical ? 'ion:alert-circle' : 'ion:checkmark-circle'" />
										</n-icon>
									</template>
									<div>
										<div class="font-medium">{{ control.name }}</div>
										<div class="text-sm text-gray-500">{{ control.description }}</div>
									</div>
								</n-list-item>
							</n-list>
						</n-card>
					</n-collapse-item>

					<!-- API Permissions -->
					<n-collapse-item title="Required API Permissions" name="permissions">
						<template #header-extra>
							<n-tag size="small" type="warning">Read-Only</n-tag>
						</template>

						<n-alert type="info" class="mb-4">
							This audit is intentionally <strong>read-only</strong>. No write or admin scopes are required.
						</n-alert>

						<n-tabs type="segment" animated>
							<n-tab-pane name="fine-grained" tab="Fine-Grained PAT (Recommended)">
								<div class="space-y-4">
									<p class="text-sm">
										Create a fine-grained PAT restricted to only the target organization and repos you intend to
										audit.
									</p>

									<n-card size="small" title="Organization Permissions (READ)">
										<n-list>
											<n-list-item v-for="perm in fineGrainedOrgPerms" :key="perm.name">
												<template #prefix>
													<n-tag :type="perm.required ? 'error' : 'default'" size="small">
														{{ perm.required ? "Required" : "Optional" }}
													</n-tag>
												</template>
												<div>
													<div class="font-medium">{{ perm.name }}</div>
													<div class="text-sm text-gray-500">{{ perm.description }}</div>
												</div>
											</n-list-item>
										</n-list>
									</n-card>

									<n-card size="small" title="Repository Permissions (READ)">
										<n-list>
											<n-list-item v-for="perm in fineGrainedRepoPerms" :key="perm.name">
												<template #prefix>
													<n-tag :type="perm.required ? 'error' : 'default'" size="small">
														{{ perm.required ? "Required" : "Optional" }}
													</n-tag>
												</template>
												<div>
													<div class="font-medium">{{ perm.name }}</div>
													<div class="text-sm text-gray-500">{{ perm.description }}</div>
												</div>
											</n-list-item>
										</n-list>
									</n-card>
								</div>
							</n-tab-pane>

							<n-tab-pane name="classic" tab="Classic PAT (Fallback)">
								<div class="space-y-4">
									<n-alert type="warning" class="mb-4">
										Classic PATs have broader scope. Use fine-grained PATs when possible.
									</n-alert>

									<n-card size="small" title="Required Scopes">
										<n-list>
											<n-list-item v-for="scope in classicScopes" :key="scope.name">
												<template #prefix>
													<n-tag :type="scope.required ? 'error' : 'default'" size="small">
														{{ scope.required ? "Required" : "Optional" }}
													</n-tag>
												</template>
												<div>
													<div class="font-mono font-medium">{{ scope.name }}</div>
													<div class="text-sm text-gray-500">{{ scope.description }}</div>
												</div>
											</n-list-item>
										</n-list>
									</n-card>
								</div>
							</n-tab-pane>
						</n-tabs>
					</n-collapse-item>

					<!-- API Endpoints -->
					<n-collapse-item title="API Endpoints Used" name="endpoints">
						<template #header-extra>
							<n-tag size="small">GET Only</n-tag>
						</template>

						<n-card size="small" title="Organization Endpoints" class="mb-3">
							<n-list>
								<n-list-item v-for="endpoint in orgEndpoints" :key="endpoint.path">
									<div class="font-mono text-sm">
										<span class="text-green-500">GET</span>
										{{ endpoint.path }}
									</div>
									<div v-if="endpoint.note" class="text-xs text-gray-500 mt-1">{{ endpoint.note }}</div>
								</n-list-item>
							</n-list>
						</n-card>

						<n-card size="small" title="Repository Endpoints">
							<n-list>
								<n-list-item v-for="endpoint in repoEndpoints" :key="endpoint.path">
									<div class="font-mono text-sm">
										<span class="text-green-500">GET</span>
										{{ endpoint.path }}
									</div>
									<div v-if="endpoint.note" class="text-xs text-gray-500 mt-1">{{ endpoint.note }}</div>
								</n-list-item>
							</n-list>
						</n-card>
					</n-collapse-item>
				</n-collapse>
			</div>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import {
    NAlert,
    NCard,
    NCollapse,
    NCollapseItem,
    NDivider,
    NDrawer,
    NDrawerContent,
    NIcon,
    NList,
    NListItem,
    NTabPane,
    NTabs,
    NTag
} from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
    show: boolean
}>()

const emit = defineEmits<{
    (e: "update:show", value: boolean): void
}>()

const InfoIcon = "ion:information-circle-outline"

const showDrawer = computed({
    get: () => props.show,
    set: (value) => emit("update:show", value)
})

// Controls data
const orgControls = [
    {
        id: "mfa",
        name: "MFA Enforcement",
        description: "Require two-factor authentication for all organization members",
        critical: true
    },
    {
        id: "org-owners",
        name: "Org Owner Minimization",
        description: "Limit the number of organization owners to reduce risk",
        critical: false
    },
    {
        id: "outside-collab",
        name: "Outside Collaborator Monitoring",
        description: "Track external collaborators with access to repositories",
        critical: false
    },
    {
        id: "saml-sso",
        name: "SAML SSO Enforced",
        description: "Enforce single sign-on for centralized authentication",
        critical: true
    },
    {
        id: "pat-expiry",
        name: "PAT Expiration Enforced",
        description: "Require personal access tokens to have expiration dates",
        critical: false
    },
    {
        id: "actions-policy",
        name: "GitHub Actions Policy",
        description: "Control allowed actions, default permissions, and fork PR approvals",
        critical: false
    },
    {
        id: "audit-log",
        name: "Audit Log Monitoring",
        description: "Monitor control-plane changes via audit log detection pack",
        critical: false
    }
]

const repoControls = [
    {
        id: "visibility",
        name: "Repository Visibility",
        description: "Ensure appropriate public/private visibility settings",
        critical: false
    },
    {
        id: "branch-protection",
        name: "Branch Protection",
        description: "Enforce approvals, status checks, and prevent force pushes",
        critical: true
    },
    {
        id: "secret-scanning",
        name: "Secret Scanning + Push Protection",
        description: "Detect and block secrets in code before they're exposed",
        critical: true
    },
    {
        id: "dependabot",
        name: "Dependabot Alerts",
        description: "Monitor dependencies for known vulnerabilities",
        critical: true
    },
    {
        id: "code-scanning",
        name: "Code Scanning",
        description: "Identify security vulnerabilities in source code",
        critical: false
    },
    {
        id: "environments",
        name: "Deployment Environments",
        description: "Protect deployment environments with reviewers and rules",
        critical: false
    }
]

// Fine-grained PAT permissions
const fineGrainedOrgPerms = [
    {
        name: "Administration",
        description: "Required for org policy, Actions settings, SSO indicator, PAT policy",
        required: true
    },
    {
        name: "Members",
        description: "Required for outside collaborator visibility and membership endpoints",
        required: true
    },
    {
        name: "Audit Log",
        description: "Required for audit-log detections; otherwise those checks will SKIP",
        required: false
    }
]

const fineGrainedRepoPerms = [
    {
        name: "Administration",
        description: "Required for branch protection, environments, and repo settings",
        required: true
    },
    {
        name: "Contents",
        description: "Often required for workflow-related metadata visibility",
        required: true
    },
    {
        name: "Actions",
        description: "Recommended for Actions-related repo metadata",
        required: false
    },
    {
        name: "Security events",
        description: "Required for secret scanning, Dependabot alerts, code scanning status",
        required: true
    }
]

// Classic PAT scopes
const classicScopes = [
    {
        name: "read:org",
        description: "Needed for org membership and org settings",
        required: true
    },
    {
        name: "repo",
        description: "Required to read branch protection and repo config on private repos",
        required: true
    }
]

// API endpoints
const orgEndpoints = [
    { path: "/orgs/{org}", note: null },
    { path: "/orgs/{org}/repos", note: null },
    { path: "/orgs/{org}/actions/permissions", note: null },
    { path: "/orgs/{org}/actions/permissions/workflow", note: null },
    { path: "/orgs/{org}/actions/permissions/selected-actions", note: null },
    { path: "/orgs/{org}/personal-access-tokens/policies", note: "May be plan/role gated" },
    { path: "/orgs/{org}/audit-log", note: "Detections; plan/role gated" }
]

const repoEndpoints = [
    { path: "/repos/{org}/{repo}", note: "Includes security_and_analysis where available" },
    { path: "/repos/{org}/{repo}/branches/{branch}/protection", note: null },
    { path: "/repos/{org}/{repo}/environments", note: null }
]
</script>

<style scoped>
.space-y-6 > * + * {
    margin-top: 1.5rem;
}

.space-y-4 > * + * {
    margin-top: 1rem;
}

.grid-cols-2 {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
}
</style>
