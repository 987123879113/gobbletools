import random

import hexdump

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, task

from crc16 import calc_crc16, calc_crc16_normal


class PacketResponse:
    def __init__(self, cmd, payload=bytearray([])):
        self.cmd = cmd
        self.payload = payload


    def is_valid(self):
        return self.cmd is not None


    def to_bytes(self):
        return bytearray([self.cmd]) + self.payload


class MsuServer:
    __instance__ = None

    next_buffer_id = random.randint(0, 15)
    registered_clients = {}


    def __init__(self):
        print("MsuServer")

        if MsuServer.__instance__ is None:
            MsuServer.__instance__ = self

        else:
            raise Exception("You cannot create another MsuServer class")


    @staticmethod
    def get_instance():
        if not MsuServer.__instance__:
            MsuServer()

        print("Returned MsuServer")

        return MsuServer.__instance__


    def register_client(self, client_obj, client_id):
        self.registered_clients[client_id] = client_obj


    def unregister_client(self, client_id):
        if client_id in self.registered_clients:
            del self.registered_clients[client_id]


    def get_registered_client(self, client_id):
        return self.registered_clients.get(client_id, None)


    def get_registered_client_name(self, client_id):
        client = self.get_registered_client(client_id)

        if client is None:
            return b""

        return client.client_name


    def get_next_buffer_id(self):
        buffer_id = self.next_buffer_id
        self.next_buffer_id = (self.next_buffer_id + 1) % 16
        return buffer_id


    def delegate_packet(self, source_client, dest_client_id, packet):
        dest_client = self.registered_clients.get(dest_client_id, None)

        if dest_client is None:
            # TODO: Respond with an error packet
            return

        dest_client.handle_packet(source_client, packet)


    def broadcast_packet(self, source_client, packet):
        for k in self.registered_clients:
            client = self.registered_clients[k]

            if client == source_client:
                # Don't send packet to source of packet
                continue

            prepared_packet = source_client.generate_packet_status_header(client) + packet
            client.handle_packet(source_client, prepared_packet)


class MsuClientBase:
    packet_internal_input_buffer = bytearray()
    packet_internal_output_buffer = bytearray()
    packet_internal_buffer_input_index = 0
    packet_internal_buffer_output_index = 0
    packet_internal_buffer_next_expected_input_index = 0
    packet_internal_buffer_next_expected_output_index = 0
    packet_internal_buffer_minimum_output_index = 0
    packet_internal_input_buffer_last_executed_index = 0


    def generate_packet_status_header(self, target_client):
        status = 0 # TODO: Will this ever change?
        sourcedest = ((1 << self.client_id) << 4) if self.client_id > 0 else 0
        sourcedest |= (1 << target_client.client_id) if target_client.client_id > 0 else 0
        return bytearray([status, sourcedest])


    def escape_packet(self, packet):
        output = bytearray()

        for c in packet:
            if c == 0xc0:
                output.append(0xdb)
                output.append(0xdc)

            elif c == 0xdb:
                output.append(0xdb)
                output.append(0xdd)

            else:
                output.append(c)

        return output


    def unescape_packet(self, packet):
        output = bytearray()
        i = 0

        while i < len(packet):
            c = packet[i]

            if i + 1 < len(packet) and c == 0xdb:
                if packet[i+1] == 0xdd:
                    c = 0xdb
                    i += 1

                elif packet[i+1] == 0xdc:
                    c = 0xc0
                    i += 1

            output.append(c)
            i += 1

        return output


    def prepare_response_packet(self, packet):
        checksum = calc_crc16(bytearray(packet)).to_bytes(2, byteorder="little")
        return b"\xc0" + self.escape_packet(packet + checksum) + b"\xc0"


    def extract_client_id(self, val):
        client_id = (val & -val).bit_length() - 1
        return client_id


