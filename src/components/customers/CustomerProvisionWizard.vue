<template>
	<div class="customer-provision-wizard">
		<n-steps :current="current" size="small">
			<n-step title="Provisioning" />
			<n-step title="Graylog" />
			<n-step title="Subscription" />
			<n-step title="Wazuh Worker">
				<template #icon>
					<Icon :name="DetailsIcon"></Icon>
				</template>
			</n-step>
		</n-steps>

		<slot name="additionalActions"></slot>
	</div>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import { NSteps, NStep, useMessage } from "naive-ui"
import type { CustomerMeta } from "@/types/customers.d"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: CustomerMeta): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const props = defineProps<{
	customerCode: string
	customerName: string
}>()
const { customerCode, customerName } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"

const loading = ref(false)
const message = useMessage()
const current = ref<number>(0)
</script>
