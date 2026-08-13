<template>
	<CardEntity embedded hoverable>
		<template #headerMain>
			<div class="flex items-center gap-2">
				{{ check.check_name }}
				<n-tag v-if="check.provisioned" type="success" size="small" round :bordered="false">Provisioned</n-tag>
			</div>
		</template>
		<template #default>
			{{ check.description }}
		</template>
		<template #headerExtra>
			<n-button
				:loading="loadingProvision"
				:type="check.provisioned ? 'warning' : 'success'"
				size="small"
				secondary
				@click="provision()"
			>
				<template #icon>
					<Icon :name="check.provisioned ? OverwriteIcon : DeployIcon" />
				</template>
				{{ check.provisioned ? "Overwrite" : "Deploy" }}
			</n-button>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AvailableInfluxDbCheck } from "@/types/stack-provisioning"
import { NButton, NTag, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const { check } = defineProps<{ check: AvailableInfluxDbCheck }>()

const emit = defineEmits<{
	(e: "provisioned"): void
}>()

const DeployIcon = "mdi:package-variant-closed-check"
const OverwriteIcon = "mdi:package-variant-plus"
const loadingProvision = ref(false)
const message = useMessage()

function provision() {
	loadingProvision.value = true

	// A check that already exists is skipped by the backend unless overwrite is set, so an
	// already-provisioned check has to opt in explicitly to replace whatever is in InfluxDB.
	Api.stackProvisioning
		.provisionInfluxDbCheck(check.name, check.provisioned)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "InfluxDB Check Provisioned Successfully")
				emit("provisioned")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingProvision.value = false
		})
}
</script>
