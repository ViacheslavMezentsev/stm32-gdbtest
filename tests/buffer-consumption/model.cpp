// Учебный буфер пакета в SRAM: никаких DMA, UART, прерываний, RTOS или физических сигналов.
// Все изменяемые данные лежат подряд в секции .experiment: опыт снимает и возвращает их целиком.
#define EXPERIMENT __attribute__( ( section( ".experiment" ), used ) )

struct PacketStats
{
    unsigned accepted, rejected, last_type, last_sum, sequence, bytes, entries, busy;
};

EXPERIMENT unsigned left_guard;
EXPERIMENT unsigned char inject_buf[16];    // буфер, принадлежащий опыту
EXPERIMENT unsigned right_guard;
EXPERIMENT unsigned char rx_buf[16];    // штатный буфер приложения
EXPERIMENT unsigned rx_len;
EXPERIMENT PacketStats stats;

extern "C" __attribute__( ( noinline ) ) void before_receive()
{
    asm volatile( "" );
}

extern "C" __attribute__( ( noinline ) ) void inside_handler()
{
    asm volatile( "" );
}

extern "C" __attribute__( ( noinline ) ) void after_processing()
{
    asm volatile( "" );
}

extern "C" void reset_state()
{
    left_guard  = 0x11111111u;
    right_guard = 0x22222222u;
    for ( unsigned i = 0; i < sizeof( inject_buf ); ++i )
    {
        inject_buf[i] = 0;
        rx_buf[i]     = 0;
    }
    rx_len         = 0;
    stats.accepted = stats.rejected = stats.last_type = stats.last_sum = 0;
    stats.sequence = stats.bytes = stats.entries = stats.busy = 0;
}

// Штатный источник следующего пакета: копирование без DMA, тип 0x10, полезная нагрузка 1, 2.
extern "C" __attribute__( ( noinline ) ) void receive()
{
    const unsigned char packet[] = { 0x5F, 0x10, 2, 1, 2, 0x74 };
    for ( unsigned i = 0; i < sizeof( packet ); ++i )
        rx_buf[i] = packet[i];
    rx_len = sizeof( packet );
}

// Пакет: 0x5F, тип, длина n, n байт, сумма всех предыдущих байтов mod 256.
extern "C" __attribute__( ( noinline ) ) unsigned handle_packet( const unsigned char* data, unsigned len )
{
    ++stats.entries;
    if ( stats.busy )
    {
        ++stats.rejected;    // повторный вход во время обработки не меняет текущий пакет
        return 0;
    }
    stats.busy = 1;
    inside_handler();
    unsigned ok = 0;
    if ( len >= 4 && len <= sizeof( inject_buf ) && data[0] == 0x5F && data[2] + 4u == len )
    {
        unsigned sum = 0, payload = 0;
        for ( unsigned i = 0; i + 1 < len; ++i )
            sum += data[i];
        for ( unsigned i = 3; i + 1 < len; ++i )
            payload += data[i];
        if ( ( sum & 0xFFu ) == data[len - 1] )
        {
            stats.last_type  = data[1];
            stats.last_sum   = payload;
            stats.bytes     += len;
            ++stats.sequence;
            ++stats.accepted;
            ok = 1;
        }
    }
    if ( !ok ) ++stats.rejected;
    stats.busy = 0;
    return ok;
}
#ifdef HOST
#include <cstdio>

static unsigned put( const unsigned char* packet, unsigned len )
{
    for ( unsigned i = 0; i < len; ++i )
        inject_buf[i] = packet[i];
    return handle_packet( inject_buf, len );
}

int main()
{
    const unsigned char a[]   = { 0x5F, 0x21, 3, 3, 4, 5, 0x8F };
    const unsigned char b[]   = { 0x5F, 0x22, 1, 9, 0x8B };
    const unsigned char bad[] = { 0x5F, 0x21, 3, 3, 4, 5, 0x90 };
    reset_state();
    receive();
    if ( handle_packet( rx_buf, rx_len ) != 1 || stats.last_type != 0x10 || stats.last_sum != 3 ) return 1;
    reset_state();
    if ( put( a, sizeof( a ) ) != 1 || put( b, sizeof( b ) ) != 1 ) return 2;
    if ( stats.sequence != 2 || stats.last_type != 0x22 || stats.last_sum != 9 ) return 3;
    receive();
    if ( handle_packet( rx_buf, rx_len ) != 1 || stats.sequence != 3 || stats.last_type != 0x10 ) return 4;
    reset_state();
    if ( put( bad, sizeof( bad ) ) != 0 || stats.rejected != 1 || stats.sequence != 0 ) return 5;
    if ( put( a, sizeof( a ) ) != 1 || stats.sequence != 1 ) return 6;
    // Повторный вход моделируется флагом busy; настоящий вложенный вызов проверяет Renode/GDB.
    reset_state();
    stats.busy = 1;
    if ( put( a, sizeof( a ) ) != 0 || stats.rejected != 1 || stats.entries != 1 ) return 7;
    if ( left_guard != 0x11111111u || right_guard != 0x22222222u ) return 8;
    std::puts( "PASS buffer consumption host model (not GDB call)" );
    return 0;
}
#else
extern "C" void main()
{
    reset_state();
    while ( true )
    {
        before_receive();
        receive();
        handle_packet( rx_buf, rx_len );
        after_processing();
    }
}

extern "C" void Reset_Handler()
{
    main();
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
#endif
