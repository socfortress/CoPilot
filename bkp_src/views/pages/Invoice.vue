<template>
    <div class="page-invoice scrollable">
        <div class="toolbar">
            <el-button class="animate__animated animate__fadeInRight" type="primary" plain size="small"
                ><i class="mdi mdi-cart"></i> Check out</el-button
            >
            <el-button class="animate__animated animate__fadeInRight" plain size="small" @click="print"
                ><i class="mdi mdi-printer"></i> Print</el-button
            >
        </div>

        <div class="invoice bg-white black-text">
            <div class="invoice-top">
                <div class="logo">
                    <img src="@/assets/images/logo.svg" alt="logo" />
                </div>
                <div class="info">
                    <h2>John Wick</h2>
                    <p>jwick@email.com<br />777-777-7777</p>
                </div>
                <!--End Info-->
                <div class="title">
                    <h1>Invoice #1337</h1>
                    <p>Issued: May 23, 2018<br />Payment Due: June 23, 2018</p>
                </div>
                <!--End Title-->
            </div>
            <!--End InvoiceTop-->

            <hr />

            <div class="invoice-middle">
                <div class="clientlogo">
                    <img src="@/assets/images/avatar.jpg" alt="client logo" />
                </div>
                <div class="info">
                    <h2>Client Name</h2>
                    <p>john.doe@email.com<br />555-555-5555</p>
                </div>

                <div class="project">
                    <h2>Project Description</h2>
                    <p>
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam in diam sit amet felis ultricies ultricies vitae et
                        tortor. Proin dapibus justo felis, ut imperdiet lacus accumsan quis.
                    </p>
                </div>
            </div>
            <!--End Invoice Mid-->

            <div class="invoice-bottom">
                <table>
                    <thead>
                        <tr>
                            <th>Item Description</th>
                            <th>Hours</th>
                            <th>Rate</th>
                            <th>Sub-total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Service 1</td>
                            <td>6</td>
                            <td>$55</td>
                            <td>$330.00</td>
                        </tr>

                        <tr>
                            <td>Service 2</td>
                            <td>3</td>
                            <td>$75</td>
                            <td>$225.00</td>
                        </tr>

                        <tr>
                            <td>Service 3</td>
                            <td>4</td>
                            <td>$75</td>
                            <td>$300.00</td>
                        </tr>

                        <tr>
                            <td>Service 4</td>
                            <td>250</td>
                            <td>$65</td>
                            <td>$16,250.00</td>
                        </tr>

                        <tr>
                            <td>Service 5</td>
                            <td>10</td>
                            <td>$70</td>
                            <td>$700.00</td>
                        </tr>

                        <tr>
                            <td></td>
                            <td>HST</td>
                            <td>13%</td>
                            <td>$2,314.65</td>
                        </tr>
                    </tbody>
                    <tfoot>
                        <tr>
                            <td></td>
                            <td></td>
                            <td class="Rate"><h2>Total</h2></td>
                            <td class="payment"><h2>$20,119.65</h2></td>
                        </tr>
                    </tfoot>
                </table>

                <div class="legalcopy flex mt-20">
                    <p class="legal box grow mr-20 mt-0">
                        <strong>Thank you for your business!</strong>  Payment is expected within 31 days; please process this invoice
                        within that time. There will be a 5% interest charge per month on late invoices.
                    </p>
                    <el-button type="primary" plain size="small" style="height: 32px"><i class="mdi mdi-cart"></i> Check out</el-button>
                </div>
            </div>
            <!--End Invoice-->
        </div>
    </div>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "Invoice",
    methods: {
        print() {
            window.print()
        }
    }
})
</script>

<style lang="scss">
@import "../../assets/scss/_variables";

.page-invoice {
    .toolbar {
        max-width: 794px;
        margin: 0 auto;
        text-align: right;
        margin-bottom: 20px;
    }

    .invoice {
        background: white;
        width: 100%;
        max-width: 794px;
        min-height: 1123px;
        margin: 0 auto;
        padding: 2em;
        box-sizing: border-box;
        box-shadow: 0px 8px 8px -8px rgba(0, 0, 0, 0.3);
        margin-bottom: 30px;

        hr {
            border: 1px solid rgba(0, 0, 0, 0.05);
        }

        .invoice-top {
            overflow: hidden;
            margin-bottom: 30px;

            .logo {
                float: left;
                height: 60px;
                width: 60px;
                box-sizing: border-box;
                border-radius: 50%;
                overflow: hidden;
                background: rgba(0, 0, 0, 0.07);
                text-align: center;

                img {
                    height: 80%;
                    margin-top: 10%;
                }
            }
            .info {
                display: block;
                float: left;
                margin-left: 20px;
                margin-top: 5px;

                & > * {
                    margin: 0;
                }
            }
            .title {
                float: right;

                & > * {
                    margin: 0;
                }

                p {
                    text-align: right;
                }
            }
        }

        .invoice-middle {
            overflow: hidden;
            margin-top: 30px;
            margin-bottom: 30px;

            .clientlogo {
                float: left;
                height: 60px;
                width: 60px;
                box-sizing: border-box;
                border-radius: 50%;
                overflow: hidden;
                background: grey;

                img {
                    width: 100%;
                }
            }

            .info {
                display: block;
                float: left;
                margin-left: 20px;
                margin-top: 5px;

                & > * {
                    margin: 0;
                }
            }

            .project {
                margin-left: 52%;

                & > * {
                    margin: 0;
                }
            }
        }

        .invoice-bottom {
            table {
                width: 100%;
                border-collapse: collapse;

                th {
                    text-align: right;
                    padding: 20px;
                    padding-bottom: 5px;
                    opacity: 0.7;

                    &:first-child {
                        text-align: left;
                        padding-left: 0px;
                        width: 100%;
                    }
                    &:last-child {
                        padding-right: 0px;
                    }
                }

                td {
                    text-align: right;
                    padding: 20px;
                    padding-bottom: 5px;
                    border-bottom: 1px solid #eee;

                    &:first-child {
                        text-align: left;
                        padding-left: 0px;
                        width: 100%;
                    }
                    &:last-child {
                        padding-right: 0px;
                    }
                }

                tfoot td {
                    border: none;
                    padding-top: 5px;
                }
            }
        }

        h1 {
            font-size: 1.5em;
            color: #222;
        }
        h2 {
            font-size: 0.9em;
        }
        h3 {
            font-size: 1.2em;
            font-weight: 300;
            line-height: 2em;
        }
        p {
            font-size: 0.7em;
            color: #666;
            line-height: 1.2em;
        }
    }
}

@media screen and (max-width: 768px) {
    .page-invoice {
        .invoice {
            .invoice-middle {
                .project {
                    display: block;
                    width: 100%;
                    clear: both;
                    padding: 10px 0;
                    margin: 0;
                }
            }
            .invoice-bottom {
                table {
                    th {
                        padding: 5px;
                    }

                    td {
                        padding: 5px;
                    }
                }
            }
        }
    }
}

@media print {
    .layout-container .container .footer,
    .layout-container .container .header,
    .layout-container .container .horizontal-nav,
    .layout-container .footer,
    .layout-container .layout-picker,
    .layout-container .vertical-nav,
    .layout-container .header {
        display: none;
    }

    .page-invoice {
        .toolbar {
            display: none;
        }

        .invoice {
            box-shadow: none;
            max-width: 100%;
            padding: 0;
        }
    }
}
</style>
