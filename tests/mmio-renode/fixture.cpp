typedef unsigned int u32;

struct Registers
{
    volatile u32 rw, wo, rc, w1c, fifo, ticking, width;
};

struct Bits
{
    volatile u32 flag : 1;
    volatile u32 rest : 31;
};

volatile unsigned index;
Registers* const regs = ( Registers* ) 0x40000000;

extern "C" void ready()
{
    asm volatile( "nop" );
}

extern "C" void Reset_Handler()
{
    index = 0;
    ready();
    while ( true )
        asm volatile( "nop" );
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
