<template>
	<div class="flex flex-col-reverse gap-6 lg:flex-row">
		<div class="border-primary shrink-0 overflow-hidden rounded-lg border-2 bg-white px-4 py-6 lg:px-8 lg:py-10">
			<Preview class="mx-auto" />
		</div>

		<n-card class="grow">
			<SettingsForm />
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import SettingsForm from "./Form.vue"
import Preview from "./Preview.vue"
</script>
