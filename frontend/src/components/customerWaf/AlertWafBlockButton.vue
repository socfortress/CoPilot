<template>
	<template v-if="visible">
		<n-button size="small" type="error" secondary @click="showDialog = true">
			<template #icon>
				<Icon :name="BlockIcon" />
			</template>
			Block at WAF
		</n-button>
		<CustomerWafBlockDialog
			v-model:show="showDialog"
			:customer-code
			:instances
			:initial-target="value"
			:alert-id
		/>
	</template>
</template>

<script setup lang="ts">
// Shown on an alert IP IoC only when the alert's customer has an enabled WAF whose token can
// block (#1168); renders nothing otherwise, so alerts without a WAF look exactly as before.
import { NButton } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import CustomerWafBlockDialog from "./CustomerWafBlockDialog.vue"
import { capabilitiesFromRoles, looksLikeIp, useCustomerWafs } from "./utils"

const { customerCode, value, alertId } = defineProps<{
	customerCode: string
	value: string
	alertId?: number | null
}>()

const BlockIcon = "carbon:locked"
const showDialog = ref(false)
const { instances } = useCustomerWafs(customerCode)

const visible = computed(
	() =>
		looksLikeIp(value) &&
		instances.value.some(i => i.enabled && capabilitiesFromRoles(i.last_verified_role).can_block)
)
</script>
