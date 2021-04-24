# cython: cdivision=True
# distutils: language=c++

from libc.stdint cimport uint8_t

cdef extern from *:
    """
    template <typename T>
    T* array_new(int n) {
        return new T[n];
    }

    template <typename T>
    void array_delete(T* x) {
        delete [] x;
    }
    """
    T* array_new[T](int)
    void array_delete[T](T* x)

from libcpp.vector cimport vector


cdef inline int find_data(unsigned char *data, int data_len, unsigned char c, int offset):
    while offset < data_len:
        if data[offset] == c:
            return offset

        offset += 1

    return -1


cpdef bytearray decode_lz(unsigned char *input_data, int data_len):
    cdef bytearray output = bytearray()
    cdef int idx = 0
    cdef int idx2 = 0
    cdef int start_offset = 0
    cdef int distance = 0
    cdef int control = 0
    cdef unsigned char data = 0
    cdef int length = 0

    while True:
        control >>= 1

        if (control & 0x100) == 0:
            control = input_data[idx] | 0xff00
            idx += 1

        data = input_data[idx]
        idx += 1

        if (control & 1) == 0:
            output.append(data)
            continue

        # print("idx: %02x" % idx)

        length = -1
        if (data & 0x80) == 0:
            distance = ((data & 0x03) << 8) | input_data[idx]
            length = (data >> 2) + 2
            idx += 1

        elif (data & 0x40) == 0:
            distance = (data & 0x0f) + 1
            length = (data >> 4) - 7

        # print("%04x %02x %02x" % (control, data, input_data[idx-1]), distance, length)

        if length != -1:
            start_offset = len(output)
            idx2 = 0

            while idx2 <= length:
                output.append(output[(start_offset - distance) + idx2])
                idx2 += 1

            continue

        if data == 0xff:
            break

        length = data - 0xb9
        # print("%02x %02x" % (data, length))
        while length >= 0:
            output.append(input_data[idx])
            idx += 1
            length -= 1

    return output


cpdef bytearray decode_lz0(unsigned char *data, int data_len):
    cdef bytearray output = bytearray()
    cdef int base_data_idx = 0
    cdef int data_idx = 0
    cdef int output_idx = 0
    cdef unsigned char cur_byte = 0
    cdef int cur_bit = 1

    print("decode_lz0 called")

    while True:
        while True:
            cur_bit -= 1
            data_idx = base_data_idx

            if cur_bit == 0:
                cur_byte = data[base_data_idx]
                data_idx = base_data_idx + 1
                cur_bit = 8

            if (cur_byte & 1) != 0:
                break

            cur_byte >>= 1
            base_data_idx = data_idx + 1
            output.append(data[data_idx])
            output_idx += 1

        cur_bit -= 1
        cur_byte >>= 1

        if cur_bit == 0:
            cur_byte = data[data_idx]
            data_idx += 1
            cur_bit = 8

        if (cur_byte & 1) == 0:
            uVar2 = (data[data_idx] << 8) | data[data_idx+1]
            cur_byte >>= 1

            if uVar2 == 0:
                return output

            base_data_idx = data_idx + 2
            if (data[data_idx+1] & 0x0f) == 0:
                bVar1 = data[base_data_idx]
                base_data_idx = data_idx + 3
                iVar3 = bVar1 + 1

            else:
                iVar3 = (uVar2 & 0x0f) + 2

            uVar4 = (uVar2 >> 4)

        else:
            cur_bit -= 1
            cur_byte >>= 1

            if cur_bit == 0:
                cur_byte = data[data_idx]
                data_idx += 1
                cur_bit = 8

            cur_bit -= 1
            uVar4 = cur_byte >> 1

            if cur_bit == 0:
                uVar4 = data[data_idx]
                data_idx += 1
                cur_bit = 8

            iVar3 = (cur_byte & 1) * 2 + 2 + (uVar4 & 1)
            cur_byte = uVar4 >> 1
            uVar4 = data[data_idx]
            base_data_idx = data_idx + 1

            if data[data_idx] == 0:
                uVar4 = 0x100

        while iVar3 != 0:
            bVar1 = output[output_idx-uVar4]
            iVar3 -= 1
            output.append(bVar1)
            output_idx += 1

    return output


