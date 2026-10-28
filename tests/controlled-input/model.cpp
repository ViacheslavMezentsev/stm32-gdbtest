// Учебный вход в SRAM: никаких GPIO, DMA, RTOS или физических сигналов.
struct InputState
{
    unsigned left_guard, source, level, consumed, active, reads, cycles, right_guard;
};

volatile InputState input_state;
static_assert( sizeof( InputState ) == 32, "Complete POD snapshot must include all fields" );

extern "C" __attribute__( ( noinline ) ) void before_refresh()
{
    asm volatile( "" );
}

extern "C" __attribute__( ( noinline ) ) void before_sample()
{
    asm volatile( "" );
}

extern "C" __attribute__( ( noinline ) ) void after_processing()
{
    asm volatile( "" );
}

extern "C" void reset_input()
{
    input_state.left_guard  = 111;
    input_state.source      = 0;
    input_state.level       = 0;
    input_state.consumed    = 0;
    input_state.active      = 0;
    input_state.reads       = 0;
    input_state.cycles      = 0;
    input_state.right_guard = 222;
}

extern "C" __attribute__( ( noinline ) ) void refresh_input()
{
    input_state.level = input_state.source;
}

extern "C" __attribute__( ( noinline ) ) unsigned sample_input()
{
    ++input_state.reads;    // ret на входе пропускает и этот эффект.
    return input_state.level;
}

extern "C" __attribute__( ( noinline ) ) void process_input( unsigned sample )
{
    input_state.consumed = sample;
    input_state.active   = sample == 1 ? 1 : 0;
    ++input_state.cycles;
}
#ifdef HOST
#include <cstdio>

int main()
{
    reset_input();
    refresh_input();
    process_input( sample_input() );
    if ( input_state.active != 0 || input_state.reads != 1 ) return 1;
    reset_input();
    refresh_input();
    input_state.level = 1;
    process_input( sample_input() );
    if ( input_state.consumed != 1 || input_state.active != 1 ) return 2;
    // Слишком ранняя запись успешна, но штатное обновление её уничтожает.
    reset_input();
    input_state.level = 1;
    refresh_input();
    process_input( sample_input() );
    if ( input_state.consumed != 0 || input_state.active != 0 ) return 3;
    // Только модель пропуска sample_input; настоящее ret проверяется в Renode/GDB.
    reset_input();
    process_input( 1 );
    if ( input_state.active != 1 || input_state.reads != 0 ) return 4;
    refresh_input();
    process_input( sample_input() );
    if ( input_state.active != 0 || input_state.reads != 1 || input_state.cycles != 2 ) return 5;
    if ( input_state.left_guard != 111 || input_state.right_guard != 222 ) return 6;
    std::puts( "PASS controlled input host model (not GDB ret)" );
    return 0;
}
#else
extern "C" void main()
{
    reset_input();
    while ( true )
    {
        before_refresh();
        refresh_input();
        before_sample();
        process_input( sample_input() );
        after_processing();
    }
}

extern "C" void Reset_Handler()
{
    main();
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
#endif
