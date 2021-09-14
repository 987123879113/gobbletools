# cython: cdivision=True

cdef rol(int val, int r_bits):
    return (val << r_bits) & 0xFFFFFFFF | ((val & 0xFFFFFFFF) >> (32 - r_bits))

cpdef decrypt(unsigned char *data, size_t data_len, unsigned int key1, unsigned short key2):
    cdef unsigned int key = key1
    cdef size_t i = 0

    while i < (data_len // 4) * 4:
        key = rol(key + key2, 3)

        data[i] ^= key & 0xff
        data[i + 1] ^= (key >> 8) & 0xff
        data[i + 2] ^= (key >> 16) & 0xff
        data[i + 3] ^= (key >> 24) & 0xff

        i += 4

    key = rol(key + key2, 3)
    key_parts = [key & 0xff, (key >> 8) & 0xff, (key >> 16) & 0xff, (key >> 24) & 0xff]
    for j in range(data_len - i):
            data[i] ^= key_parts[j]

