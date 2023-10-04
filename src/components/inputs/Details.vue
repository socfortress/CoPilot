<template>
	<div class="input-details-box" v-loading="loading" :class="{ active: currentInput }">
		<div class="box-header">
			<div class="title">
				<span v-if="currentInput">Below the details for input</span>
				<span v-else>Select an input to see the details</span>
			</div>
			<div class="select-box" v-if="inputs && inputs.length">
				<el-select v-model="currentInput" placeholder="Inputs list" clearable value-key="input" filterable>
					<el-option v-for="input in inputs" :key="input.id" :label="input.title" :value="input"></el-option>
				</el-select>
			</div>
		</div>
		<div class="details-box" v-if="currentInput">
			<div class="info">
				<InputCard :input="currentInput" showActions @delete="clearCurrentInput()" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { type Inputs } from "@/types/graylog.d"
import InputCard from "@/components/inputs/InputCard.vue"

type InputModel = Inputs | null | ""

const emit = defineEmits<{
	(e: "update:modelValue", value: InputModel): void
}>()

const props = defineProps<{
	inputs: Inputs[] | null
	modelValue: InputModel
}>()
const { inputs, modelValue } = toRefs(props)

const loading = computed(() => !inputs?.value || inputs.value === null)

const currentInput = computed<InputModel>({
	get() {
		return modelValue.value
	},
	set(value) {
		emit("update:modelValue", value)
	}
})

function clearCurrentInput() {
	currentInput.value = null
}

onBeforeMount(() => {
	// getShards()
})
</script>

<style lang="scss" scoped>
.input-details-box {
	padding: var(--size-5) var(--size-6);
	border: 2px solid transparent;

	&.active {
		border-color: var(--primary-color);
	}

	.box-header {
		display: flex;
		align-items: center;

		.title {
			margin-right: var(--size-4);
		}

		.select-box {
			.el-select {
				min-width: var(--size-fluid-9);
				max-width: 100%;
			}
		}
	}

	.details-box {
		margin-top: var(--size-6);

		.shards {
			margin-top: var(--size-4);

			.shard-state {
				font-weight: bold;
				&.STARTED {
					color: var(--success-color);
				}
				&.UNASSIGNED {
					color: var(--warning-color);
				}
			}
		}
	}

	@media (max-width: 1000px) {
		.box-header {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--size-2);
			.select-box {
				width: 100%;
				.el-select {
					min-width: 100%;
				}
			}
		}
	}
}
</style>
