<template>
	<n-form class="flex flex-col gap-5" :model="options" :rules="rules" ref="formRef">
		<n-form-item label="Protocol" label-placement="left" :show-feedback="false" size="small" path="protocol">
			<n-select v-model:value="options.protocol" :options="protocolOptions" />
		</n-form-item>
		<div class="flex items-end justify-between gap-5">
			<n-form-item label="Hot Data Retention (days)" size="small" path="hot_data_retention">
				<n-input-number
					v-model:value="options.hot_data_retention"
					placeholder="Input time in days"
					:min="1"
					:step="1"
					:precision="0"
				/>
			</n-form-item>
			<n-form-item label="Index Replicas" size="small" path="index_replicas">
				<n-input-number
					v-model:value="options.index_replicas"
					placeholder="Input value"
					:min="0"
					:step="1"
					:precision="0"
				/>
			</n-form-item>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import { NFormItem, NSelect, NForm, NInputNumber, type FormRules, type FormItemRule } from "naive-ui"

export interface FortinetModel {
	protocol: "tcp" | "udp"
	hot_data_retention: number
	index_replicas: number
}

const options = defineModel<FortinetModel>("options", {
	default: {
		protocol: "tcp",
		hot_data_retention: 1,
		index_replicas: 0
	}
})

const protocolOptions = [
	{ value: "tcp", label: "TCP" },
	{ value: "udp", label: "UDP" }
]

const rules: FormRules = {
	hot_data_retention: {
		message: "Field required",
		trigger: ["input", "blur"],
		validator: (rule: FormItemRule, value: string): boolean => {
			return value !== null
		}
	},
	index_replicas: {
		message: "Field required",
		trigger: ["input", "blur"],
		validator: (rule: FormItemRule, value: string): boolean => {
			return value !== null
		}
	}
}
</script>
