<template>
	<div class="grid gap-2 grid-auto-flow-200">
		<KVCard v-for="(value, key) of alert.alert_context" :key="key">
			<template #key>{{ key }}</template>
			<template #value>
				<template v-if="key === 'process_name' && value && value !== '-'">
					<SocAlertItemEvaluation :process-name="value + ''" />
				</template>
				<template v-else>
					{{ value ?? "-" }}
				</template>
			</template>
		</KVCard>
	</div>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import KVCard from "@/components/common/KVCard.vue"
import { defineAsyncComponent } from "vue"
const SocAlertItemEvaluation = defineAsyncComponent(() => import("./SocAlertItemEvaluation.vue"))

const { alert } = defineProps<{
	alert: SocAlert
}>()
</script>
