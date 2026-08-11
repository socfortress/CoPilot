<template>
	<n-button secondary @click="showManualSend = true">
		<template #icon>
			<Icon :name="SendIcon" :size="14" />
		</template>
		Send to channel
	</n-button>

	<ManualSendDialog
		v-model:show="showManualSend"
		entity-type="alert"
		:entity-id="alert.id"
		:customer-code="alert.customer_code"
	/>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts"
import { NButton } from "naive-ui"
import { ref, toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import ManualSendDialog from "@/components/notifications/ManualSendDialog.vue"

const props = defineProps<{ alert: Alert }>()
const { alert } = toRefs(props)

const SendIcon = "carbon:send-alt"
const showManualSend = ref(false)
</script>
