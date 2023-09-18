<template>
	<div class="indices-marquee">
		<n-spin :show="loading">
			<Vue3Marquee
				class="marquee-wrap"
				:duration="200"
				:pauseOnHover="true"
				:clone="true"
				:gradient="true"
				:gradient-color="[255, 255, 255]"
				gradient-length="10%"
			>
				<span
					v-for="item in indices"
					:key="item.index"
					class="item"
					:class="item.health"
					@click="emit('click', item)"
					title="Click to select"
				>
					<IndexIcon :health="item.health" color />
					{{ item.index }}
				</span>
			</Vue3Marquee>
			<div class="info">
				<i class="mdi mdi-information-outline"></i>
				Click on an index to select
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { type Index } from "@/types/indices.d"
import { Vue3Marquee } from "vue3-marquee"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { NSpin } from "naive-ui"

const emit = defineEmits<{
	(e: "click", value: Index): void
}>()

const props = defineProps<{
	indices: Index[] | null
}>()
const { indices } = toRefs(props)

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
