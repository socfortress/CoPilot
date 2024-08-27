<template>
	<ThreatIntelProcessEvaluationProvider :processName v-slot="{ openEvaluation }">
		<code class="cursor-pointer text-primary-color" @click="openEvaluation()">
			{{ processName }}
			<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
		</code>
	</ThreatIntelProcessEvaluationProvider>
</template>

<script setup lang="ts">
import ThreatIntelProcessEvaluationProvider from "./ThreatIntelProcessEvaluationProvider.vue"
import Icon from "@/components/common/Icon.vue"

const { processName } = defineProps<{
	processName: string
}>()

const LinkIcon = "carbon:launch"
</script>
