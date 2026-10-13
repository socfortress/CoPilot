<template>
	<span class="inline-flex flex-wrap items-baseline gap-x-2" data-testid="customer-name" :title="code ?? undefined">
		<span>{{ name }}</span>
		<span v-if="code && name !== code" class="text-secondary font-mono text-xs">{{ code }}</span>
	</span>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useCustomers } from "@/composables/common/useCustomers"

/** A customer by name, with its code beside it (the code is what support and the SOC quote). */
const { code } = defineProps<{ code: string | null | undefined }>()

const { customerName } = useCustomers()
const name = computed(() => customerName(code) || "—")
</script>
