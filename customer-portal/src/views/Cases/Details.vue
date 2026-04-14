<template>
	<div class="page @container flex flex-col gap-6">
		<CaseDetails v-if="caseId" :case-id @deleted="handleDeleted" />
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import CaseDetails from "@/components/cases/CaseDetails"
import { useNavigation } from "@/composables/common/useNavigation"
import { toNumber } from "@/utils/format"

const route = useRoute()
const { routeCasesList } = useNavigation()
const caseId = route.params.id ? toNumber(route.params.id as string) : null

function handleDeleted() {
	routeCasesList().navigate()
}
</script>
