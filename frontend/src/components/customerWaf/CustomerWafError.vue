<template>
	<n-alert type="error" :bordered="false">
		<div class="flex flex-col gap-1 text-sm">
			<span>{{ message }}</span>
			<span v-if="hint" class="text-xs opacity-80">{{ hint }}</span>
		</div>
	</n-alert>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NAlert } from "naive-ui"
import { computed } from "vue"
import { getApiErrorMessage } from "@/utils"
import { reasonHint } from "./utils"

const { error } = defineProps<{ error: ApiError }>()

const message = computed(() => getApiErrorMessage(error) || "The WAF request failed.")
const hint = computed(() => reasonHint((error.response?.data as { reason?: string } | undefined)?.reason))
</script>
