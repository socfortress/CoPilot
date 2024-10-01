<template>
	<slot />
</template>

<script setup lang="ts">
import { useGlobalActions } from "@/composables/useGlobalActions"
import { useMessage, useNotification } from "naive-ui"

const message = useMessage()
const notification = useNotification()

useGlobalActions().init({ message, notification })
</script>
