# cython: cdivision=True

cpdef unsigned int get_filename_hash(unsigned char *filename, unsigned int filename_len):
    cdef int hash = 0
    cdef unsigned int cidx = 0
    cdef unsigned int i = 0

    while cidx < filename_len:
        i = 0
        while i < 6:
            hash = ((hash >> 31) & 0x4c11db7) ^ ((hash << 1) | ((filename[cidx] >> i) & 1))
            i += 1

        cidx += 1

    return hash & 0xffffffff


cdef rot(int c):
    return ((c >> 7) & 1) | ((c << 1) & 0xff)


cdef int is_bit_set(int value, int n):
    return (value >> n) & 1


cdef int bit_swap(int v, int b15, int b14, int b13, int b12, int b11, int b10, int b9, int b8, int b7, int b6, int b5, int b4, int b3, int b2, int b1, int b0):
    return (is_bit_set(v, b15) << 15) | \
        (is_bit_set(v, b14) << 14) | \
        (is_bit_set(v, b13) << 13) | \
        (is_bit_set(v, b12) << 12) | \
        (is_bit_set(v, b11) << 11) | \
        (is_bit_set(v, b10) << 10) | \
        (is_bit_set(v, b9) << 9) | \
        (is_bit_set(v, b8) << 8) | \
        (is_bit_set(v, b7) << 7) | \
        (is_bit_set(v, b6) << 6) | \
        (is_bit_set(v, b5) << 5) | \
        (is_bit_set(v, b4) << 4) | \
        (is_bit_set(v, b3) << 3) | \
        (is_bit_set(v, b2) << 2) | \
        (is_bit_set(v, b1) << 1) | \
        (is_bit_set(v, b0) << 0)


cpdef bytearray decrypt(unsigned char *data, int data_len, unsigned short key1, unsigned short key2, unsigned char key3):
    cdef unsigned short v = 0
    cdef unsigned short m = 0
    cdef unsigned int idx = 0

    output_data = bytearray(data_len * 2)

    while idx < data_len:
        v = (data[idx * 2 + 1] << 8) | data[idx * 2]
        m = key1 ^ key2

        v = bit_swap(
            v,
            15 - is_bit_set(m, 0xF),
            14 + is_bit_set(m, 0xF),
            13 - is_bit_set(m, 0xE),
            12 + is_bit_set(m, 0xE),
            11 - is_bit_set(m, 0xB),
            10 + is_bit_set(m, 0xB),
            9 - is_bit_set(m, 0x9),
            8 + is_bit_set(m, 0x9),
            7 - is_bit_set(m, 0x8),
            6 + is_bit_set(m, 0x8),
            5 - is_bit_set(m, 0x5),
            4 + is_bit_set(m, 0x5),
            3 - is_bit_set(m, 0x3),
            2 + is_bit_set(m, 0x3),
            1 - is_bit_set(m, 0x2),
            0 + is_bit_set(m, 0x2)
        )


        v ^= (is_bit_set(m, 0xD) << 14) ^ \
            (is_bit_set(m, 0xC) << 12) ^ \
            (is_bit_set(m, 0xA) << 10) ^ \
            (is_bit_set(m, 0x7) << 8) ^ \
            (is_bit_set(m, 0x6) << 6) ^ \
            (is_bit_set(m, 0x4) << 4) ^ \
            (is_bit_set(m, 0x1) << 2) ^ \
            (is_bit_set(m, 0x0) << 0)

        v ^= bit_swap(
                key3,
                7, 0, 6, 1,
                5, 2, 4, 3,
                3, 4, 2, 5,
                1, 6, 0, 7
            )

        output_data[idx * 2] = (v >> 8) & 0xff
        output_data[idx * 2 + 1] = v & 0xff

        key1 = ((key1 & 0x8000) | ((key1 << 1) & 0x7FFE) | ((key1 >> 14) & 1)) & 0xFFFF

        if (((key1 >> 15) ^ key1) & 1) != 0:
            key2 = ((key2 << 1) | (key2 >> 15)) & 0xFFFF

        idx += 1
        key3 += 1

    return output_data

