<template>
	<n-form :model label-placement="left" label-width="auto">
		<n-form-item label="Protocol" required :show-feedback="false">
			<n-radio-group v-model:value="model.protocol">
				<n-radio-button value="tls">TLS</n-radio-button>
				<n-radio-button value="udp">UDP</n-radio-button>
			</n-radio-group>
		</n-form-item>
		<p class="text-secondary mb-5 text-sm" data-testid="sonicwall-protocol-hint">
			{{ protocolHint }}
		</p>

		<n-form-item label="Hot Data Retention (days)" required>
			<n-input-number v-model:value="model.hot_data_retention" :min="1" :max="90" class="w-full" />
		</n-form-item>

		<n-form-item label="Index Replicas" required>
			<n-input-number v-model:value="model.index_replicas" :min="0" :max="3" class="w-full" />
		</n-form-item>
	</n-form>
</template>

<script setup lang="ts">
import type { SonicwallProtocol } from "./sonicwall"
import { NForm, NFormItem, NInputNumber, NRadioButton, NRadioGroup } from "naive-ui"
import { computed } from "vue"
import { SONICWALL_PROTOCOL_HINTS } from "./sonicwall"

export interface SonicWallModel {
	protocol: SonicwallProtocol
	hot_data_retention: number
	index_replicas: number
}

const model = defineModel<SonicWallModel>("options", { required: true })

const protocolHint = computed(() => SONICWALL_PROTOCOL_HINTS[model.value.protocol])
</script>
