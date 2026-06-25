<template>
	<CardEntity>
		<template #headerMain>
			<div class="flex items-center gap-3">
				<Icon name="codicon:organization" :size="20" />

				<div class="text-default font-display text-lg font-semibold">
					{{ config.organization }}
				</div>
			</div>
		</template>
		<template #headerExtra>
			<div class="flex items-center justify-end gap-2">
				<n-tag v-if="config.enabled" type="success" size="small">Enabled</n-tag>
				<n-tag v-else type="error" size="small">Disabled</n-tag>

				<n-tag v-if="config.auto_audit_enabled" type="success" size="small">Scheduled</n-tag>
				<n-tag v-else type="error" size="small">Not scheduled</n-tag>
			</div>
		</template>
		<template #default>
			<GitHubAuditConfigSummary :config meta-fields="card" />
		</template>
		<template #footerMain>
			<GitHubAuditScopeFlags :config />
		</template>
		<template #footerExtra>
			<div class="flex flex-wrap items-center justify-end gap-2">
				<n-button size="small" quaternary :loading="running" @click.stop="runAudit">
					<template #icon>
						<Icon :name="PlayIcon" />
					</template>
					Run Audit
				</n-button>
				<n-button size="small" @click.stop="$emit('edit', config)">
					<template #icon>
						<Icon :name="EditIcon" />
					</template>
					Edit
				</n-button>
				<n-button size="small" type="primary" secondary @click.stop="$emit('click', config)">
					<template #icon>
						<Icon :name="DetailIcon" />
					</template>
					View Details
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { GitHubAuditConfig } from "@/types/githubAudit"
import { NButton, NTag, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CardEntity from "../common/cards/CardEntity.vue"
import GitHubAuditConfigSummary from "./GitHubAuditConfigSummary.vue"
import GitHubAuditScopeFlags from "./GitHubAuditScopeFlags.vue"

const props = defineProps<{
	config: GitHubAuditConfig
}>()
const emit = defineEmits<{
	(e: "click", config: GitHubAuditConfig): void
	(e: "edit", config: GitHubAuditConfig): void
	(e: "audit-complete"): void
}>()

const PlayIcon = "carbon:play"
const EditIcon = "carbon:edit"
const DetailIcon = "carbon:view"

const message = useMessage()
const running = ref(false)

async function runAudit() {
	running.value = true
	try {
		await Api.githubAudit.runAuditFromConfig(props.config.id)
		message.success("Audit completed successfully")
		emit("audit-complete")
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to run audit")
	} finally {
		running.value = false
	}
}
</script>
