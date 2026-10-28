<template>
	<div class="text-secondary flex items-center gap-2 text-sm" role="note" data-testid="read-only-notice">
		<Icon name="carbon:view" :size="16" class="shrink-0" />
		<span>{{ $t("common.readOnly.notice") }}</span>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"

/** Where a form or an action would be, for a user who may only read this customer's data (#1312). */
</script>
