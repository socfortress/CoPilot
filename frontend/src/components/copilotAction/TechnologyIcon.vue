<template>
    <Icon v-if="technology" :name="getTechnologyIcon(technology)" :size />
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { iconFromOs } from "@/utils"

const { technology, size = 14 } = defineProps<{
    technology?: string
    size?: number
}>()

function getTechnologyIcon(tech: string | undefined): string {
    if (!tech) return "carbon:application"

    const techLower = tech.toLowerCase()

    if (techLower.includes("win") || techLower.includes("lin") || techLower.includes("mac")) {
        return iconFromOs(tech)
    }

    if (techLower.includes("wazuh")) {
        return "carbon:security"
    }
    if (techLower.includes("velociraptor")) {
        return "fluent-emoji-high-contrast:eagle"
    }
    if (techLower.includes("network")) {
        return "carbon:network-3"
    }
    if (techLower.includes("cloud")) {
        return "carbon:cloud"
    }

    return "carbon:application"
}
</script>