class MsuSessionClient(MsuClientBase):
    packet_output_buffers = {}
    timestamp_looper = None
    cur_timestamp = 0

    def __init__(self):
        print("MsuSessionClient")
        self.msu_server = MsuServer.get_instance()
        self.client_id = 0
        self.client_name = b"SESSION"
        self.msu_server.register_client(self, self.client_id)


    def broadcast_timestamp_update(self):
        if self.cur_timestamp > 0xffffff:
            self.msu_server.broadcast_packet(self, bytearray([0x46]) + int.to_bytes(self.cur_timestamp, 4, 'little'))

        else:
            self.msu_server.broadcast_packet(self, bytearray([0x4e]) + int.to_bytes(self.cur_timestamp, 3, 'little'))

        self.cur_timestamp += 750



    # Opcode handlers
    def opcode_register_client(self, source_client, packet):
        # MSU Handler: 80001238
        # MSU Response: 80001328
        # DM10 Handler: 80065d34
        # Returns the port number for the player
        client_name_len = min(packet[0], 0x20)
        client_name = packet[1:][:client_name_len]
        assert(len(client_name) == client_name_len)

        source_client.client_name = client_name
        self.msu_server.register_client(source_client, source_client.client_id)
        source_client.buffer_id = self.msu_server.get_next_buffer_id()

        # TODO: Put this on a timer to send 4 times
        val = (source_client.buffer_id << 4) | source_client.client_id
        self.msu_server.broadcast_packet(self, bytearray([0x01, val]))

        # TOOD: Reset full client state at this time
        # if self.buffer_looper is not None:
        #     self.buffer_looper.stop()
        #     self.buffer_looper = None

        self.packet_output_buffers[source_client.client_id] = []
        source_client.packet_internal_input_buffer = bytearray()
        source_client.packet_internal_output_buffer = bytearray()
        source_client.packet_internal_buffer_input_index = 0
        source_client.packet_internal_buffer_output_index = 0
        source_client.packet_internal_buffer_next_expected_input_index = 0
        source_client.packet_internal_buffer_next_expected_output_index = 0
        source_client.packet_internal_buffer_minimum_output_index = 0
        source_client.packet_internal_input_buffer_last_executed_index = 0

        response_payload = bytearray([source_client.client_id])
        response = PacketResponse(0x03, response_payload)
        return packet[1+client_name_len:], response


    def opcode_get_registered_client(self, source_client, packet):
        # MSU Handler: 800014b0
        # MSU Response: 80001568
        # DM10 Handler: 80065824
        # Returns the requested client name string of the request size

        client_idx = packet[0]
        name_len = min(packet[1], 0x20)

        client_name = self.msu_server.get_registered_client_name(client_idx)

        if len(client_name) < name_len:
            client_name += b"\0" * (name_len - len(client_name))

        response_payload = bytearray([name_len]) + client_name[:name_len]
        response = PacketResponse(0x05, response_payload)
        return packet[2:], response


    def opcode_echo(self, source_client, packet):
        # MSU Handler: 8000110c
        # MSU Response: 80001194
        # DM10 Handler: 80065b10
        # Returns the exact same data that was sent to it
        payload_len = min(packet[0], 0x3e)
        payload = packet[1:][:payload_len]
        assert(len(payload) == payload_len)

        response_payload = packet[:1+payload_len]
        response = PacketResponse(0x07, response_payload)
        return packet[1+payload_len:], response


    def opcode_keepalive(self, source_client, packet):
        # MSU Handler: 80001048
        # MSU Response: 80001098
        # DM10 Handler: 80065f1c
        # Returns nothing
        response = PacketResponse(0x1f)
        return packet, response


    def opcode_20(self, source_client, packet):
        # MSU Handler: 8000250c
        # MSU Response: 80002518
        # DM10 Handler: 80065e90
        # Returns a length and 4 bytes (what data? timestamps?)

        # Sets +0x1a04 to 1
        # Will return either 1 or 2? Seems to only be set at 0x800005cc
        # Possibly related to file loading???
        val = 1
        response_payload = bytearray([0x04]) + int.to_bytes(val, 4, 'little') # Big endian?
        response = PacketResponse(0x21, response_payload)
        return packet, response


    def opcode_load_file(self, source_client, packet):
        # MSU Handler: 80001724
        # MSU Response: 80001804
        # DM10 Handler: 80065f58
        filename_len = packet[0]
        filename = packet[1:][:filename_len]
        assert(len(filename) == filename_len)

        # TODO: Implement some code to load/check for file here
        # Starts fifotask
        success = True # File was successfully loaded or not

        response_payload = bytearray([int(success)])
        response = PacketResponse(0x41, response_payload)
        return packet[1+filename_len:], response


    def opcode_42(self, source_client, packet):
        # MSU Handler: 80001868
        # MSU Response: 800018fc
        # DM10 Handler: 80065fa8

        # TODO: Calls some function, 80005e58, and the return value is based on its result
        # Starts fifotask
        # Used to call: FUN_80005e58(*(obj + 0x19cc), [4, 0, 1, 2, 3][self.client_id])
        success = True

        response_payload = bytearray([int(success)])
        response = PacketResponse(0x43, response_payload)
        return packet, response


    def opcode_44(self, source_client, packet):
        # MSU Handler: 80001960
        # MSU Response: 80001a18
        # DM10 Handler: 80065ff8
        param = min(packet[0], 0x7f)

        # TODO: Calls some function, 80005eb8, and the return value is based on its result
        # Used to call: FUN_80005eb8(*(obj + 0x19cc), [4, 0, 1, 2, 3][self.client_id], param)
        success = True

        response_payload = bytearray([int(success)])
        response = PacketResponse(0x45, response_payload)
        return packet[1:], response


    def opcode_48(self, source_client, packet):
        # MSU Handler: 80001b98
        # MSU Response: 80001c0c
        # DM10 Handler: 80066108

        # Functionally the same as 0x4c
        # Will always return 1

        param1 = packet[0] & 3
        param2 = packet[0] >> 2

        response_payload = bytearray([1])
        response = PacketResponse(0x49, response_payload)
        return packet[1:], response


    def opcode_4a(self, source_client, packet):
        # MSU Handler: 80001a7c
        # MSU Response: 80001b34
        # DM10 Handler: 80066154

        param = packet[0] & 1

        # TODO: In 80001a7c, a function (80005e8c) is called.
        # If it fails, the result will be 2. If it succeeds, it's 1.
        # Figure out what the function is doing.
        # Used to call: FUN_80005e8c(*(obj + 0x19cc), [4, 0, 1, 2, 3][self.client_id], param)
        success = True

        response_payload = bytearray([int(success)])
        response = PacketResponse(0x4b, response_payload)
        return packet[1:], response


    def opcode_4c(self, source_client, packet):
        # MSU Handler: 80001c68
        # MSU Response: 80001cd8
        # DM10 Handler: 800661a4

        # Functionally the same as 0x48
        # Will always return 1

        param1 = packet[0] & 3
        param2 = packet[0] >> 2

        response_payload = bytearray([1])
        response = PacketResponse(0x4d, response_payload)
        return packet[1:], response


    def opcode_50(self, source_client, packet):
        # MSU Handler: 80001ef0
        # MSU Response: 800020a4
        # DM10 Handler: 80066248

        param1 = packet[0] & 0x0f
        param6 = packet[2] & 1
        param7 = (packet[2] >> 1) & 3
        # This is really a lookup table and a branch in the real code but this is equivalent
        # unk_param = (0x10 << param7) * param6
        # Used to call: FUN_8000d288([4, 0, 1, 2, 3][self.client_id], ((0x10 << param7) * param6) | param1)

        param2 = packet[1] & 3
        param3 = (packet[1] >> 2) & 3
        param4 = (packet[1] >> 4) & 3
        param5 = (packet[1] >> 6) & 3
        param8 = (packet[2] >> 3) & 3
        # Used in another call: FUN_8000e36c([4, 0, 1, 2, 3][self.client_id], (param8 << 8) | (param2 << 6) | (param3 << 4) | (param4 << 2) | param5)


        # Possibly in charge of starting songs?
        # param1 == 1 is start song?
        # param1 == 0 is stop song?

        if param1 == 1:
            self.cur_timestamp = 0
            self.timestamp_looper = task.LoopingCall(self.broadcast_timestamp_update)
            self.timestamp_looper.start(0.025)

        elif param1 == 0 and self.timestamp_looper is not None and self.timestamp_looper.running:
            self.timestamp_looper.stop()

        response_payload = bytearray([int((2 if param8 == 2 else 1) == 1)])
        response = PacketResponse(0x51, response_payload)
        return packet[3:], response


    def opcode_58(self, source_client, packet):
        # MSU Handler: 80002108
        # MSU Response: 800021a4
        # DM10 Handler: 80066290
        # Will always return 1

        param = packet[0] & 1
        s = ((3 - [4, 0, 1, 2, 3][self.client_id]) * 2 + 9) & 0x1f
        # REG_B0400040 &= ~(1 << s) # Clear bit
        # REG_B0400040 |= param << s # Set bit with param

        response_payload = bytearray([1])
        response = PacketResponse(0x59, response_payload)
        return packet[1:], response


    def opcode_60(self, source_client, packet):
        # MSU Handler: 80002200
        # MSU Response: 8000229c
        # DM10 Handler: 800662d8
        # Will always return 1

        param = packet[0] & 1
        s = ((3 - [4, 0, 1, 2, 3][self.client_id]) * 2 + 8) & 0x1f
        # REG_B0400040 &= ~(1 << s) # Clear bit
        # REG_B0400040 |= param << s # Set bit with param

        response_payload = bytearray([1])
        response = PacketResponse(0x61, response_payload)
        return packet[1:], response


    def opcode_62(self, source_client, packet):
        # MSU Handler: 800022f8
        # MSU Response: 80002394
        # DM10 Handler: 80066320
        # Will always return 1

        param = packet[0] & 1
        s = (7 - [4, 0, 1, 2, 3][self.client_id]) & 0x1f
        # REG_B0400040 &= ~(1 << s) # Clear bit
        # REG_B0400040 |= param << s # Set bit with param

        response_payload = bytearray([1])
        response = PacketResponse(0x63, response_payload)
        return packet[1:], response


    def opcode_68(self, source_client, packet):
        # MSU Handler: 800023f8
        # MSU Response: 8000245c
        # DM10 Handler: 80066368

        # TODO: Calls a function, 80005878, and the return value is used as the result of the opcode
        success = True

        response_payload = bytearray([int(success)])
        response = PacketResponse(0x69, response_payload)
        return packet, response


    def opcode_chain_packet(self, source_client, packet):
        buffer_input_index = packet[0]
        buffer_output_index = packet[1]
        payload_len = packet[2]
        packet = packet[3:]

        payload = packet[:payload_len]
        packet = packet[payload_len:]

        print("%02x %02x %02x | %02x %02x %02x" % (buffer_input_index, len(source_client.packet_internal_input_buffer), source_client.packet_internal_buffer_input_index, buffer_output_index, len(source_client.packet_internal_output_buffer), source_client.packet_internal_buffer_output_index))

        if buffer_input_index > len(source_client.packet_internal_input_buffer):
            print("buffer_input_index > len(source_client.packet_internal_input_buffer): %d > %d" % (buffer_input_index, len(source_client.packet_internal_input_buffer)))
            # If the input index is greater then it gets set to the end of the input index buffer and is not executed
            source_client.packet_internal_buffer_input_index = len(source_client.packet_internal_input_buffer)
            return packet, PacketResponse(None)

        if buffer_output_index > len(source_client.packet_internal_output_buffer):
            print("buffer_output_index > len(source_client.packet_internal_output_buffer): %d > %d" % (buffer_output_index, len(source_client.packet_internal_output_buffer)))
            # If the output index is greater then the command gets ignored and the output index is not updated
            return packet, PacketResponse(None)

        if buffer_input_index > source_client.packet_internal_buffer_input_index:
            # It's possible to increase but not decrease this by sending FF commands, even if the command fails
            source_client.packet_internal_buffer_input_index = buffer_input_index

        if buffer_output_index > source_client.packet_internal_buffer_output_index:
            # It's possible to increase but not decrease this by sending FF commands, even if the command fails
            source_client.packet_internal_buffer_output_index = buffer_output_index

        # TODO: Fix these buffers
        if buffer_input_index == len(source_client.packet_internal_input_buffer) and buffer_output_index <= len(source_client.packet_internal_output_buffer):
            immediate_return_offset = len(source_client.packet_internal_output_buffer)

            source_client.packet_internal_input_buffer += payload
            source_client.packet_internal_buffer_input_index += payload_len

            payload = source_client.packet_internal_input_buffer[source_client.packet_internal_input_buffer_last_executed_index:]
            found_resp = []
            while payload:
                cur_payload_len = len(payload)
                payload, response = self.handle_packet_internal(source_client, payload)

                source_client.packet_internal_input_buffer_last_executed_index += cur_payload_len - len(payload)

                if response.is_valid():
                    if response.cmd == 0x4d and response.cmd in found_resp:
                        continue

                    response_bytes = response.to_bytes()
                    source_client.packet_internal_output_buffer += response_bytes
                    source_client.packet_internal_buffer_next_expected_output_index += len(response_bytes)
                    found_resp.append(response.cmd)


            if payload_len == 0:
                # Hack
                resp2 = PacketResponse(0x47, bytearray([1]))
                self.packet_output_buffers[source_client.client_id].append(resp2)
                found_resp.append(resp2.cmd)

            # The result of the command should be immediately returned, separate from the looped return results
            resp_data = source_client.packet_internal_output_buffer[immediate_return_offset:]
            if resp_data:
                print("Immediate return")
                resp = PacketResponse(0xff, bytearray([immediate_return_offset, source_client.packet_internal_buffer_input_index, len(resp_data)]) + resp_data)
                hexdump.hexdump(resp.to_bytes())
                self.packet_output_buffers[source_client.client_id].append(resp)

        else:
            source_client.packet_internal_buffer_output_index = source_client.packet_internal_buffer_next_expected_output_index

        source_client.packet_internal_buffer_minimum_output_index = source_client.packet_internal_buffer_output_index

        # source_client.send_chain_buffer_packets()

        return packet, PacketResponse(None)


    def handle_packet_internal(self, source_client, packet):
        opcode_handlers = {
            0x02: self.opcode_register_client,
            0x04: self.opcode_get_registered_client,
            0x06: self.opcode_echo,
            0x1e: self.opcode_keepalive,
            0x20: self.opcode_20,
            0x40: self.opcode_load_file,
            0x42: self.opcode_42,
            0x44: self.opcode_44,
            0x48: self.opcode_48,
            0x4a: self.opcode_4a,
            0x4c: self.opcode_4c,
            0x50: self.opcode_50,
            0x58: self.opcode_58,
            0x60: self.opcode_60,
            0x62: self.opcode_62,
            0x68: self.opcode_68,
            0xff: self.opcode_chain_packet,
        }

        cmd = packet[0]
        packet = packet[1:]

        if cmd not in opcode_handlers:
            print("Unknown opcode! %02x" % (cmd))
            return

        return opcode_handlers[cmd](source_client, packet)


    def handle_packet(self, source_client, packet):
        packet = packet[2:] # Remove status and source/dest byte

        found_resp = []
        while packet:
            packet, response = self.handle_packet_internal(source_client, packet)

            if response.is_valid():
                if response.cmd == 0x4d and response.cmd in found_resp:
                    continue

                self.packet_output_buffers[source_client.client_id].append(response)
                found_resp.append(response.cmd)

        self.send_responses()


    def send_responses(self):
        for client_id in self.packet_output_buffers:
            response_packets = []
            output_data = bytearray()

            client = self.msu_server.get_registered_client(client_id)
            packet_header = self.generate_packet_status_header(client)

            while self.packet_output_buffers[client_id]:
                packet = self.packet_output_buffers[client_id].pop(0)

                if not packet.is_valid():
                    continue

                payload = packet.to_bytes()
                if output_data and len(payload) + len(output_data) + 3 > 0x40:
                    # Reached max packet size limit, send rest of data in another packet
                    response_packets.append(packet_header + output_data)
                    output_data = bytearray()

                output_data += payload

            if output_data:
                response_packets.append(packet_header + output_data)

            for output in response_packets:
                client.send_packet(self, self.prepare_response_packet(output))


