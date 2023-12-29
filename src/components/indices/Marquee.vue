<template>
	<div class="indices-marquee">
		<n-card content-style="padding:0; " class="overflow-hidden">
			<n-spin :show="loading">
				<Vue3Marquee
					class="marquee-wrap"
					:duration="200"
					:pauseOnHover="true"
					:clone="false"
					:gradient="true"
					:gradient-color="gradientColor"
					gradient-length="10%"
				>
					<span
						v-for="item in indices"
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
		<div class="info" v-if="indices?.length">
			<i class="mdi mdi-information-outline"></i>
			Click on an index to select
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import type { IndexStats } from "@/types/indices.d"
import { Vue3Marquee } from "vue3-marquee"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { NSpin, NCard } from "naive-ui"
import { useThemeStore } from "@/stores/theme"

const emit = defineEmits<{
	(e: "click", value: IndexStats): void
}>()

const props = defineProps<{
	indices: IndexStats[] | null
}>()
const { indices } = toRefs(props)

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
const gradientColor = computed(() => style.value["--bg-color-rgb"].split(", "))
const loading = computed(() => !indices?.value || indices.value === null)
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
