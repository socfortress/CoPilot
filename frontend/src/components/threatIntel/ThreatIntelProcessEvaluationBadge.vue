<template>
	<ThreatIntelProcessEvaluationProvider v-slot="{ openEvaluation }" :process-name>
		<code class="text-primary cursor-pointer" @click="openEvaluation()">
			{{ processName }}
			<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
		</code>
	</ThreatIntelProcessEvaluationProvider>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import ThreatIntelProcessEvaluationProvider from "./ThreatIntelProcessEvaluationProvider.vue"

const { processName } = defineProps<{
	processName: string
}>()

const LinkIcon = "carbon:launch"
</script>
