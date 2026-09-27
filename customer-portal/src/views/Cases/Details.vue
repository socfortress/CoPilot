<template>
	<div class="page @container flex flex-col gap-6">
		<CaseDetails v-if="caseId" :case-id />
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import CaseDetails from "@/components/cases/CaseDetails"
import { toNumber } from "@/utils/format"

const route = useRoute()
const caseId = route.params.id ? toNumber(route.params.id as string) : null
</script>
