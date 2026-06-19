<template>
	<n-card segmented content-class="pr-1!">
		<template #header>
			<div class="flex items-center justify-between">
				<span>Unhealthy Indices</span>
				<span class="text-secondary font-mono">{{ unhealthyIndices.length }}</span>
			</div>
		</template>
		<n-spin :show="loading" class="min-h-14">
			<n-scrollbar class="max-h-125" trigger="none" content-class="pr-5!">
				<template v-if="unhealthyIndices && unhealthyIndices.length">
					<div class="flex flex-col gap-3">
						<div
							v-for="item of unhealthyIndices"
							:key="item.index"
							class="cursor-pointer"
							title="Click for details"
							@click="emit('click', item)"
						>
							<IndexCard :index="item" />
						</div>
					</div>
				</template>
				<n-empty v-else description="No Unhealthy Indices found">
					<template #icon>
						<Icon :name="ShieldIcon" />
					</template>
					<template #extra>Great, all indices are healthy!</template>
				</n-empty>
			</n-scrollbar>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import type { IndexStats } from "@/types/indices.d"
import { NCard, NEmpty, NScrollbar, NSpin } from "naive-ui"
import { computed, toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import IndexCard from "@/components/indices/IndexCard.vue"
import { IndexHealth } from "@/types/indices.d"

const props = defineProps<{
	indices: IndexStats[] | null
}>()

const emit = defineEmits<{
	(e: "click", value: IndexStats): void
}>()

const ShieldIcon = "fluent:shield-task-20-regular"

const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value === null)

const unhealthyIndices = computed(() =>
	(indices.value || []).filter(
		(index: IndexStats) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED
	)
)
</script>