class MsuClient(MsuClientBase, Protocol):
    packets = []
    packet_input_buffers = []
    packet_chain_responses = {}
    chain_buffer_counter = 0
    last_sent_chain_packet = bytearray()


    def __init__(self, client_id):
        self.msu_server = MsuServer.get_instance()
        self.client_id = client_id

        self.buffer_looper = task.LoopingCall(self.send_chain_buffer_packets)
        self.buffer_looper.start(0.5)


    def send_chain_buffer_packets(self):
        # if self.chain_buffer_counter > 3:
        #     return

        # These packets will always come from the MSU
        session_client = self.msu_server.get_registered_client(0)
        tail_len = self.packet_internal_buffer_next_expected_output_index - self.packet_internal_buffer_output_index
        resp_data = self.packet_internal_output_buffer[-tail_len:] if tail_len > 0 else bytearray()

        print("Called send_chain_buffer_packets for client %d" % self.client_id)
        if resp_data:
            packet_header = session_client.generate_packet_status_header(self)
            resp = PacketResponse(0xff, bytearray([self.packet_internal_buffer_output_index, self.packet_internal_buffer_input_index, len(resp_data)]) + resp_data)
            hexdump.hexdump(packet_header + resp.to_bytes())
            self.send_packet(session_client, self.prepare_response_packet(packet_header + resp.to_bytes()))

            self.chain_buffer_counter += 1

            self.last_sent_chain_packet = self.prepare_response_packet(packet_header + resp.to_bytes())

        elif self.last_sent_chain_packet:
            hexdump.hexdump(self.last_sent_chain_packet)
            self.send_packet(session_client, self.last_sent_chain_packet)


    def send_packet(self, source_sender, packet):
        print("Packet sent to client %d" % (self.client_id))
        hexdump.hexdump(packet)
        self.transport.write(packet)


    def process_packets(self):
        while self.packets:
            packet = self.packets.pop(0)

            print("To MSU (%d):" % (self.client_id))
            hexdump.hexdump(packet)

            packet = packet[1:-3]

            source_client_id = self.extract_client_id(packet[1] >> 4)
            dest_client_id = self.extract_client_id(packet[1] & 0x0f)

            self.msu_server.delegate_packet(self, dest_client_id, packet)


    def handle_packet(self, source_client, packet):
        # Send a packet forwarded from another client to the current client
        print("Packet broadcast to client %d" % (self.client_id))
        packet = self.prepare_response_packet(packet)
        hexdump.hexdump(packet)
        self.transport.write(packet)


    def dataReceived(self, data):
        for i, c in enumerate(data):
            if len(self.packet_input_buffers) != 0 and len(self.packet_input_buffers[-1]) > 1 and self.packet_input_buffers[-1][0] == 0xc0 and self.packet_input_buffers[-1][-1] == 0xc0:
                self.packet_input_buffers.append(bytearray())

            if len(self.packet_input_buffers) == 0 and c == 0xc0:
                self.packet_input_buffers.append(bytearray())

            if len(self.packet_input_buffers) != 0:
                self.packet_input_buffers[-1].append(c)

        output_packet = bytearray()
        for packet in self.packet_input_buffers[::]:
            if not packet:
                self.packet_input_buffers.remove(packet)
                continue

            if packet[0] != 0xc0:
                self.packet_input_buffers.remove(packet)
                continue

            if len(packet) <= 1 or 0xc0 not in packet[1:]:
                continue

            packet_clean = self.unescape_packet(packet)

            # Verify packet
            checksum_packet = int.from_bytes(packet_clean[-3:-1], 'little')
            packet_data = packet_clean[1:-3]
            checksum = calc_crc16(packet_clean[1:-3])
            if checksum != checksum_packet:
                print("Invalid checksum? %04x vs %04x" % (checksum, checksum_packet))
                hexdump.hexdump(packet_clean)
                # exit(1)

            else:
                # print("Checksum good")

                self.packets.append(packet_clean)

            self.packet_input_buffers.remove(packet)

        self.process_packets()


