#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Adapter must synchronously read/store exactly N bytes; no concurrent writers.
template<std::size_t N, class Adapter>
class BufferedStore
{
    static_assert( N > 0 );
    Adapter& storage_;
    std::array<std::uint8_t, N> bytes_{};
    bool loaded_ = false;
    bool dirty_  = false;

    static bool range( std::size_t a, std::size_t n ) { return a <= N && n <= N - a; }

public:
    explicit BufferedStore( Adapter& storage ) : storage_( storage ) {}

    bool dirty() const { return dirty_; }

    // Refuse to silently discard unsaved changes. Failed load leaves the old cache intact.
    bool load()
    {
        if ( dirty_ ) return false;
        std::array<std::uint8_t, N> next{};
        if ( !storage_.read( next.data(), N ) ) return false;
        bytes_  = next;
        loaded_ = true;
        return true;
    }

    bool read( std::size_t a, std::uint8_t* dst, std::size_t n ) const
    {
        if ( !loaded_ || !range( a, n ) || ( n && !dst ) ) return false;
        for ( std::size_t i = 0; i < n; ++i )
            dst[i] = bytes_[a + i];
        return true;
    }

    bool write( std::size_t a, const std::uint8_t* src, std::size_t n )
    {
        if ( !loaded_ || !range( a, n ) || ( n && !src ) ) return false;
        for ( std::size_t i = 0; i < n; ++i )
        {
            if ( bytes_[a + i] != src[i] )
            {
                bytes_[a + i] = src[i];
                dirty_        = true;
            }
        }
        return true;
    }

    bool commit()
    {
        if ( !loaded_ ) return false;
        if ( !dirty_ ) return true;
        if ( !storage_.store( bytes_.data(), N ) ) return false;
        std::array<std::uint8_t, N> actual{};
        if ( !storage_.read( actual.data(), N ) ) return false;
        for ( std::size_t i = 0; i < N; ++i )
            if ( actual[i] != bytes_[i] ) return false;
        dirty_ = false;
        return true;
    }
};
