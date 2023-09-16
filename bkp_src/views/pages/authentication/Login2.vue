<template>
    <div class="login-page flex">
        <div class="box grow scrollable align-vertical side-box box-left">
            <div class="align-vertical-middle wrapper text-center">
                <img class="image-logo" src="@/assets/images/logo.svg" alt="logo-left" />
                <h1 class="h-big">Pragmatic</h1>
                <p class="p-50">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus ullamcorper nisl erat, vel convallis elit fermentum
                    pellentesque. Sed mollis velit facilisis facilisis viverra.
                </p>
            </div>
        </div>
        <div class="box grow scrollable align-vertical side-box box-right">
            <div class="align-vertical-middle wrapper">
                <form class="form-box" @submit.prevent="login">
                    <h2>Log in to your account</h2>
                    <p class="mb-40">Go to the dashboard</p>

                    <div class="field-box">
                        <input type="username" name="username" placeholder="Username" v-model="username" />
                    </div>
                    <div class="field-box">
                        <input type="password" name="password" placeholder="Password" v-model="password" />
                    </div>
                    <div>
                        <el-checkbox>Remember me </el-checkbox>
                    </div>
                    <div>
                        <router-link to="/forgot-password">Lost Password?</router-link>
                    </div>
                    <div>
                        <button class="login-btn">Login</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "Login2",
    data() {
        return {
            username: "",
            password: ""
        }
    },
    methods: {}
})
</script>

<style lang="scss">
@import "@/assets/scss/_variables.scss";

.login-page {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 0 !important;

    .side-box {
        .wrapper {
            width: 100%;
            box-sizing: border-box;
            padding: 20px;
        }
    }

    .box-left {
        background-image: url("../../../assets/images/login2.jpg");
        background-size: cover;
        background-position: 50% 50%;

        .wrapper {
            .image-logo {
                width: 90%;
                max-width: 100px;
                margin-top: 20px;
            }
        }
    }
    .box-right {
        background: white;
    }

    .form-box {
        width: 100%;
        max-width: 340px;
        padding: 30px;
        box-sizing: border-box;
        margin: 20px auto;
        //background: transparent;

        a {
            font-size: 14px;
            color: $text-color-primary;
            text-decoration: none;
            font-weight: 500;
        }

        .image-logo {
            width: 80px;
            margin: 0px auto;
            margin-bottom: 70px;
            display: block;
        }

        .field-box {
            margin-bottom: 10px;
            input {
                width: 100%;
                box-sizing: border-box;
                border-radius: 10px;
                padding: 10px 20px;
                outline: none;
                border: 1px solid $text-color-primary;
            }
        }

        .login-btn {
            margin-top: 20px;
            width: 100%;
            background-color: $text-color-primary;
            color: #fff;
            font-weight: bold;
            border-radius: 10px;
            padding: 10px 20px;
            outline: none;
            border: none;
        }
    }
}

@media (max-width: 1200px) {
    .login-page {
        .box-left {
            .wrapper {
                .h-big {
                    font-size: 50px;
                }
            }
        }
    }
}
@media (max-width: 900px) {
    .login-page {
        .box-left {
            .wrapper {
                .h-big {
                    font-size: 30px;
                }
            }
        }
    }
}
@media (max-width: 768px) {
    .login-page {
        display: block;
        overflow: auto;

        .side-box {
            display: block;
        }
    }
}
</style>
