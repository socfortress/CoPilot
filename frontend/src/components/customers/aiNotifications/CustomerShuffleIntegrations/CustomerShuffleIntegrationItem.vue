<template>
	<CardEntity hoverable embedded>
		<template #headerMain>
			<div class="flex items-center gap-2">
				<Icon name="carbon:integration" :size="16" />
				<span class="font-medium">{{ integration.display_name }}</span>
				<Badge v-if="!integration.enabled" type="splitted" color="warning">
					<template #label>Status</template>
					<template #value>Disabled</template>
				</Badge>
				<Badge v-if="verifyResult === 'ok'" type="splitted" color="success">
					<template #label>Probe</template>
					<template #value>{{ verifyAppCount }} app(s)</template>
				</Badge>
				<Badge v-else-if="verifyResult === 'fail'" type="splitted" color="danger">
					<template #label>Probe</template>
					<template #value>failed</template>
				</Badge>
			</div>
		</template>

		<template #headerExtra>
			<div class="flex items-center gap-2">
				<n-tooltip>
					<template #trigger>
						<n-button
							size="tiny"
							quaternary
							circle
							:loading="verifying"
							:type="verifyButtonType"
							@click="verify"
						>
							<template #icon>
								<Icon :name="verifyButtonIcon" :size="14" />
							</template>
						</n-button>
					</template>
					{{ verifyTooltip }}
				</n-tooltip>

				<n-tooltip>
					<template #trigger>
						<n-button size="tiny" quaternary circle @click="$emit('manageApps')">
							<template #icon>
								<Icon :name="ManageAppsIcon" :size="14" />
							</template>
						</n-button>
					</template>
					Manage apps
				</n-tooltip>

				<n-tooltip>
					<template #trigger>
						<n-button size="tiny" quaternary circle @click="toggleEnabled">
							<template #icon>
								<Icon :name="integration.enabled ? PauseIcon : PlayIcon" :size="14" />
							</template>
						</n-button>
					</template>
					{{ integration.enabled ? "Disable" : "Enable" }}
				</n-tooltip>

				<n-tooltip>
					<template #trigger>
						<n-button size="tiny" quaternary circle @click="$emit('edit')">
							<template #icon>
								<Icon :name="EditIcon" :size="14" />
							</template>
						</n-button>
					</template>
					Edit
				</n-tooltip>

				<n-popconfirm @positive-click="confirmDelete">
					<template #trigger>
						<n-button size="tiny" quaternary circle>
							<template #icon>
								<Icon :name="DeleteIcon" :size="14" />
							</template>
						</n-button>
					</template>
					Delete this integration?
					<template #icon>
						<Icon :name="WarningIcon" :size="14" />
					</template>
				</n-popconfirm>
			</div>
		</template>

		<template #default>
			<div class="flex flex-col gap-1 text-sm">
				<div class="text-secondary">
					<span class="font-medium">Org-Id:</span>
					<code class="ml-1 break-all">{{ integration.shuffle_org_id }}</code>
				</div>
				<div v-if="verifyError" class="text-error text-xs">
					{{ verifyError }}
				</div>
			</div>
		</template>

		<template #footer>
			<div class="text-tertiary flex items-center gap-3 text-xs">
				<span v-if="integration.last_used_at">
					last used {{ formatDate(integration.last_used_at, "MMM D, YYYY HH:mm") }}
				</span>
				<span v-else>never used</span>
				<span v-if="integration.created_by">· created by {{ integration.created_by }}</span>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ShuffleIntegration } from "@/types/notifications.d"
import { NButton, NPopconfirm, NTooltip, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	integration: ShuffleIntegration
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "deleted"): void
	(e: "toggled"): void
	(e: "manageApps"): void
}>()

const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
const PauseIcon = "carbon:pause"
const PlayIcon = "carbon:play"
const ManageAppsIcon = "carbon:catalog"
const VerifyIcon = "carbon:checkmark-outline"
const VerifyOkIcon = "carbon:checkmark-filled"
const VerifyFailIcon = "carbon:misuse"
const WarningIcon = "carbon:warning"

const message = useMessage()

// Verify state — null until the user clicks "Test connection." Drives
// both the inline status badge and the verify button's color/icon so
// admins get an at-a-glance signal that the probe succeeded without
// having to read the badge text.
const verifying = ref(false)
const verifyResult = ref<"ok" | "fail" | null>(null)
const verifyAppCount = ref<number | null>(null)
const verifyError = ref<string | null>(null)

// naive-ui n-button accepts type='success'|'error'|'default'|... — we
// map verify result to a colored button so the icon turns green on a
// good probe and red on a bad one, and stays neutral before/while
// running. `quaternary` keeps the button visually subtle when there's
// no result yet.
const verifyButtonType = computed<"default" | "success" | "error">(() => {
	if (verifyResult.value === "ok") return "success"
	if (verifyResult.value === "fail") return "error"
	return "default"
})

const verifyButtonIcon = computed(() => {
	if (verifyResult.value === "ok") return VerifyOkIcon
	if (verifyResult.value === "fail") return VerifyFailIcon
	return VerifyIcon
})

const verifyTooltip = computed(() => {
	if (verifyResult.value === "ok") return `Probe OK · ${verifyAppCount.value ?? "?"} app(s) · click to re-test`
	if (verifyResult.value === "fail") return "Probe failed · click to re-test"
	return "Test connection"
})

async function verify() {
	verifying.value = true
	verifyError.value = null
	try {
		const res = await Api.notifications.verifyShuffleIntegration(
			props.integration.customer_code,
			props.integration.id
		)
		if (res.data.success) {
			verifyResult.value = "ok"
			verifyAppCount.value = res.data.app_count
		} else {
			verifyResult.value = "fail"
			verifyError.value = res.data.error || res.data.message || "Verification failed"
		}
	} catch (err: unknown) {
		verifyResult.value = "fail"
		verifyError.value = getApiErrorMessage(err as never) || "Verification failed"
	} finally {
		verifying.value = false
	}
}

async function toggleEnabled() {
	try {
		const res = await Api.notifications.updateShuffleIntegration(
			props.integration.customer_code,
			props.integration.id,
			{ enabled: !props.integration.enabled }
		)
		if (res.data.success) {
			message.success(`Integration ${res.data.integration.enabled ? "enabled" : "disabled"}`)
			emit("toggled")
		} else {
			message.warning(res.data.message || "Failed to toggle integration")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to toggle integration")
	}
}

async function confirmDelete() {
	try {
		const res = await Api.notifications.deleteShuffleIntegration(
			props.integration.customer_code,
			props.integration.id
		)
		if (res.data.success) {
			message.success("Integration deleted")
			emit("deleted")
		} else {
			message.warning(res.data.message || "Failed to delete integration")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to delete integration")
	}
}
</script>
