<template>
	<div class="indices-marquee">
		<n-card content-class="!p-0" class="overflow-hidden">
			<n-spin :show="loading" content-class="h-12">
				<Vue3Marquee
					v-if="list?.length"
					class="marquee-wrap"
					:duration="(list?.length || 0) * 1"
					:pause-on-hover="true"
					:clone="false"
					:gradient="true"
					:gradient-color="gradientColor"
					gradient-length="10%"
				>
					<span
						v-for="item of list"
						:key="item.index"
						class="item flex items-center gap-2"
						:class="item.health"
						title="Click to select"
						@click="emit('click', item)"
					>
						<IndexIcon :health="item.health" color />
						{{ item.index }}
					</span>
				</Vue3Marquee>
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
		<div v-if="list?.length" class="info">
			<i class="mdi mdi-information-outline"></i>
			Click on an index to select
		</div>
	</div>
</template>

<script setup lang="ts">
import type { IndexStats } from "@/types/indices.d"
import Api from "@/api"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { useThemeStore } from "@/stores/theme"
import { NCard, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import { Vue3Marquee } from "vue3-marquee"

const props = defineProps<{
	indices?: IndexStats[] | null
}>()

const emit = defineEmits<{
	(e: "click", value: IndexStats): void
}>()

const { indices } = toRefs(props)
const list = ref(indices.value)
const message = useMessage()
const style = computed(() => useThemeStore().style)
const gradientColor = computed(() => style.value["bg-color-rgb"].split(", "))
const loading = ref(false)

function getIndices() {
	loading.value = true

	Api.indices
		.getIndices()
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
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(err.response?.data?.message || "No indices were found.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

watch(indices, val => {
	list.value = val
})

onBeforeMount(() => {
	if (indices.value === undefined) {
		getIndices()
	}
})
</script>

<style lang="scss" scoped>
.indices-marquee {
	.info {
		opacity: 0.5;
		@apply text-xs;
		margin-top: 5px;
	}
	.marquee-wrap {
		height: 100%;
		transform: translate3d(0, 0, 0);

		:deep() {
			.marquee {
				transform: translate3d(0, 0, 0);
			}
			.overlay {
				&:after {
					right: -1px;
				}
			}
		}

		.item {
			padding: 10px 20px;
			cursor: pointer;
			line-height: 1;

			&.green {
				i {
					color: var(--success-color);
				}
			}
			&.yellow {
				color: var(--warning-color);
				font-weight: bold;
			}
			&.red {
				color: var(--error-color);
				font-weight: bold;
			}
		}
	}
}
</style>
