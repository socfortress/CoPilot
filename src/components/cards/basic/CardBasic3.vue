<template>
	<n-card>
		<template #cover>
			<img :src="image" width="900" height="400" />
		</template>
		<template #header>
			{{ title }}
		</template>
		<template #default>
			<p>
				{{ text }}
			</p>
		</template>
		<template #action>
			<n-collapse>
				<n-collapse-item title="Info" name="1">
					<div>{{ info }}</div>
				</n-collapse-item>
			</n-collapse>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NCollapse, NCollapseItem } from "naive-ui"

const image = faker.image.urlPicsumPhotos({ width: 900, height: 400 })
const title = faker.lorem.sentence({ min: 2, max: 5 })
const text = faker.lorem.paragraph()
const info = faker.lorem.paragraph()
</script>
