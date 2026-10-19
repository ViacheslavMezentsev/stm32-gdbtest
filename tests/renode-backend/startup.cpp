extern "C" __attribute__( ( noinline ) ) unsigned calculate( unsigned value )
{
    return value * 3 + 1;
}

extern "C" __attribute__( ( noinline ) ) void endless()
{
    while ( true )
        asm volatile( "nop" );
}

// Нейтральная программа: счётчик, точка наблюдения и явная инициализация RAM.
volatile unsigned counter;

extern "C" __attribute__( ( noinline ) ) void observe()
{
    volatile unsigned local  = 1;
    local                   += 2;
    local                   += 3;
    local                   += 4;
    asm volatile( "nop" );
}

extern "C" int main()
{
    counter = calculate( 0 ) + 2;
    observe();
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
