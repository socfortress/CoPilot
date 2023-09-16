<template>
	<n-card :title="title">
		<template #cover>
			<img :src="image" width="900" height="400" />
		</template>
		<template #default>
			<p>
				{{ text }}
			</p>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard } from "naive-ui"

const image = faker.image.urlPicsumPhotos({ width: 900, height: 400 })
const title = faker.lorem.sentence({ min: 2, max: 5 })
const text = faker.lorem.paragraph()
</script>
