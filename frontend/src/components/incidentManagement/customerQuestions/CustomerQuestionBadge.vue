<template>
	<Badge
		v-if="count"
		type="splitted"
		size="small"
		bright
		color="warning"
		:title="`The customer asked the SOC ${count === 1 ? 'a question' : `${count} questions`} not answered yet`"
		data-testid="customer-question-badge"
	>
		<template #iconLeft>
			<Icon name="carbon:help" :size="13" />
		</template>
		<template #label>Customer question</template>
		<template v-if="count > 1" #value>{{ count }}</template>
	</Badge>
</template>

<script setup lang="ts">
import type { QuestionEntity } from "./customerQuestions"
import { computed, onMounted } from "vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useOpenCustomerQuestions } from "@/composables/useOpenCustomerQuestions"

/** "Customer question" on a case or alert row while the customer waits for the SOC (#1305). */
const { entity, entityId } = defineProps<{
	entity: QuestionEntity
	entityId: number
}>()

const { ensure, countFor } = useOpenCustomerQuestions()
const count = computed(() => countFor(entity, entityId))

onMounted(() => {
	ensure()
})
</script>
