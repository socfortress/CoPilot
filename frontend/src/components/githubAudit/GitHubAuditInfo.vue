<template>
	<div class="@container flex flex-col gap-6">
		<!-- Status Legend -->
		<n-card size="small" title="Interpreting Results" embedded>
			<div class="grid gap-3 @md:grid-cols-2">
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
			<div class="flex flex-col gap-2 text-sm">
				<strong>Skip Reasons:</strong>
				<div class="flex flex-col gap-1.5">
					<div>
						<code>not_authorized</code>
						<span class="text-secondary">— Token/user missing permission</span>
					</div>
					<div>
						<code>not_supported</code>
						<span class="text-secondary">— Plan/feature not available</span>
					</div>
					<div>
						<code>error</code>
						<span class="text-secondary">— Transient/API error; retry or inspect details</span>
					</div>
				</div>
			</div>
		</n-card>

		<!-- Controls Coverage -->
		<n-collapse>
			<n-collapse-item title="Controls Coverage" name="controls">
				<template #header-extra>
					<n-tag size="small" type="info">What We Check</n-tag>
				</template>

				<div class="flex flex-col gap-3">
					<n-card size="small" title="Organization-Level (Governance)" embedded>
						<div class="divide-border flex flex-col divide-y">
							<div
								v-for="control in orgControls"
								:key="control.id"
								class="flex items-start gap-2 py-2 first:pt-0 last:pb-0"
							>
								<Icon
									class="mt-0.5"
									:size="18"
									:name="control.critical ? 'ion:alert-circle' : 'ion:checkmark-circle'"
									:class="control.critical ? 'text-error' : 'text-success'"
								/>

								<div class="flex flex-col gap-0">
									<div class="text-sm font-medium">{{ control.name }}</div>
									<div class="text-secondary text-xs">{{ control.description }}</div>
								</div>
							</div>
						</div>
					</n-card>

					<n-card size="small" title="Repository-Level (Posture)" embedded>
						<div class="divide-border flex flex-col divide-y">
							<div
								v-for="control in repoControls"
								:key="control.id"
								class="flex items-start gap-2 py-2 first:pt-0 last:pb-0"
							>
								<Icon
									class="mt-0.5"
									:size="18"
									:name="control.critical ? 'ion:alert-circle' : 'ion:checkmark-circle'"
									:class="control.critical ? 'text-error' : 'text-success'"
								/>

								<div class="flex flex-col gap-0">
									<div class="text-sm font-medium">{{ control.name }}</div>
									<div class="text-secondary text-xs">{{ control.description }}</div>
								</div>
							</div>
						</div>
					</n-card>
				</div>
			</n-collapse-item>

			<!-- API Permissions -->
			<n-collapse-item title="Required API Permissions" name="permissions">
				<template #header-extra>
					<n-tag size="small" type="warning">Read-Only</n-tag>
				</template>

				<div class="flex flex-col gap-2">
					<p class="*: flex items-center gap-2 text-sm">
						<Icon name="carbon:information" />
						This audit is intentionally
						<strong>read-only</strong>
						. No write or admin scopes are required.
					</p>

					<n-tabs type="segment" animated>
						<n-tab-pane name="fine-grained" tab="Fine-Grained PAT (Recommended)">
							<div class="flex flex-col gap-3">
								<p class="text-warning flex items-center gap-2 text-sm">
									<Icon name="carbon:warning" class="text-warning" />
									Create a fine-grained PAT restricted to only the target organization and repos you
									intend to audit.
								</p>

								<n-card size="small" title="Organization Permissions (READ)" embedded>
									<n-list class="bg-transparent!">
										<n-list-item v-for="perm in fineGrainedOrgPerms" :key="perm.name">
											<template #prefix>
												<n-tag :type="perm.required ? 'error' : 'default'" size="small">
													{{ perm.required ? "Required" : "Optional" }}
												</n-tag>
											</template>
											<div>
												<div class="text-sm font-medium">{{ perm.name }}</div>
												<div class="text-secondary text-xs">{{ perm.description }}</div>
											</div>
										</n-list-item>
									</n-list>
								</n-card>

								<n-card size="small" title="Repository Permissions (READ)" embedded>
									<n-list class="bg-transparent!">
										<n-list-item v-for="perm in fineGrainedRepoPerms" :key="perm.name">
											<template #prefix>
												<n-tag :type="perm.required ? 'error' : 'default'" size="small">
													{{ perm.required ? "Required" : "Optional" }}
												</n-tag>
											</template>
											<div>
												<div class="text-sm font-medium">{{ perm.name }}</div>
												<div class="text-secondary text-xs">{{ perm.description }}</div>
											</div>
										</n-list-item>
									</n-list>
								</n-card>
							</div>
						</n-tab-pane>

						<n-tab-pane name="classic" tab="Classic PAT (Fallback)">
							<div class="flex flex-col gap-3">
								<p class="text-warning flex items-center gap-2 text-sm">
									<Icon name="carbon:warning" class="text-warning" />
									Classic PATs have broader scope. Use fine-grained PATs when possible.
								</p>

								<n-card size="small" title="Required Scopes" embedded>
									<n-list class="bg-transparent!">
										<n-list-item v-for="scope in classicScopes" :key="scope.name">
											<template #prefix>
												<n-tag :type="scope.required ? 'error' : 'default'" size="small">
													{{ scope.required ? "Required" : "Optional" }}
												</n-tag>
											</template>
											<div>
												<div class="text-sm font-medium">{{ scope.name }}</div>
												<div class="text-secondary text-xs">
													{{ scope.description }}
												</div>
											</div>
										</n-list-item>
									</n-list>
								</n-card>
							</div>
						</n-tab-pane>
					</n-tabs>
				</div>
			</n-collapse-item>

			<!-- API Endpoints -->
			<n-collapse-item title="API Endpoints Used" name="endpoints">
				<template #header-extra>
					<n-tag size="small">GET Only</n-tag>
				</template>

				<div class="flex flex-col gap-3">
					<n-card size="small" title="Organization Endpoints" embedded>
						<n-list class="bg-transparent!">
							<n-list-item v-for="endpoint in orgEndpoints" :key="endpoint.path">
								<div class="font-mono text-sm">
									<span class="text-green-500">GET</span>
									{{ endpoint.path }}
								</div>
								<div v-if="endpoint.note" class="text-secondary mt-1 text-xs">
									{{ endpoint.note }}
								</div>
							</n-list-item>
						</n-list>
					</n-card>

					<n-card size="small" title="Repository Endpoints" embedded>
						<n-list class="bg-transparent!">
							<n-list-item v-for="endpoint in repoEndpoints" :key="endpoint.path">
								<div class="font-mono text-sm">
									<span class="text-green-500">GET</span>
									{{ endpoint.path }}
								</div>
								<div v-if="endpoint.note" class="text-secondary mt-1 text-xs">
									{{ endpoint.note }}
								</div>
							</n-list-item>
						</n-list>
					</n-card>
				</div>
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
import { NCard, NCollapse, NCollapseItem, NDivider, NList, NListItem, NTabPane, NTabs, NTag } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

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
