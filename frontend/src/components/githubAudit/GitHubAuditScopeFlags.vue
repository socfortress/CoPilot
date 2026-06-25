<template>
	<div class="border-border divide-border grid grid-cols-4 divide-x rounded-md border">
		<n-tooltip v-for="flag in includeFlags" :key="flag.key" class="px-2! py-1!">
			<template #trigger>
				<div
					class="flex flex-col items-center justify-center"
					:class="size === 'large' ? 'gap-1 px-2 py-2.5' : 'gap-0 px-1 py-0.5'"
				>
					<span :class="size === 'large' ? 'text-sm' : 'text-xs'">
						{{ flag.shortLabel }}
					</span>
					<Icon
						:name="config[flag.key] ? 'carbon:checkmark' : 'carbon:close'"
						:class="config[flag.key] ? 'text-success' : 'text-error'"
					/>
				</div>
			</template>
			<span :class="size === 'large' ? 'text-sm' : 'text-xs'">{{ flag.label }}</span>
		</n-tooltip>
	</div>
</template>

<script setup lang="ts">
import type { GitHubAuditConfig } from "@/types/github-audit"
import { NTooltip } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

type IncludeFlagKey = "include_archived_repos" | "include_members" | "include_repos" | "include_workflows"

type FlagSize = "small" | "large"

withDefaults(
	defineProps<{
		config: GitHubAuditConfig
		size?: FlagSize
	}>(),
	{ size: "small" }
)

const includeFlags: { key: IncludeFlagKey; shortLabel: string; label: string }[] = [
	{ key: "include_archived_repos", shortLabel: "A", label: "Include archived repos" },
	{ key: "include_members", shortLabel: "M", label: "Include members" },
	{ key: "include_repos", shortLabel: "R", label: "Include repos" },
	{ key: "include_workflows", shortLabel: "W", label: "Include workflows" }
]
</script>
