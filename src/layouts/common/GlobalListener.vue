<template>
	<slot />
</template>

<script setup>
import { useMessage } from "naive-ui"
import { useGlobalActions } from "@/composables/useGlobalActions"

const message = useMessage()

useGlobalActions().init({ message })
</script>
