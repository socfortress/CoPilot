<template>
	<div class="unhealthy-indices">
		<h4 class="title mb-5">
			Unhealthy Indices
			<small class="opacity-50">({{ unhealthyIndices.length }})</small>
		</h4>
		<n-spin :show="loading">
			<div class="info">
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
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { type Index, IndexHealth } from "@/types/indices.d"
import IndexCard from "@/components/indices/IndexCard.vue"
import { NSpin } from "naive-ui"

const emit = defineEmits<{
	(e: "click", value: Index): void
}>()

const props = defineProps<{
	indices: Index[] | null
}>()
const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value === null)

const unhealthyIndices = computed(() =>
	(indices.value || []).filter(
		(index: Index) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED
	)
)
</script>

<style lang="scss" scoped>
.unhealthy-indices {
	@apply py-5 px-6;

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
