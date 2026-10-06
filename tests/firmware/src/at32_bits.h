/* AT32F403A/407 register bits used by the CI firmware; positions from RM AT32F403A/407 V2.02 and the SDK bit
   fields. The SDK exposes them as bit fields only, so the firmware names the masks it needs here. */
#ifndef AT32_BITS_H
#define AT32_BITS_H

/* CRM: clock control, configuration, peripheral clocks and resets. */
#define AT32_CRM_CTRL_HICKEN      ( 1U << 0 )
#define AT32_CRM_CTRL_HICKSTBL    ( 1U << 1 )
#define AT32_CRM_CTRL_PLLEN       ( 1U << 24 )
#define AT32_CRM_CFG_SCLKSEL      ( 3U << 0 )
#define AT32_CRM_CFG_SCLKSTS      ( 3U << 2 )
#define AT32_CRM_CFG_AHBDIV       ( 0xFU << 4 )
#define AT32_CRM_CFG_APB1DIV      ( 7U << 8 )
#define AT32_CRM_CFG_APB2DIV      ( 7U << 11 )
#define AT32_CRM_CFG_ADCDIV       ( ( 3U << 14 ) | ( 1U << 28 ) )
#define AT32_CRM_AHB_DMA1         ( 1U << 0 )
#define AT32_CRM_APB2_GPIOC       ( 1U << 4 )
#define AT32_CRM_APB2_ADC1        ( 1U << 9 )
#define AT32_CRM_APB1_TMR2        ( 1U << 0 )
#define AT32_CRM_APB1_BPR         ( 1U << 27 )
#define AT32_CRM_APB1_PWC         ( 1U << 28 )
#define AT32_CRM_BPDC_RTCSEL      ( 3U << 8 )
#define AT32_CRM_BPDC_RTCSEL_LICK ( 2U << 8 )
#define AT32_CRM_BPDC_RTCEN       ( 1U << 15 )
#define AT32_CRM_CTRLSTS_LICKEN   ( 1U << 0 )
#define AT32_CRM_CTRLSTS_LICKSTBL ( 1U << 1 )

/* GPIO. */
#define AT32_GPIO_PIN13 ( 1U << 13 )

/* TMR2. */
#define AT32_TMR_CTRL1_TMREN   ( 1U << 0 )
#define AT32_TMR_IDEN_OVFIEN   ( 1U << 0 )
#define AT32_TMR_ISTS_OVFIF    ( 1U << 0 )
#define AT32_TMR_SWEVT_OVFSWTR ( 1U << 0 )

/* PWC: battery powered domain write enable. */
#define AT32_PWC_CTRL_BPWEN ( 1U << 8 )

/* RTC: counter/alarm, F1-compatible layout. */
#define AT32_RTC_CTRLH_TAIEN ( 1U << 1 )
#define AT32_RTC_CTRLL_TSF   ( 1U << 0 )
#define AT32_RTC_CTRLL_TAF   ( 1U << 1 )
#define AT32_RTC_CTRLL_OVFF  ( 1U << 2 )
#define AT32_RTC_CTRLL_UPDF  ( 1U << 3 )
#define AT32_RTC_CTRLL_CFGEN ( 1U << 4 )
#define AT32_RTC_CTRLL_CFGF  ( 1U << 5 )

/* EXINT: line 17 is the RTC alarm. */
#define AT32_EXINT_LINE17 ( 1U << 17 )

/* DMA1: channel 1 flags and control. */
#define AT32_DMA_STS_GF1        ( 1U << 0 )
#define AT32_DMA_STS_FDTF1      ( 1U << 1 )
#define AT32_DMA_STS_DTERRF1    ( 1U << 3 )
#define AT32_DMA_CLR_GFC1       ( 1U << 0 )
#define AT32_DMA_CTRL_CHEN      ( 1U << 0 )
#define AT32_DMA_CTRL_FDTIEN    ( 1U << 1 )
#define AT32_DMA_CTRL_DTERRIEN  ( 1U << 3 )
#define AT32_DMA_CTRL_MINCM     ( 1U << 7 )
#define AT32_DMA_CTRL_PWIDTH_16 ( 1U << 8 )
#define AT32_DMA_CTRL_MWIDTH_16 ( 1U << 10 )

/* ADC1. */
#define AT32_ADC_CTRL1_SQEN       ( 1U << 8 )
#define AT32_ADC_CTRL2_ADCEN      ( 1U << 0 )
#define AT32_ADC_CTRL2_ADCAL      ( 1U << 2 )
#define AT32_ADC_CTRL2_ADCALINIT  ( 1U << 3 )
#define AT32_ADC_CTRL2_OCDMAEN    ( 1U << 8 )
#define AT32_ADC_CTRL2_OCTESEL_SW ( 7U << 17 )
#define AT32_ADC_CTRL2_OCTEN      ( 1U << 20 )
#define AT32_ADC_CTRL2_OCSWTRG    ( 1U << 22 )
#define AT32_ADC_CTRL2_ITSRVEN    ( 1U << 23 )
#define AT32_ADC_SPT1_CSPT16_MAX  ( 7U << 18 )
#define AT32_ADC_SPT1_CSPT17_MAX  ( 7U << 21 )
#define AT32_ADC_OSQ1_OCLEN_2     ( 1U << 20 )

#endif
