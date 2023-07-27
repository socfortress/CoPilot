import { EFooter, ENavPos, EToolbar } from "@/types"

export default {
    contenOnly: {
        navPos: false,
        toolbar: false,
        footer: false
    },
    navLeft: {
        navPos: ENavPos.left,
        toolbar: EToolbar.bottom,
        boxed: false,
        roundedCorners: false,
        footer: EFooter.below
    },
    navRight: {
        navPos: ENavPos.right,
        toolbar: EToolbar.bottom,
        boxed: false,
        roundedCorners: false,
        footer: EFooter.below
    },
    navTop: {
        navPos: ENavPos.top,
        toolbar: EToolbar.bottom,
        boxed: false,
        roundedCorners: false,
        footer: EFooter.below
    },
    navBottom: {
        navPos: ENavPos.bottom,
        toolbar: EToolbar.bottom,
        boxed: false,
        roundedCorners: false,
        footer: EFooter.below
    }
}
