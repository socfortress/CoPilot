<template>
    <div class="page-table scrollable only-y" id="affix-container">
        <div class="page-header">
            <h1>Table</h1>
            <h4>simple table</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Tables</el-breadcrumb-item>
                <el-breadcrumb-item>Table</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="table-box card-base card-shadow--medium scrollable only-x">
            <table class="styled striped">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>First name</th>
                        <th>Last name</th>
                        <th>Email</th>
                        <th>Gender</th>
                        <th>IP address</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in list" :key="item.id">
                        <td>{{ item.id }}</td>
                        <td>{{ item.first_name }}</td>
                        <td>{{ item.last_name }}</td>
                        <td>{{ item.email }}</td>
                        <td>{{ item.gender }}</td>
                        <td>{{ item.ip_address }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import Affix from "@/components/Affix.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Table",
    data() {
        return {
            affixEnabled: true,
            list: [
                {
                    id: 1,
                    first_name: "Fidela",
                    last_name: "MacLaverty",
                    email: "fmaclaverty0@scribd.com",
                    gender: "Female",
                    ip_address: "165.9.197.163"
                },
                {
                    id: 2,
                    first_name: "Garrard",
                    last_name: "Inge",
                    email: "ginge1@51.la",
                    gender: "Male",
                    ip_address: "138.87.225.97"
                },
                {
                    id: 3,
                    first_name: "Clayborn",
                    last_name: "Blencoe",
                    email: "cblencoe2@cbc.ca",
                    gender: "Male",
                    ip_address: "237.146.154.222"
                },
                {
                    id: 4,
                    first_name: "Reinaldos",
                    last_name: "Briiginshaw",
                    email: "rbriiginshaw3@mashable.com",
                    gender: "Male",
                    ip_address: "35.148.222.21"
                },
                {
                    id: 5,
                    first_name: "Abigael",
                    last_name: "Richmond",
                    email: "arichmond4@shinystat.com",
                    gender: "Female",
                    ip_address: "135.221.192.85"
                },
                {
                    id: 6,
                    first_name: "Elna",
                    last_name: "Deboick",
                    email: "edeboick5@4shared.com",
                    gender: "Female",
                    ip_address: "53.209.210.199"
                },
                {
                    id: 7,
                    first_name: "Lanna",
                    last_name: "Prentice",
                    email: "lprentice6@oracle.com",
                    gender: "Female",
                    ip_address: "198.34.29.215"
                },
                {
                    id: 8,
                    first_name: "Sheffie",
                    last_name: "Fellgett",
                    email: "sfellgett7@ow.ly",
                    gender: "Male",
                    ip_address: "219.29.191.217"
                },
                {
                    id: 9,
                    first_name: "Mamie",
                    last_name: "Calkin",
                    email: "mcalkin8@oakley.com",
                    gender: "Female",
                    ip_address: "69.0.235.44"
                },
                {
                    id: 10,
                    first_name: "Saudra",
                    last_name: "Dunniom",
                    email: "sdunniom9@ameblo.jp",
                    gender: "Female",
                    ip_address: "182.157.218.101"
                },
                {
                    id: 11,
                    first_name: "Sile",
                    last_name: "Rudeforth",
                    email: "srudefortha@jimdo.com",
                    gender: "Female",
                    ip_address: "26.176.141.77"
                },
                {
                    id: 12,
                    first_name: "Nichole",
                    last_name: "Verrell",
                    email: "nverrellb@fotki.com",
                    gender: "Male",
                    ip_address: "196.88.10.200"
                },
                {
                    id: 13,
                    first_name: "Portie",
                    last_name: "Sporle",
                    email: "psporlec@jimdo.com",
                    gender: "Male",
                    ip_address: "1.157.38.106"
                },
                {
                    id: 14,
                    first_name: "Cosme",
                    last_name: "Pauling",
                    email: "cpaulingd@nytimes.com",
                    gender: "Male",
                    ip_address: "209.203.192.28"
                },
                {
                    id: 15,
                    first_name: "Elisha",
                    last_name: "Tipperton",
                    email: "etippertone@discovery.com",
                    gender: "Male",
                    ip_address: "219.8.155.219"
                },
                {
                    id: 16,
                    first_name: "Skyler",
                    last_name: "Schwandermann",
                    email: "sschwandermannf@devhub.com",
                    gender: "Male",
                    ip_address: "150.227.132.171"
                },
                {
                    id: 17,
                    first_name: "Anallise",
                    last_name: "Tuftin",
                    email: "atufting@ustream.tv",
                    gender: "Female",
                    ip_address: "98.234.28.78"
                },
                {
                    id: 18,
                    first_name: "Janka",
                    last_name: "Hissie",
                    email: "jhissieh@etsy.com",
                    gender: "Female",
                    ip_address: "125.255.226.56"
                },
                {
                    id: 19,
                    first_name: "Tonie",
                    last_name: "Swede",
                    email: "tswedei@constantcontact.com",
                    gender: "Female",
                    ip_address: "111.113.252.139"
                },
                {
                    id: 20,
                    first_name: "Marve",
                    last_name: "Egle",
                    email: "meglej@scribd.com",
                    gender: "Male",
                    ip_address: "202.240.145.168"
                }
            ]
        }
    },
    components: {
        Affix
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-table {
    padding-left: 20px;
    padding-right: 15px;
    padding-bottom: 20px;
}
.table-box {
    overflow: auto;
}
</style>
