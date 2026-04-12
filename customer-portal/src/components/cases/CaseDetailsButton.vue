<template>
	<div>
		<n-button @click="showDetails = true">View Details</n-button>

		<n-modal
			v-model:show="showDetails"
			title="Case Details"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
		>
			<CaseDetails :case-id />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import CaseDetails from "./CaseDetails"

defineProps<{
	caseId: number | null
}>()

const showDetails = ref(false)
</script>
