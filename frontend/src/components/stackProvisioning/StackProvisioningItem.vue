<template>
	<CardEntity embedded hoverable>
		<template #headerMain>
			{{ contentPack.name }}
		</template>
		<template #default>
			{{ contentPack.description }}
		</template>
		<template #headerExtra>
			<n-button
				:loading="loadingProvision"
				type="success"
				size="small"
				secondary
				@click="provision(contentPack.name)"
			>
				<template #icon>
					<Icon :name="DeployIcon" />
				</template>
				Deploy
			</n-button>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { AvailableContentPack } from "@/types/stackProvisioning.d"
import { NButton, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const { contentPack } = defineProps<{ contentPack: AvailableContentPack }>()

const emit = defineEmits<{
	(e: "provisioned"): void
}>()

const DeployIcon = "mdi:package-variant-closed-check"
const loadingProvision = ref(false)
const message = useMessage()

function provision(contentPackName: string) {
	loadingProvision.value = true

	Api.stackProvisioning
		.provisionContentPack(contentPackName)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Content Pack Provisioned Successfully")
				emit("provisioned")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingProvision.value = false
		})
}
</script>
