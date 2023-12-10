<template>
	<n-card class="unhealthy-indices" segmented>
		<template #header>
			<div class="flex align-center justify-between">
				<span>Unhealthy Indices</span>
				<span class="text-secondary-color font-mono">{{ unhealthyIndices.length }}</span>
			</div>
		</template>
		<n-spin :show="loading">
			<div class="info">
				<n-scrollbar style="max-height: 500px" trigger="none">
					<template v-if="unhealthyIndices && unhealthyIndices.length">
						<div
							v-for="item of unhealthyIndices"
							:key="item.index"
							class="item"
							:class="item.health"
							@click="emit('click', item)"
							title="Click for details"
						>
							<IndexCard :index="item" />
						</div>
					</template>
					<n-empty description="No Unhealthy Indices found" v-else>
						<template #icon>
							<Icon :name="ShieldIcon"></Icon>
						</template>
						<template #extra>Great, all indices are healthy!</template>
					</n-empty>
				</n-scrollbar>
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { type IndexStats, IndexHealth } from "@/types/indices.d"
import IndexCard from "@/components/indices/IndexCard.vue"
import { NSpin, NCard, NEmpty, NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const ShieldIcon = "fluent:shield-task-20-regular"

const emit = defineEmits<{
	(e: "click", value: IndexStats): void
}>()

const props = defineProps<{
	indices: IndexStats[] | null
}>()
const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value === null)

const unhealthyIndices = computed(() =>
	(indices.value || []).filter(
		(index: IndexStats) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED
	)
)
</script>

<style lang="scss" scoped>
.unhealthy-indices {
	.info {
		min-height: 50px;
		.item {
			cursor: pointer;

			&:not(:last-child) {
				@apply mb-3;
			}
		}
	}
}
</style>
