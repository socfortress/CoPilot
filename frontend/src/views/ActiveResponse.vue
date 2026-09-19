<template>
	<div class="page">
		<n-card class="mx-auto max-w-3xl" title="Active Response Wizard" content-class="flex flex-col p-0!" segmented>
			<ActiveResponseWizard />
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import ActiveResponseWizard from "@/components/activeResponse/ActiveResponseWizard.vue"
</script>
