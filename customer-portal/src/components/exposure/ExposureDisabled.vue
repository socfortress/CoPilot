<template>
	<div
		class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
		data-testid="exposure-disabled"
	>
		<Icon name="carbon:security" :size="28" class="text-tertiary" />
		<p class="font-semibold">Exposure is not available yet</p>
		<p class="text-secondary max-w-md text-sm">
			Your SOC has not published the vulnerabilities and compliance across your agents. Each agent's page still
			shows its own. Ask your SOC contact if you would like to see them here.
		</p>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
</script>
