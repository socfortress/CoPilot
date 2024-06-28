<template>
	<div class="indices-marquee">
		<n-card content-style="padding:0; " class="overflow-hidden">
			<n-spin :show="loading">
				<Vue3Marquee
					class="marquee-wrap"
					:duration="(list?.length || 0) * 1"
					:pauseOnHover="true"
					:clone="false"
					:gradient="true"
					:gradient-color="gradientColor"
					gradient-length="10%"
				>
					<span
						v-for="item in list"
						:key="item.index"
						class="item flex items-center gap-2"
						:class="item.health"
						@click="emit('click', item)"
						title="Click to select"
					>
						<IndexIcon :health="item.health" color />
						{{ item.index }}
					</span>
				</Vue3Marquee>
			</n-spin>
		</n-card>
		<div class="info" v-if="list?.length">
			<i class="mdi mdi-information-outline"></i>
			Click on an index to select
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs, watch, onBeforeMount } from "vue"
import type { IndexStats } from "@/types/indices.d"
import { Vue3Marquee } from "vue3-marquee"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { NSpin, NCard, useMessage } from "naive-ui"
import { useThemeStore } from "@/stores/theme"
import Api from "@/api"

const emit = defineEmits<{
	(e: "click", value: IndexStats): void
}>()

const props = defineProps<{
	indices?: IndexStats[] | null
}>()
const { indices } = toRefs(props)

const list = ref(indices.value)

watch(indices, val => {
	list.value = val
})

const message = useMessage()
const style = computed(() => useThemeStore().style)
const gradientColor = computed(() => style.value["bg-color-rgb"].split(", "))
const loading = computed(() => !list?.value || list.value === null)

function getIndices() {
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
}

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
		height: 45px;
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
