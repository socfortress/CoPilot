<template>
	<n-card
		:title="title"
		:segmented="{
			content: true,
			footer: 'soft'
		}"
	>
		<template #default>
			<p>
				{{ text }}
			</p>
		</template>
		<template #action>
			<div class="flex justify-around">
				<Icon :size="20" :name="CheckIcon"></Icon>
				<Icon :size="20" :name="StarIcon"></Icon>
				<Icon :size="20" :name="ShieldIcon"></Icon>
				<Icon :size="20" :name="PremiumIcon"></Icon>
				<Icon :size="20" :name="EcoIcon"></Icon>
			</div>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const CheckIcon = "fluent:checkmark-starburst-16-regular"
const StarIcon = "fluent:star-16-regular"
const ShieldIcon = "fluent:shield-keyhole-16-regular"
const PremiumIcon = "fluent:premium-24-regular"
const EcoIcon = "material-symbols:eco-outline"

const title = faker.lorem.sentence({ min: 2, max: 5 })
const text = faker.lorem.paragraph()
</script>
