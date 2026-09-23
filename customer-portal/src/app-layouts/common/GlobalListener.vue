<template>
	<slot />
</template>

<script setup lang="ts">
import { useMessage, useNotification } from "naive-ui"
import { useGlobalActions } from "@/composables/common/useGlobalActions"
import { useLoadingBarSetup } from "@/composables/common/useLoadingBarSetup"
import { useReportGenerationStore } from "@/stores/reportGeneration"

const message = useMessage()
const notification = useNotification()

useGlobalActions().init({ message, notification })
useLoadingBarSetup()

// A report queued before a reload is still generating server-side: pick the watch
// back up so its notification is not lost.
useReportGenerationStore().resume()
</script>
