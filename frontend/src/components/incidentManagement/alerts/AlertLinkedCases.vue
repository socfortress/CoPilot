<template>
	<code
		v-for="linkedCase of linkedCases"
		:key="linkedCase.id"
		class="cursor-pointer text-primary-color"
		@click="gotoIncidentManagementCases(linkedCase.id)"
	>
		#{{ linkedCase.id }}
		<Icon :name="LinkIcon" :size="14" class="top-0.5 relative" />
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
