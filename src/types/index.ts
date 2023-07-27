export enum ENavPos {
    "top" = "top",
    "bottom" = "bottom",
    "left" = "left",
    "right" = "right"
}
export enum EToolbar {
    "top" = "top",
    "bottom" = "bottom"
}
export enum EFooter {
    "above" = "above",
    "below" = "below"
}
export enum EViewAnimation {
    "fadeLeft" = "fade-left",
    "fadeRight" = "fade-right",
    "fadeTop" = "fade-top",
    "fadeTopInOut" = "fade-top-in-out",
    "fadeBottom" = "fade-bottom",
    "fadeBottomInOut" = "fade-bottom-in-out",
    "fade" = "fade"
}

export interface StateLayout {
    navPos: ENavPos | boolean | null
    toolbar: EToolbar | boolean | null
    footer: EFooter | boolean | null
    boxed: boolean
    roundedCorners: boolean
    viewAnimation: EViewAnimation
}
export interface State {
    layout: StateLayout
    splashScreen: boolean
    logged: boolean
}
