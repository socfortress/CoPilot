<template>
	<div class="configured-sources-list">
		<div v-if="showToolbar" class="mb-3 flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon" />
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ totalConfiguredSources }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="actions flex items-center gap-2">
				<NewConfiguredSourceButton
					:disabled-sources="configuredSourcesList"
					@success="getConfiguredSources()"
				/>
			</div>
		</div>
		<n-spin :show="loading" class="min-h-32">
			<div v-if="configuredSourcesList.length" class="list grid-auto-fill-250 grid gap-4">
				<ConfiguredSourceItem
					v-for="source of configuredSourcesList"
					:key="source"
					:source
					class="item-appear item-appear-bottom item-appear-005"
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
import type { SourceName } from "@/types/incidentManagement/sources.d"
import { NButton, NEmpty, NPopover, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
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

const InfoIcon = "carbon:information"
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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
