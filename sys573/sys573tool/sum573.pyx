# cython: cdivision=True

cpdef inline unsigned short calc_final_sum(unsigned int val):
    cdef unsigned short output = val & 0xffff

    while val > 0xffff:
        val = output + (val >> 16)
        output = val

    return output


cdef inline (unsigned int, unsigned int) sum_chunk(unsigned char *data, unsigned int offset, unsigned int chunk_size=0x20000):
    cdef unsigned int a = 0
    cdef unsigned int b = 0
    cdef unsigned int i = 0

    while i < chunk_size:
        a += data[offset+i]
        b += data[offset+i+1]
        i += 2

    return [a, b]


cpdef bytearray checksum_chunk(unsigned char *data, unsigned int offset, unsigned int chunk_size=0x20000):
    cdef unsigned int sum1, sum2
    cdef unsigned short a = 0
    cdef unsigned short b = 0

    sum1, sum2 = sum_chunk(data, offset, chunk_size)
    a = calc_final_sum(calc_final_sum(sum1) & 0xffff)
    b = calc_final_sum(calc_final_sum(sum2) & 0xffff)

    return bytearray([a & 0xff, b & 0xff, (a >> 8) & 0xff, (b >> 8) & 0xff])


cpdef list balance_sums(list cards, list card_sizes, unsigned int last_chunk_offset):
    cdef unsigned int last_chunk_checksum_offset = last_chunk_offset + 0x10
    cdef unsigned int i = 0
    cdef unsigned int j = 0
    cdef unsigned int a = 0
    cdef unsigned int b = 0
    cdef unsigned int pad = 0
    cdef unsigned char val = 0
    cdef unsigned int card_sum = sum(card_sizes)

    cards[0][last_chunk_checksum_offset + card_sum:last_chunk_offset + 0x2000] = bytearray([0] * (0x2000 - card_sum - 0x10))

    a, b = sum_chunk(cards[0], last_chunk_offset, 0x2000)
    while i < 2:
        pad = 0x10000 - calc_final_sum(a if i == 0 else b)
        j = card_sum

        while pad > 0 and j < 0x2000:
            val = pad if pad < 0xff else 0xff

            cards[0][last_chunk_checksum_offset + j + i] += val

            pad -= val
            j += 2

        i += 1

    return cards


cpdef add_checksums(list cards, list card_sizes, unsigned int chunk_size, unsigned int last_chunk_checksum_offset, unsigned int card_start_index, unsigned int card_count):
    cdef unsigned int real_card_index = 0
    cdef unsigned int i = 0
    cdef unsigned int card_offset = 0
    cdef unsigned int checksum_offset = 0
    cdef unsigned int total_cards = len(cards)
    cdef bytearray final_sum

    while real_card_index < total_cards:
        card_data = cards[real_card_index]

        if real_card_index < card_start_index:
            # Skip first DAT because it's already been done
            real_card_index += 1
            continue

        if real_card_index - card_start_index > card_count:
            break

        card_offset = (sum(card_sizes[:real_card_index]) // 4) * real_card_index

        i = 0
        s = len(card_data) // chunk_size
        while i < s:
            offset = (i * chunk_size) + (0x20 if real_card_index == 0 and i == 0 else 0)
            length = chunk_size - (0x20 if real_card_index == 0 and i == 0 else 0)
            final_sum = checksum_chunk(card_data, offset, length)

            checksum_offset = last_chunk_checksum_offset + ((i + card_offset) * 4)
            cards[0][checksum_offset:checksum_offset+4] = final_sum

            i += 1

        real_card_index += 1

    return cards
