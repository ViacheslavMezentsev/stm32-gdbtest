// Нейтральная программа: счётчик, точка наблюдения и явная инициализация RAM.
volatile unsigned counter;

extern "C" __attribute__( ( noinline ) ) void observe()
{
    asm volatile( "nop" );
}

extern "C" int main()
{
    counter = 3;
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
