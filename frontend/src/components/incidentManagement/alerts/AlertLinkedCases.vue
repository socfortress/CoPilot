<template>
	<code
		v-for="linkedCase of linkedCases"
		:key="linkedCase.id"
		class="text-primary cursor-pointer"
		@click="gotoIncidentManagementCases(linkedCase.id)"
	>
		#{{ linkedCase.id }}
		<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
	</code>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { computed, toRefs } from "vue"

const props = defineProps<{ alert: Alert }>()
const { alert } = toRefs(props)

const LinkIcon = "carbon:launch"

const { gotoIncidentManagementCases } = useGoto()
const linkedCases = computed(() => alert.value.linked_cases)
</script>