cpdef bytearray encrypt(unsigned char *data, int data_len, unsigned short key1, unsigned short key2, unsigned char key3):
    cdef unsigned short v = 0
    cdef unsigned short m = 0
    cdef unsigned int idx = 0

    output_data = bytearray(data_len * 2)

    while idx < data_len:
        v = (data[idx * 2 + 1] << 8) | data[idx * 2]
        m = key1 ^ key2

        v = bit_swap(
            v,
            15 - is_bit_set(m, 0xF),
            14 + is_bit_set(m, 0xF),
            13 - is_bit_set(m, 0xE),
            12 + is_bit_set(m, 0xE),
            11 - is_bit_set(m, 0xB),
            10 + is_bit_set(m, 0xB),
            9 - is_bit_set(m, 0x9),
            8 + is_bit_set(m, 0x9),
            7 - is_bit_set(m, 0x8),
            6 + is_bit_set(m, 0x8),
            5 - is_bit_set(m, 0x5),
            4 + is_bit_set(m, 0x5),
            3 - is_bit_set(m, 0x3),
            2 + is_bit_set(m, 0x3),
            1 - is_bit_set(m, 0x2),
            0 + is_bit_set(m, 0x2)
        )


        v ^= (is_bit_set(m, 0xD) << 14) ^ \
            (is_bit_set(m, 0xC) << 12) ^ \
            (is_bit_set(m, 0xA) << 10) ^ \
            (is_bit_set(m, 0x7) << 8) ^ \
            (is_bit_set(m, 0x6) << 6) ^ \
            (is_bit_set(m, 0x4) << 4) ^ \
            (is_bit_set(m, 0x1) << 2) ^ \
            (is_bit_set(m, 0x0) << 0)

        v ^= bit_swap(
                key3,
                3, 4, 2, 5,
                1, 6, 0, 7,
                7, 0, 6, 1,
                5, 2, 4, 3
            )

        output_data[idx * 2] = (v >> 8) & 0xff
        output_data[idx * 2 + 1] = v & 0xff

        key1 = ((key1 & 0x8000) | ((key1 << 1) & 0x7FFE) | ((key1 >> 14) & 1)) & 0xFFFF

        if (((key1 >> 15) ^ key1) & 1) != 0:
            key2 = ((key2 << 1) | (key2 >> 15)) & 0xFFFF

        idx += 1
        key3 += 1

    return output_data


cpdef bytearray decrypt_ddrsbm(unsigned char *data, int data_len, unsigned short key):
    cdef unsigned int output_idx = 0
    cdef unsigned int idx = 0
    cdef unsigned int even_bit_shift = 0
    cdef unsigned int odd_bit_shift = 0
    cdef unsigned int is_even_bit_set = 0
    cdef unsigned int is_odd_bit_set = 0
    cdef unsigned int is_key_bit_set = 0
    cdef unsigned int is_scramble_bit_set = 0
    cdef unsigned int cur_bit = 0
    cdef unsigned int output_word = 0

    output_data = bytearray(data_len * 2)
    key_data = bytearray(16)

    # Generate key data based on input key
    key_state = is_bit_set(key, 0x0d) << 15 | \
        is_bit_set(key, 0x0b) << 14 | \
        is_bit_set(key, 0x09) << 13 | \
        is_bit_set(key, 0x07) << 12 | \
        is_bit_set(key, 0x05) << 11 | \
        is_bit_set(key, 0x03) << 10 | \
        is_bit_set(key, 0x01) << 9 | \
        is_bit_set(key, 0x0f) << 8 | \
        is_bit_set(key, 0x0e) << 7 | \
        is_bit_set(key, 0x0c) << 6 | \
        is_bit_set(key, 0x0a) << 5 | \
        is_bit_set(key, 0x08) << 4 | \
        is_bit_set(key, 0x06) << 3 | \
        is_bit_set(key, 0x04) << 2 | \
        is_bit_set(key, 0x02) << 1 | \
        is_bit_set(key, 0x00) << 0

    while idx < 8:
        key_data[idx * 2] = key_state & 0xff
        key_data[idx * 2 + 1] = (key_state >> 8) & 0xff

        key_state = (rot(key_state >> 8) << 8) | rot(key_state & 0xff)

        idx += 1

    while idx < data_len:
        output_word = 0
        cur_data = (data[(idx * 2) + 1] << 8) | data[(idx * 2)]

        cur_bit = 0
        while cur_bit < 8:
            even_bit_shift = (cur_bit * 2) & 0xff
            odd_bit_shift = (cur_bit * 2 + 1) & 0xff

            is_even_bit_set = int((cur_data & (1 << even_bit_shift)) != 0)
            is_odd_bit_set = int((cur_data & (1 << odd_bit_shift)) != 0)
            is_key_bit_set = int((key_data[idx % 16] & (1 << cur_bit)) != 0)
            is_scramble_bit_set = int((key_data[(idx - 1) % 16] & (1 << cur_bit)) != 0)

            if is_scramble_bit_set == 1:
                is_even_bit_set, is_odd_bit_set = is_odd_bit_set, is_even_bit_set

            if ((is_even_bit_set ^ is_key_bit_set)) == 1:
                output_word |= 1 << even_bit_shift

            if is_odd_bit_set == 1:
                output_word |= 1 << odd_bit_shift

            cur_bit += 1

        output_data[output_idx] = (output_word >> 8) & 0xff
        output_data[output_idx+1] = output_word & 0xff
        output_idx += 2
        idx += 1

    return output_data

