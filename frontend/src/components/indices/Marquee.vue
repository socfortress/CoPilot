<template>
	<div class="flex flex-col">
		<n-card content-class="p-0!" class="overflow-hidden">
			<n-spin :show="loading" content-class="h-10">
				<div v-if="list?.length" class="h-10 overflow-hidden">
					<n-marquee :speed="100">
						<div class="flex h-10 w-max items-center">
							<button
								v-for="item of list"
								:key="item.index"
								type="button"
								class="mx-3 inline-flex shrink-0 cursor-pointer items-center gap-1.5 leading-none whitespace-nowrap"
								:class="healthClass(item.health)"
								title="Click to select"
								@click="emit('click', item)"
							>
								<IndexIcon :health="item.health" color />
								{{ item.index }}
							</button>
						</div>
					</n-marquee>
				</div>
				<template v-else>
					<n-empty
						v-if="!loading"
						class="h-full justify-center"
						description="No indices found"
						:show-icon="false"
					/>
				</template>
			</n-spin>
		</n-card>

		<div v-if="list?.length" class="text-secondary mt-1 flex items-center gap-1 text-xs opacity-50">
			<Icon :name="InfoIcon" :size="14" />
			Click on an index to select
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { IndexStats } from "@/types/indices"
import { NCard, NEmpty, NMarquee, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { IndexHealth } from "@/types/indices"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	indices?: IndexStats[] | null
	customerCodes?: string[]
	loading?: boolean
}>()

const emit = defineEmits<{
	(e: "click", value: IndexStats): void
}>()

const InfoIcon = "carbon:information"
const { indices, customerCodes, loading: parentLoading } = toRefs(props)
const list = ref(indices.value)
const message = useMessage()
const internalLoading = ref(false)
const loading = computed(() => parentLoading.value ?? internalLoading.value)

function healthClass(health: IndexStats["health"]) {
	switch (health) {
		case IndexHealth.YELLOW:
			return "text-warning font-bold"
		case IndexHealth.RED:
			return "text-error font-bold"
		default:
			return ""
	}
}

function getIndices() {
	internalLoading.value = true

	const query = customerCodes.value?.length ? { customerCodes: customerCodes.value } : undefined

	Api.wazuh.indices
		.getIndices(query)
		.then(res => {
			if (res.data.success) {
				list.value = res.data.indices_stats
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					getApiErrorMessage(err as ApiError) ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(getApiErrorMessage(err as ApiError) || "No indices were found.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			internalLoading.value = false
		})
}

watch(indices, val => {
	list.value = val
})

watch(
	() => customerCodes.value,
	() => {
		if (indices.value === undefined) {
			getIndices()
		}
	},
	{ deep: true }
)

onBeforeMount(() => {
	if (indices.value === undefined) {
		getIndices()
	}
})
</script>