# MsuSessionClient()
# client2 = MsuClient(2)
# client2.client_name = b"TEST"
# client2.msu_server.register_client(client2, client2.client_id)

# client = MsuClient(1)
# client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x00, 0x00, 0x0A, 0x40, 0x08, 0x4A, 0x41, 0x31, 0x30, 0x2E, 0x44, 0x41, 0x54, 0x35, 0x14, 0xC0]))

# # client.dataReceived(bytearray([0xC0, 0x0F, 0x01, 0x02, 0x0A, 0x47, 0x43, 0x44, 0x34, 0x30, 0x4A, 0x41, 0x41, 0x11, 0x01, 0xD5, 0xC8, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x00, 0x00, 0x03, 0x04, 0x01, 0x0A, 0x23, 0xf8, 0xC0]))
# # # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x02, 0x00, 0x03, 0x04, 0x00, 0x0A, 0xad, 0xe9, 0xC0]))

# # # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x03, 0x10, 0x03, 0x04, 0x00, 0x0A, 0xc6, 0x59, 0xC0]))

# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x03, 0x00, 0x03, 0x04, 0x00, 0x0A, 0x86, 0xed, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x06, 0x00, 0x03, 0x04, 0x01, 0x0A, 0xd9, 0xe0, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x09, 0x00, 0x03, 0x04, 0x00, 0x0A, 0x88, 0xc4, 0xC0]))

# # # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xCC, 0x3F, 0xC0]))
# # exit(1)

# # client.dataReceived(bytearray([0xC0, 0x0F, 0x01, 0x02, 0x0A, 0x47, 0x43, 0x44, 0x34, 0x30, 0x4A, 0x41, 0x41, 0x11, 0x01, 0xD5, 0xC8, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x0F, 0x01, 0x06, 0x9d, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0x06, 0x10, 0x48, 0x41, 0x52, 0x44, 0x20, 0x43, 0x48, 0x45, 0x43, 0x4B, 0x20, 0x30, 0x32, 0x38, 0x34, 0x00, 0x9c, 0xd4, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x0C, 0x30, 0x12, 0x58, 0x00, 0x60, 0x00, 0x62, 0x00, 0x4C, 0x00, 0x4C, 0x01, 0x4C, 0x02, 0x4C, 0x03, 0x50, 0x00, 0x00, 0x01, 0xcd, 0x63, 0xC0]))
# # client.dataReceived(bytearray([0xC0, 0x00, 0x21, 0xFF, 0x0C, 0x30, 0x14, 0x58, 0x00, 0x60, 0x00, 0x62, 0x00, 0x4C, 0x00, 0x4C, 0x01, 0x4C, 0x02, 0x4C, 0x03, 0x50, 0x00, 0x00, 0x01, 0x4A, 0x00, 0x76, 0x2c, 0xC0]))
# exit(1)


class MsuClientFactory(Factory):
    def __init__(self, client_id):
        self.client_id = client_id

    def buildProtocol(self, addr):
        return MsuClient(self.client_id)


def main():
    MsuSessionClient()
    reactor.listenTCP(8001, MsuClientFactory(1))
    reactor.listenTCP(8002, MsuClientFactory(2))
    reactor.listenTCP(8003, MsuClientFactory(3))
    reactor.listenTCP(8004, MsuClientFactory(4))
    reactor.run()


if __name__ == "__main__":
    main()
