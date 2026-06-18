<template>
	<div class="flex flex-col gap-3">
		<div v-if="showToolbar" class="flex flex-wrap items-center justify-end gap-2">
			<div class="flex min-w-0 grow flex-wrap items-center gap-2">
				<Badge type="splitted" color="primary" size="small">
					<template #label>Total</template>
					<template #value>
						<span class="font-mono">{{ totalConfiguredSources }}</span>
					</template>
				</Badge>
			</div>

			<NewConfiguredSourceButton :disabled-sources="configuredSourcesList" @success="getConfiguredSources()" />
		</div>

		<n-spin :show="loading" class="min-h-32">
			<div v-if="configuredSourcesList.length" class="flex flex-col gap-4">
				<ConfiguredSourceItem
					v-for="source of configuredSourcesList"
					:key="source"
					:source
					class="animate-fade-up"
					@deleted="getConfiguredSources()"
				/>
			</div>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SourceName } from "@/types/incidentManagement/sources.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import { getApiErrorMessage } from "@/utils"
import ConfiguredSourceItem from "./ConfiguredSourceItem.vue"
import NewConfiguredSourceButton from "./NewConfiguredSourceButton.vue"

const { showToolbar = true } = defineProps<{ showToolbar?: boolean }>()

const emit = defineEmits<{
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
	(e: "loaded", value: number): void
}>()

const message = useMessage()
const loading = ref(false)
const configuredSourcesList = ref<SourceName[]>([])
const totalConfiguredSources = computed(() => configuredSourcesList.value.length)

function getConfiguredSources() {
	loading.value = true

	Api.incidentManagement.sources
		.getConfiguredSources()
		.then(res => {
			if (res.data.success) {
				configuredSourcesList.value = res.data?.sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
			emit("loaded", configuredSourcesList.value.length)
		})
}

onBeforeMount(() => {
	getConfiguredSources()

	emit("mounted", {
		reload: getConfiguredSources
	})
})
</script>
