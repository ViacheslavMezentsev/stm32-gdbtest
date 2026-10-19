.syntax unified
.cpu cortex-m4
.thumb
.section .text
.global irq_hook, function_hook, params
.type irq_hook,%function
irq_hook:
    push {r0-r3}
    ldr r0, =0x20008400
    ldr r1, [r0]
    adds r1, #1
    str r1, [r0]
    pop {r0-r3}
    @ Keep EXC_RETURN in LR; the original ISR returns from the exception.
    ldr pc, irq_original
.align 2
irq_original: .word 0
.type function_hook,%function
function_hook:
    push {r0-r3}
    ldr r0, =0x20008404
    ldr r1, [r0]
    adds r1, #1
    str r1, [r0]
    pop {r0-r3}
    ldr pc, function_original
.align 2
function_original: .word 0
.global irq_original, function_original
params:
.ltorg

.align 2
.global fpb_hook, continuation
.type fpb_hook,%function
fpb_hook:
    push {r0-r3}
    ldr r0, =0x20008404
    ldr r1, [r0]
    adds r1, #1
    str r1, [r0]
    pop {r0-r3}
    @ Replay only the exact two instructions admitted by prepare.py.
    push {r7}
    sub sp, #12
    ldr pc, continuation
.align 2
continuation: .word 0
.ltorg
