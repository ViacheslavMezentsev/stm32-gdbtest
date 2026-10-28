volatile unsigned calls;

// Neutral C++ fixture: explicit startup, no peripherals or runtime library.
struct Probe
{
    unsigned value;
    unsigned choose( int n );
    unsigned choose( unsigned n ) const;
    unsigned inspect() volatile;
    unsigned inspect_cv() const volatile;
    __attribute__( ( noinline ) ) void add( unsigned n );
    __attribute__( ( noinline ) ) unsigned read() const;
    __attribute__( ( noinline ) ) static unsigned twice( unsigned n );

    __attribute__( ( always_inline ) ) inline unsigned absent() const { return value; }
};

void Probe::add( unsigned n )
{
    ++calls;
    value += n;
}

unsigned Probe::read() const
{
    ++calls;
    return value;
}

unsigned Probe::twice( unsigned n )
{
    ++calls;
    return 2 * n;
}

namespace demo
{
    __attribute__( ( noinline ) ) unsigned increment( unsigned n )
    {
        ++calls;
        return n + 1;
    }
}

Probe probe;
Probe* probe_ptr;
const Probe* const_probe;
volatile Probe* volatile_probe;
const volatile Probe* cv_probe;
Probe* null_probe;

struct Other
{
    unsigned value;
} other;

struct VirtualProbe
{
    virtual unsigned run();
};

unsigned VirtualProbe::run()
{
    ++calls;
    return 9;
}

unsigned Probe::choose( int n )
{
    ++calls;
    return value + n;
}

unsigned Probe::choose( unsigned n ) const
{
    ++calls;
    return value + n + 100;
}

unsigned Probe::inspect() volatile
{
    ++calls;
    return value;
}

unsigned Probe::inspect_cv() const volatile
{
    ++calls;
    return value;
}

extern "C" __attribute__( ( noinline ) ) void ready()
{
    asm volatile( "nop" );
}

__attribute__( ( noinline ) ) unsigned free_cpp( unsigned n )
{
    ++calls;
    return n + 2;
}

extern "C" __attribute__( ( noinline ) ) void set_value( unsigned n )
{
    probe.value = n;
}

unsigned samples[6];
unsigned* samples_ptr;
unsigned* mmio_ptr;
unsigned* unaligned_ptr;
unsigned* null_samples;
const unsigned* readonly_samples;
typedef const unsigned ReadonlyWord;
ReadonlyWord* readonly_alias;
unsigned scalar;

namespace demo
{
    unsigned sum( ReadonlyWord* p, unsigned n )
    {
        ++calls;
        unsigned result = 0;
        for ( unsigned i = 0; i < n; ++i )
            result += p[i];
        return result;
    }

    void fill( unsigned* p, unsigned n )
    {
        ++calls;
        for ( unsigned i = 0; i < n; ++i )
            p[i] += 10;
    }

    void bump( unsigned& value )
    {
        ++calls;
        value += 7;
    }

    unsigned peek( const unsigned& value )
    {
        ++calls;
        return value;
    }

    void update( Probe& value )
    {
        ++calls;
        value.value += 9;
    }

    unsigned nullable( const unsigned* p )
    {
        ++calls;
        return p ? *p : 99;
    }

    void double_pointer( unsigned** p )
    {
        ++calls;
        **p = 1;
    }
}

extern "C" unsigned c_sum( const unsigned* p, unsigned n )
{
    ++calls;
    unsigned result = 0;
    for ( unsigned i = 0; i < n; ++i )
        result += p[i];
    return result;
}

// Нейтральная иерархия: вторая база имеет ненулевое смещение.
struct Left
{
    unsigned guard;
};

struct Base
{
    unsigned value;
    unsigned step( unsigned n );
};

unsigned Base::step( unsigned n )
{
    ++calls;
    value += n;
    return value;
}

struct Derived : Left, Base
{
    unsigned tail;
};

struct Deep : Derived
{
    unsigned end;
};

struct One : Base
{
    unsigned tail;
};

struct ArmA : Base
{
};

struct ArmB : Base
{
};

struct Diamond : ArmA, ArmB
{
};

struct VirtualDerived : virtual Base
{
    unsigned tail;
    unsigned layout_probe() const;
};

unsigned VirtualDerived::layout_probe() const
{
    return tail;
}

Derived derived;
Deep deep;
One one;
Diamond diamond;
Derived* derived_ptr;
const Derived* const_derived;
VirtualDerived* virtual_derived;
unsigned base_oracle;
unsigned deep_oracle;

unsigned inherited_pointer( Base* p )
{
    ++calls;
    p->value += 5;
    return p->value;
}

unsigned inherited_reference( Base& p )
{
    ++calls;
    p.value += 7;
    return p.value;
}

unsigned inherited_const( const Base& p )
{
    ++calls;
    return p.value;
}

extern "C" void main()
{
    derived.guard = 111;
    derived.value = 10;
    derived.tail  = 222;
    derived_ptr   = &derived;
    const_derived = &derived;
    deep.guard    = 333;
    deep.value    = 20;
    deep.tail     = 444;
    deep.end      = 555;
    one.value     = 30;
    one.tail      = 666;
    // Эталон адреса вычисляет компилятор, независимо от Python-preflight.
    base_oracle     = reinterpret_cast<unsigned>( static_cast<Base*>( &derived ) );
    deep_oracle     = reinterpret_cast<unsigned>( static_cast<Base*>( &deep ) );
    virtual_derived = nullptr;    // Тип нужен для отказа; объект не конструируем.
    mmio_ptr        = reinterpret_cast<unsigned*>( 0x40000000 );
    unaligned_ptr   = reinterpret_cast<unsigned*>( 0x20000101 );
    null_samples    = nullptr;
    for ( unsigned i = 0; i < 6; ++i )
        samples[i] = i + 1;
    samples_ptr      = samples;
    readonly_samples = samples;
    readonly_alias   = samples;
    scalar           = 3;
    probe_ptr        = &probe;
    const_probe      = &probe;
    volatile_probe   = &probe;
    cv_probe         = &probe;
    null_probe       = nullptr;
    calls            = 0;
    probe.value      = 3;
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

namespace demo
{
    unsigned overloaded( unsigned n )
    {
        ++calls;
        return n;
    }

    unsigned overloaded( int n )
    {
        ++calls;
        return n;
    }

    unsigned pointer( unsigned* p )
    {
        ++calls;
        return *p;
    }

    float floating( unsigned n )
    {
        ++calls;
        return 1.0f;
    }

    void clear()
    {
        ++calls;
    }
}
