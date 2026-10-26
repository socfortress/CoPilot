<template>
	<div
		class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
		data-testid="exposure-disabled"
	>
		<Icon name="carbon:security" :size="28" class="text-tertiary" />
		<p class="text-default font-semibold">{{ $t("exposure.disabled.title") }}</p>
		<p class="text-secondary max-w-md text-sm">
			{{ $t("exposure.disabled.text") }}
		</p>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
</script>
