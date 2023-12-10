<template>
	<slot />
</template>

<script setup>
import { useMessage, useNotification } from "naive-ui"
import { useGlobalActions } from "@/composables/useGlobalActions"

const message = useMessage()
const notification = useNotification()

useGlobalActions().init({ message, notification })
</script>
