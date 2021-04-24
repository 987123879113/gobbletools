#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>

const int STEPS[] = {
    256,  272,  304,   336,   368,   400,   448,   496,   544,   592,   656,   720,
    800,  880,  960,  1056,  1168,  1280,  1408,  1552,  1712,  1888,  2080,  2288,
    2512, 2768, 3040,  3344,  3680,  4048,  4464,  4912,  5392,  5936,  6528,  7184,
    7904, 8704, 9568, 10528, 11584, 12736, 14016, 15408, 16960, 18656, 20512, 22576,
    24832
};

const int CHANGES[] = {
    -1, -1, -1, -1, 2, 4, 6, 8,
    -1, -1, -1, -1, 2, 4, 6, 8
};

class AdpcmWave {
public:
    AdpcmWave() {
    }

    unsigned short *process_sample_batch(unsigned char *samples, int samples_len, unsigned short *output, int output_offset, bool encode, int channel, int cidx_max) {
        int step_index = 0;
        int pcm_sample = 0;
        int sample_encode = 0;
        int mask = 0xfffffffe;

        for(int idx = 0; idx < samples_len; idx += cidx_max) {
            for(int cidx = 0; cidx < cidx_max; cidx++) {
                int sample = 0;

                if (encode) {
                    sample = *(short*)(samples + (idx + cidx) * (4 / cidx_max) + (channel * 2));
                } else {
                    sample = samples[idx / cidx_max];

                    if (channel + cidx == 0) {
                        sample = (sample >> 4) & 0x0f;
                    } else if (channel + cidx == 1) {
                        sample = sample & 0x0f;
                    }
                }

                int step = STEPS[step_index];

                if (encode) {
                    int delta = sample - pcm_sample;

                    int sign = 0;
                    if (delta < 0) {
                        sign = 0x08;
                        delta = -delta;
                    }

                    int v = (delta << 2);
                    v = v / step;


                    if (v > 7) {
                        v = 7;
                    }

                    sample = sign | v;
                    sample_encode = sample;
                }

                int new_sample = (step >> 3)
                    + ((step >> 2) & -(sample & 1))
                    + ((step >> 1) & -((sample >> 1) & 1))
                    + (step & -((sample >> 2) & 1));

                step_index += CHANGES[sample % 16];

                if (step_index > 48) {
                    step_index = 48;
                } else if (step_index < 0) {
                    step_index = 0;
                }

                if ((sample & 0x08) != 0) {
                    new_sample = -new_sample;
                }

                pcm_sample += new_sample;

                if (pcm_sample > 32767) {
                    pcm_sample = 32767;
                } else if (pcm_sample < -32768) {
                    pcm_sample = -32768;
                }

                if (encode) {
                    if (channel + cidx == 0) {
                        ((unsigned char*)output)[idx / cidx_max] |= (unsigned char)(((sample_encode & 0xff) << 4) & 0xff);
                    } else if (channel + cidx == 1) {
                        ((unsigned char*)output)[idx / cidx_max] |= (unsigned char)(sample_encode & 0xff);
                    }
                } else {
                    output[((idx / cidx_max) * 2) + output_offset + cidx] = (unsigned short)(pcm_sample & 0xffff);
                }
            }
        }

        return output;
    }
};

unsigned char *process_stereo(unsigned char *samples, int samples_len, int *output_len, bool encode) {
    AdpcmWave decoder;
    AdpcmWave decoder2;

    unsigned short *output = (unsigned short*)calloc(samples_len * 2, sizeof(unsigned short));

    if (encode) {
        decoder.process_sample_batch(samples, samples_len / 2 / 2, output, 0, encode, 0, 1);
        decoder2.process_sample_batch(samples, samples_len / 2 / 2, output, 1, encode, 1, 1);
        *output_len = samples_len / 4;
    } else {
        decoder.process_sample_batch(samples, samples_len, output, 0, encode, 0, 1);
        decoder2.process_sample_batch(samples, samples_len, output, 1, encode, 1, 1);
        *output_len = samples_len * 2 * sizeof(unsigned short);
    }

    return (unsigned char*)output;
}

unsigned char *process_mono(unsigned char *samples, int samples_len, int *output_len, bool encode) {
    AdpcmWave decoder;

    unsigned short *output = (unsigned short*)calloc(samples_len * 2, sizeof(unsigned short));

    if (encode) {
        decoder.process_sample_batch(samples, samples_len / 2, output, 0, encode, 0, 2);
        *output_len = samples_len / 4;
    } else {
        decoder.process_sample_batch(samples, samples_len * 2, output, 0, encode, 0, 2);
        *output_len = samples_len * 2 * sizeof(unsigned short);
    }

    return (unsigned char*)output;
}

int parse_file(char *mode, char *filename, char *output_filename, int channels) {
    FILE *file = fopen(filename, "rb");

    if (!file) {
        printf("Couldn't open %s\n", filename);
        exit(1);
    }

    int samples_len = 0;
    fseek(file, 0, SEEK_END);
    samples_len = ftell(file);
    rewind(file);

    unsigned char *samples = (unsigned char*)calloc(samples_len, sizeof(unsigned char));
    fread(samples, 1, samples_len, file);
    fclose(file);

    int output_len = 0;
    unsigned char *decoded;

    uint32_t data_offset = 0;
    if (memcmp(samples, "ADP\x02", 4) == 0) {
        uint32_t filesize = (samples[4] << 24) | (samples[5] << 16) | (samples[6] << 8) | samples[7];

        if (filesize == samples_len - 0x10) {
            data_offset = 0x10;
            printf("Found PPP 2nd ADP file, skipping header\n");
        }
    }

    bool is_encode = mode[0] == 'e' || mode[0] == 'E';
    if (channels == 1) {
        decoded = process_mono(samples + data_offset, samples_len - data_offset, &output_len, is_encode);
    } else if (channels == 2) {
        decoded = process_stereo(samples + data_offset, samples_len - data_offset, &output_len, is_encode);
    }

    file = fopen(output_filename, "wb");
    fwrite(decoded, 1, output_len, file);
    fclose(file);

    free(samples);
    free(decoded);
}

int main(int argc, char **argv) {
    if (argc != 5) {
        printf("usage: %s [d/e] input output channels\n", argv[0]);
        exit(1);
    }

    parse_file(argv[1], argv[2], argv[3], atoi(argv[4]));
}