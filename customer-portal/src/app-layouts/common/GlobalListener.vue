<template>
	<slot />
</template>

<script setup lang="ts">
import { useMessage, useNotification } from "naive-ui"
import { useGlobalActions } from "@/composables/common/useGlobalActions"
import { useLoadingBarSetup } from "@/composables/common/useLoadingBarSetup"

const message = useMessage()
const notification = useNotification()

useGlobalActions().init({ message, notification })
useLoadingBarSetup()
</script>
