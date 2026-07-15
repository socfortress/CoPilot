<template>
	<div>
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
					<n-button size="small" @click.stop="openEdit()">
						<template #icon>
							<Icon :name="EditIcon" />
						</template>
						Edit
					</n-button>
					<EntityDetailsButton
						size="small"
						view-label="View Details"
						:route="routeGitHubAuditConfig(config.id)"
						@view="showDetail = true"
					/>
				</div>
			</template>
		</CardEntity>

		<!-- Detail drawer (owned by the card) -->
		<n-drawer v-model:show="showDetail" :width="800" placement="right" class="max-w-[98vw]" display-directive="show">
			<n-drawer-content closable :native-scrollbar="false">
				<template #header>
					<div class="flex items-center gap-3">
						<Icon name="codicon:organization" :size="24" />
						<span>{{ config.organization }}</span>
						<n-tag v-if="!config.enabled" type="warning" size="small">Disabled</n-tag>
					</div>
				</template>

				<GitHubAuditDetail
					:config
					@updated="emit('updated')"
					@edit="openEdit()"
					@close="showDetail = false"
				/>
			</n-drawer-content>
		</n-drawer>

		<!-- Edit drawer (owned by the card) -->
		<n-drawer v-model:show="showEdit" :width="600" placement="right" class="max-w-[98vw]" display-directive="show">
			<n-drawer-content title="Edit Configuration" closable :native-scrollbar="false">
				<GitHubAuditConfigForm v-if="showEdit" :config @saved="onSaved()" @cancel="showEdit = false" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { GitHubAuditConfig } from "@/types/github-audit"
import { NButton, NDrawer, NDrawerContent, NTag, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import CardEntity from "../common/cards/CardEntity.vue"
import GitHubAuditConfigForm from "./GitHubAuditConfigForm.vue"
import GitHubAuditConfigSummary from "./GitHubAuditConfigSummary.vue"
import GitHubAuditDetail from "./GitHubAuditDetail.vue"
import GitHubAuditScopeFlags from "./GitHubAuditScopeFlags.vue"

const props = defineProps<{
	config: GitHubAuditConfig
}>()
const emit = defineEmits<{
	(e: "updated"): void
}>()

const { routeGitHubAuditConfig } = useNavigation()

const PlayIcon = "carbon:play"
const EditIcon = "carbon:edit"

const message = useMessage()
const running = ref(false)
const showDetail = ref(false)
const showEdit = ref(false)

function openEdit() {
	showDetail.value = false
	showEdit.value = true
}

function onSaved() {
	showEdit.value = false
	emit("updated")
}

async function runAudit() {
	running.value = true
	try {
		await Api.githubAudit.runAuditFromConfig(props.config.id)
		message.success("Audit completed successfully")
		emit("updated")
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to run audit")
	} finally {
		running.value = false
	}
}
</script>
