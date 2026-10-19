// Прошивка знает о попытках отправки, но не о приёме моделью.
volatile unsigned sent;
volatile unsigned initialized;

extern "C" __attribute__( ( noinline ) ) void ready()
{
    asm volatile( "nop" );
}

extern "C" int main()
{
    sent        = 0;
    initialized = 1;
    for ( unsigned value = 1; value <= 3; ++value )
    {
        *( volatile unsigned* ) 0x40000000 = value;
        sent++;
    }
    ready();
    while ( true )
    {
        asm volatile( "nop" );
    }
}

extern "C" void Reset_Handler()
{
    main();
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
