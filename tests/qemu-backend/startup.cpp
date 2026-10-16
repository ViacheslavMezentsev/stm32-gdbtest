// Нейтральная программа: счётчик, точка наблюдения и явная инициализация RAM.
volatile unsigned counter;

extern "C" __attribute__( ( noinline ) ) void observe()
{
    asm volatile( "nop" );
}

extern "C" int main()
{
#ifdef QA_SEMIHOSTING
    // SYS_WRITE0: журнал хоста включается только в отдельной проверке opt-in.
    register unsigned operation asm( "r0" )  = 4;
    register const char* message asm( "r1" ) = "QEMU semihosting witness\n";
    asm volatile( "bkpt 0xab" : "+r"( operation ) : "r"( message ) : "memory" );
#endif
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
