<template>
    <div class="profile-gallery">
        <viewer :images="images" class="images-list" :class="{ ['box-margins']: !!boxMargins }">
            <!--<img v-for="i in 50" :key="i" v-lazy="'/static/images/gallery/photo-'+i+'.jpg'" alt="gallery image">-->
            <!-- lazy load -->
            <img v-for="i in 50" :key="i" :src="'/static/images/gallery/photo-' + i + '.jpg'" alt="gallery image" />
        </viewer>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ProfileGallery",
    props: ["boxMargins"],
    data() {
        return {
            images: []
        }
    }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.profile-gallery {
    /*.images-list {
		margin: 0 -10px;
		margin-top: -10px;

		img {
			cursor: pointer;
			width: calc(50% - 20px);
			border-radius: 10px;
			max-width: 278px;
			float: left;
			box-sizing: border-box;
			margin: 10px;
			border: 5px solid #fff;
			box-shadow: 0px 7px 20px -7px rgba(0, 0, 0, 0.55);
			transition: all .5s;

			&:hover {
				box-shadow: none;
				transform: translateY(3px);
			}
		}
	}*/

    .images-list {
        overflow: hidden;
        margin: -1%;
        &.box-margins {
            margin: 1%;
        }

        img {
            cursor: pointer;
            width: 18%;
            border-radius: 10px;
            //max-width: 278px;
            float: left;
            box-sizing: border-box;
            margin: 1%;
            border: 5px solid #fff;
            box-shadow: 0px 7px 20px -7px rgba(0, 0, 0, 0.55);
            transition: all 0.5s;

            &:hover {
                box-shadow: none;
                transform: translateY(3px);
            }
        }
    }
}

@media (max-width: 768px) {
    .profile-gallery {
        .images-list {
            margin: -1.5%;
            &.box-margins {
                margin: 1.5%;
            }

            img {
                width: 30.3%;
                margin: 1.5%;
            }
        }
    }
}
@media (max-width: 480px) {
    .profile-gallery {
        .images-list {
            margin: -2%;
            &.box-margins {
                margin: 2%;
            }

            img {
                width: 46%;
                margin: 2%;
            }
        }
    }
}
@media (max-width: 360px) {
    .profile-gallery {
        .images-list {
            margin: -2%;
            &.box-margins {
                margin: 2%;
            }

            img {
                width: 96%;
                margin: 2%;
            }
        }
    }
}
</style>