cpdef bytearray encode_lz(unsigned char *data, int data_len):
    cdef uint8_t *output = array_new[uint8_t](data_len * 2)
    cdef int output_len = 0
    cdef int i = 0
    cdef int j = 0
    cdef int v = 0
    cdef int run_length = 0
    cdef int last_history_idx = 0
    cdef int history_idx = 0
    cdef int cmd_offset = 0
    cdef int cmd_bit = 0

    cdef int offset = 0
    cdef list compress_commands = []
    cdef list history_commands = []

    # Compress runs of previous characters
    while offset < data_len:
        # Run detection
        if output_len > 0 and data[offset] == output[output_len-1]:
            c = output[output_len-1]
            run_length = 1

            while offset + run_length < data_len and data[offset+run_length] == c and run_length < 0x21:
                run_length += 1

            if run_length > 1:
                compress_commands.append([
                    'repeat',
                    run_length
                ])

                j = 0
                while j < run_length:
                    output[output_len] = c
                    output_len += 1
                    j += 1

                offset += run_length
                continue

        # History check
        last_history_idx = max(output_len - 0x400, 0)
        history_idx = find_data(output, output_len, data[offset], last_history_idx)
        if history_idx != -1:
            history_commands.clear()

            while True:
                history_idx = find_data(output, output_len, data[offset], last_history_idx)
                last_history_idx = history_idx + 1

                if history_idx == -1:
                    break

                # Check how long we can match the history
                i = 1

                while offset + i < data_len:
                    if history_idx + i > output_len and output[-1] == data[offset+i]:
                        # Copy + repeat
                        i += 1

                    elif history_idx + i < output_len and output[history_idx+i] == data[offset+i]:
                        i += 1

                    else:
                        break

                history_back_idx = output_len - history_idx
                if i in [1, 2, 3, 4] and history_back_idx >= 1 and history_back_idx <= 16:
                    # Can use a short copy
                    history_commands.append([
                        'short_copy',
                        history_back_idx,
                        i,
                        1
                    ])

                elif history_back_idx <= 0x3ff and i >= 3 and i <= 0x21:
                    # Can use a long copy
                    history_commands.append([
                        'long_copy',
                        history_back_idx,
                        i,
                        2
                    ])

            best_compression = None
            for x in history_commands:
                if best_compression is None or x[2] - x[3] >= best_compression[2] - best_compression[3]:
                    best_compression = x

            if best_compression and best_compression[2] - best_compression[3] > 0:
                compress_commands.append(best_compression)

                j = 0
                while j < best_compression[2]:
                    output[output_len] = data[offset]
                    output_len += 1
                    offset += 1
                    j += 1

                continue

        compress_commands.append([
            'raw',
            data[offset]
        ])

        output[output_len] = data[offset]
        output_len += 1
        offset += 1

    compress_commands.append(['eof'])

    # Step 2: Compress down raw runs
    # Step 3: Build down repeat commands
    compress_commands2 = []
    i = 0
    compress_commands_len = len(compress_commands)
    while i < compress_commands_len:
        if compress_commands[i][0] == 'raw':
            run_length = 1

            while compress_commands[i+run_length][0] == 'raw':
                run_length += 1

            if run_length == 1:
                compress_commands2.append(compress_commands[i])
                i += 1
                continue

            raw_bulk = bytearray()
            for j in range(run_length):
                raw_bulk.append(compress_commands[i+j][1])

            while len(raw_bulk) > 7:
                copy_len = min(len(raw_bulk), 0x46)
                chunk = raw_bulk[:copy_len]
                raw_bulk = raw_bulk[copy_len:]

                compress_commands2.append([
                    'raw_bulk',
                    chunk,
                    len(chunk)
                ])

            while len(raw_bulk) > 0:
                copy_len = 1
                chunk = raw_bulk[:copy_len]
                raw_bulk = raw_bulk[copy_len:]

                compress_commands2.append([
                    'raw',
                    chunk[0]
                ])

            i += run_length

        elif compress_commands[i][0] == 'repeat':
            history_back_idx = 1
            length = compress_commands[i][1]

            while length > 0:
                if length in [1, 2, 3, 4] and history_back_idx >= 1 and history_back_idx <= 16:
                    copy_len = length

                    # Can use a short copy
                    compress_commands2.append([
                        'short_copy',
                        history_back_idx,
                        copy_len,
                        1
                    ])

                    length -= copy_len

                elif history_back_idx <= 0x3ff and length >= 3:
                    copy_len = min(length, 0x21)

                    # Can use a long copy
                    compress_commands2.append([
                        'long_copy',
                        history_back_idx,
                        copy_len,
                        2
                    ])

                    length -= copy_len

            i += 1

        else:
            compress_commands2.append(compress_commands[i])
            i += 1

    output_buffer = bytearray([0])
    cmd_offset = 0
    cmd_bit = 0

    # Step 4: Build actual data now
    for x in compress_commands2:
        # print("%04x" % len(output_buffer), x)

        if cmd_bit == 8:
            cmd_offset = len(output_buffer)
            output_buffer += int.to_bytes(0, 1, 'little')
            cmd_bit = 0

        if x[0] == 'raw':
            output_buffer += int.to_bytes(x[1], 1, 'little')

        elif x[0] == 'eof':
            output_buffer[cmd_offset] |= 1 << cmd_bit
            output_buffer += int.to_bytes(0xff, 1, 'little')

        else:
            output_buffer[cmd_offset] |= 1 << cmd_bit

            if x[0] == 'raw_bulk':
                # 1 + x bytes
                output_buffer += int.to_bytes(0xb9 + len(x[1]) - 1, 1, 'little')
                output_buffer += x[1]

            elif x[0] == 'short_copy':
                # 1 byte
                v = ((x[2] + 6) << 4) | (x[1] - 1)
                output_buffer += int.to_bytes(v, 1, 'little')

            elif x[0] == 'long_copy':
                # 2 bytes
                v = (((x[2] - 3) << 2) << 8) | (x[1] & 0x3ff)
                output_buffer += int.to_bytes(v, 2, 'big')

        # if len(output_buffer) >= 0x170:
        #     exit(1)

        cmd_bit += 1

    return output_buffer

