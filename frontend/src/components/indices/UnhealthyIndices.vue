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
							title="Click for details"
							@click="emit('click', item)"
						>
							<IndexCard :index="item" />
						</div>
					</template>
					<n-empty v-else description="No Unhealthy Indices found">
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
import Icon from "@/components/common/Icon.vue"
import IndexCard from "@/components/indices/IndexCard.vue"
import { IndexHealth, type IndexStats } from "@/types/indices.d"
import { NCard, NEmpty, NScrollbar, NSpin } from "naive-ui"
import { computed, toRefs } from "vue"

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
