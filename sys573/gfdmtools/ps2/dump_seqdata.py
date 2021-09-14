import argparse
import ctypes
import os


def get_filename_hash(filename):
    def rshift(val, n): return val>>n if val >= 0 else (val+0x100000000)>>n
    def lshift(val, n): return val<<n if val >= 0 else (val+0x100000000)<<n

    filename_hash = 0

    for i, c in enumerate(filename.encode('ascii')):
        filename_hash = (((rshift(filename_hash, 23)) | (lshift(filename_hash, 5))) + c) & 0x0fffffff

    return filename_hash & 0xffffffff

class DecodeGfdm:
    def __init__(self, data):
        self.data = data

        self.unk = int.from_bytes(data[:4], 'little')
        self.cur_offset = 4
        self.cur_bit = -1

        self.tree = self.build_tree()
        self.build_starts()
        self.build_lookups()

    def get_bit(self):
        def rshift(val, n): return val>>n if val >= 0 else (val+0x100000000)>>n

        if self.cur_bit < 0:
            self.cur_bit = 7
            self.orig_flag = self.data[self.cur_offset]
            self.flag = ctypes.c_byte(self.data[self.cur_offset]).value
            self.cur_offset += 1

        ret = rshift(self.flag, self.cur_bit) & 1
        self.cur_bit -= 1

        return ret

    def get_byte(self):
        cur_idx = 0x100

        while True:
            bit = self.get_bit()
            cur_idx = [self.lookup_l, self.lookup_r][bit][cur_idx]

            if cur_idx < 0x100:
                break

        return cur_idx


    def build_tree(self):
        tree = bytearray(0x100)
        tree_idx = 0
        s3 = 0

        if self.data[self.cur_offset] == 0:
            return self.data

        while tree_idx < 0x100:
            if self.get_bit() == 0:
                tree[tree_idx] = s3
                tree_idx += 1

            else:
                s1 = 1

                cnt = 0
                while self.get_bit() == 0:
                    cnt += 1

                while cnt > 0:
                    s1 = (s1 << 1) | self.get_bit()
                    cnt -= 1

                s3 ^= s1
                tree[tree_idx] = s3
                tree_idx += 1

        return tree

    def build_starts(self):
        self.statistics = [0] * 16
        for c in self.tree:
            if c >= 0x11:
                raise Exception("Invalid code")

            else:
                self.statistics[c] += 1

        self.starts = [0] * 16
        for i in range(1, 16-1):
            self.starts[i+1] = (self.starts[i] + self.statistics[i]) * 2

        self.offsets = [0] * len(self.tree)
        for idx in range(len(self.starts)):
            for i, c in enumerate(self.tree):
                if c == idx:
                    self.offsets[i] += self.starts[idx]
                    self.starts[idx] += 1

    def build_lookups(self):
        lookup_r = [0] * 0x10000
        lookup_l = [0] * 0x10000

        cur_idx = len(self.tree)
        next_idx = len(self.tree) + 1
        lookup_r[cur_idx] = lookup_l[cur_idx] = -1
        lookup_r[next_idx] = lookup_l[next_idx] = -1

        for i, c in enumerate(self.tree):
            if c == 0:
                continue

            cur_idx = len(self.tree)

            is_right = False
            for j in range(0, c):
                is_right = (self.offsets[i] >> (c - j - 1)) & 1

                if j + 1 == c:
                    break

                if is_right:
                    a1 = lookup_r[cur_idx]
                    if a1 == -1:
                        lookup_r[cur_idx] = next_idx

                    else:
                        cur_idx = a1

                else:
                    a1 = lookup_l[cur_idx]
                    if a1 == -1:
                        lookup_l[cur_idx] = next_idx

                    else:
                        cur_idx = a1

                if a1 == -1:
                    lookup_l[next_idx] = -1
                    lookup_r[next_idx] = -1
                    cur_idx = next_idx
                    next_idx += 1

            if is_right:
                lookup_r[cur_idx] = i

            else:
                lookup_l[cur_idx] = i

        self.lookup_r = lookup_r
        self.lookup_l = lookup_l

    def decode(self):
        output = []

        decomp_size = int.from_bytes(self.data[:4], 'little')
        for i in range(decomp_size):
            output.append(self.get_byte() & 0xff)

        return bytearray(output)


def decode_lz(input_data):
    output = bytearray()
    input_data = bytearray(input_data)
    idx = 0
    distance = 0
    control = 0

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

        length = None
        if (data & 0x80) == 0:
            distance = ((data & 0x03) << 8) | input_data[idx]
            length = (data >> 2) + 2
            idx += 1

        elif (data & 0x40) == 0:
            distance = (data & 0x0f) + 1
            length = (data >> 4) - 7

        if length is not None:
            start_offset = len(output)
            idx2 = 0

            while idx2 <= length:
                output.append(output[(start_offset - distance) + idx2])
                idx2 += 1

            continue

        if data == 0xff:
            break

        length = data - 0xb9
        while length >= 0:
            output.append(input_data[idx])
            idx += 1
            length -= 1

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input file', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="output")

    args = parser.parse_args()

    base_filename = os.path.basename(args.input)

    filename_table = None
    if base_filename == "d_seq.dat":
        filename_table = [
            "seq013prac.dsq",
            "seq020lnkn.dsq",
            "seq020lnkx.dsq",
            "seq020norm.dsq",
            "seq020real.dsq",
            "seq021expr.dsq",
            "seq021lnkn.dsq",
            "seq021lnkx.dsq",
            "seq021norm.dsq",
            "seq021real.dsq",
            "seq022expr.dsq",
            "seq022lnkn.dsq",
            "seq022lnkx.dsq",
            "seq022real.dsq",
            "seq023expr.dsq",
            "seq023lnkn.dsq",
            "seq023lnkx.dsq",
            "seq023norm.dsq",
            "seq023real.dsq",
            "seq024expr.dsq",
            "seq024lnkn.dsq",
            "seq024lnkx.dsq",
            "seq024norm.dsq",
            "seq100expr.dsq",
            "seq100lnkn.dsq",
            "seq100lnkx.dsq",
            "seq100norm.dsq",
            "seq100real.dsq",
            "seq101expr.dsq",
            "seq101lnkn.dsq",
            "seq101lnkx.dsq",
            "seq101norm.dsq",
            "seq101real.dsq",
            "seq102expr.dsq",
            "seq102lnkn.dsq",
            "seq102lnkx.dsq",
            "seq102real.dsq",
            "seq103expr.dsq",
            "seq103lnkn.dsq",
            "seq103lnkx.dsq",
            "seq103norm.dsq",
            "seq103real.dsq",
            "seq104easy.dsq",
            "seq104expr.dsq",
            "seq104lnkn.dsq",
            "seq104lnkx.dsq",
            "seq104norm.dsq",
            "seq104prac.dsq",
            "seq104real.dsq",
            "seq105expr.dsq",
            "seq105lnkn.dsq",
            "seq105lnkx.dsq",
            "seq105real.dsq",
            "seq106expr.dsq",
            "seq106real.dsq",
            "seq107expr.dsq",
            "seq107real.dsq",
            "seq108expr.dsq",
            "seq109expr.dsq",
            "seq109norm.dsq",
            "seq109real.dsq",
            "seq110expr.dsq",
            "seq110lnkn.dsq",
            "seq110lnkx.dsq",
            "seq110norm.dsq",
            "seq110real.dsq",
            "seq111expr.dsq",
            "seq111lnkn.dsq",
            "seq111lnkx.dsq",
            "seq111norm.dsq",
            "seq111real.dsq",
            "seq112expr.dsq",
            "seq112lnkn.dsq",
            "seq112lnkx.dsq",
            "seq112real.dsq",
            "seq113expr.dsq",
            "seq113lnkn.dsq",
            "seq113lnkx.dsq",
            "seq113real.dsq",
            "seq114expr.dsq",
            "seq114lnkn.dsq",
            "seq114lnkx.dsq",
            "seq114real.dsq",
            "seq115expr.dsq",
            "seq115lnkn.dsq",
            "seq115lnkx.dsq",
            "seq115norm.dsq",
            "seq115real.dsq",
            "seq117easy.dsq",
            "seq117expr.dsq",
            "seq117norm.dsq",
            "seq117prac.dsq",
            "seq117real.dsq",
            "seq118expr.dsq",
            "seq118norm.dsq",
            "seq118real.dsq",
            "seq119easy.dsq",
            "seq119norm.dsq",
            "seq119prac.dsq",
            "seq119real.dsq",
            "seq121expr.dsq",
            "seq121norm.dsq",
            "seq122easy.dsq",
            "seq122norm.dsq",
            "seq122real.dsq",
            "seq123easy.dsq",
            "seq123expr.dsq",
            "seq123norm.dsq",
            "seq123prac.dsq",
            "seq123real.dsq",
            "seq126lnkn.dsq",
            "seq126lnkx.dsq",
            "seq127expr.dsq",
            "seq127norm.dsq",
            "seq128norm.dsq",
            "seq128easy.dsq",
            "seq117lnkn.dsq",
            "seq117lnkx.dsq",
            "seq123lnkn.dsq",
            "seq123lnkx.dsq",
            "seq118lnkn.dsq",
            "seq118lnkx.dsq"
        ]

    elif base_filename == "g_seq.dat":
        filename_table = [
            "mm_n_1p1.bin",
            "mm_n_1p2.bin",
            "mm_n_2p1.bin",
            "mm_n_2p2.bin",
            "mm_x_1p1.bin",
            "mm_x_2p1.bin",
            "mm_x_2p2.bin",
            "mm_z_1p1.bin",
            "mm_z_2p1.bin",
            "mm_z_2p2.bin",
            "ct_n_1p1.bin",
            "ct_n_1p2.bin",
            "ct_n_2p1.bin",
            "ct_n_2p2.bin",
            "ct_e_1p1.bin",
            "ct_e_1p2.bin",
            "ct_e_2p1.bin",
            "ct_e_2p2.bin",
            "ct_x_1p1.bin",
            "ct_x_2p1.bin",
            "ct_x_2p2.bin",
            "ct_w_1p1.bin",
            "ct_z_2p1.bin",
            "ct_z_2p2.bin",
            "ctse_1p1.bin",
            "ctse_1p2.bin",
            "ctse_2p1.bin",
            "ctse_2p2.bin",
            "ctsx_1p1.bin",
            "ctsx_2p1.bin",
            "ctsx_2p2.bin",
            "ad_n_1p1.bin",
            "ad_n_1p2.bin",
            "ad_n_2p1.bin",
            "ad_n_2p2.bin",
            "ad_e_1p1.bin",
            "ad_e_1p2.bin",
            "ad_e_2p1.bin",
            "ad_e_2p2.bin",
            "ad_x_1p1.bin",
            "ad_x_2p1.bin",
            "ad_x_2p2.bin",
            "ad_z_1p1.bin",
            "ad_z_2p1.bin",
            "ad_z_2p2.bin",
            "adse_1p1.bin",
            "adse_1p2.bin",
            "adse_2p1.bin",
            "adse_2p2.bin",
            "adsx_1p1.bin",
            "adsx_2p1.bin",
            "adsx_2p2.bin",
            "hd_n_1p1.bin",
            "hd_n_1p2.bin",
            "hd_n_2p1.bin",
            "hd_n_2p2.bin",
            "hd_x_1p1.bin",
            "hd_x_2p1.bin",
            "hd_x_2p2.bin",
            "hd_z_1p1.bin",
            "hd_z_2p1.bin",
            "hd_z_2p2.bin",
            "rf_n_1p1.bin",
            "rf_n_1p2.bin",
            "rf_n_2p1.bin",
            "rf_n_2p2.bin",
            "rf_x_1p1.bin",
            "rf_x_2p1.bin",
            "rf_x_2p2.bin",
            "rf_z_1p1.bin",
            "rf_z_2p1.bin",
            "rf_z_2p2.bin",
            "sb_n_1p1.bin",
            "sb_n_1p2.bin",
            "sb_n_2p1.bin",
            "sb_n_2p2.bin",
            "sb_x_1p1.bin",
            "sb_x_2p1.bin",
            "sb_x_2p2.bin",
            "sb_z_1p1.bin",
            "sb_z_2p1.bin",
            "sb_z_2p2.bin",
            "lt_n_1p1.bin",
            "lt_n_1p2.bin",
            "lt_n_2p1.bin",
            "lt_n_2p2.bin",
            "lt_x_1p1.bin",
            "lt_x_2p1.bin",
            "lt_x_2p2.bin",
            "lt_z_1p1.bin",
            "lt_z_2p1.bin",
            "lt_z_2p2.bin",
            "uc_n_1p1.bin",
            "uc_n_1p2.bin",
            "uc_n_2p1.bin",
            "uc_n_2p2.bin",
            "uc_x_1p1.bin",
            "uc_x_2p1.bin",
            "uc_x_2p2.bin",
            "uc_z_1p1.bin",
            "uc_z_2p1.bin",
            "uc_z_2p2.bin",
            "sh_n_bas.bin",
            "sh_x_bas.bin",
            "sh_x_bas.bin",
            "sh_n_1p1.bin",
            "sh_n_1p2.bin",
            "sh_n_2p1.bin",
            "sh_n_2p2.bin",
            "sh_x_1p1.bin",
            "sh_x_2p1.bin",
            "sh_x_2p2.bin",
            "sh_z_1p1.bin",
            "sh_z_2p1.bin",
            "sh_z_2p2.bin",
            "bs_n_bas.bin",
            "bs_x_bas.bin",
            "bs_x_bas.bin",
            "bs_n_1p1.bin",
            "bs_n_1p2.bin",
            "bs_n_2p1.bin",
            "bs_n_2p2.bin",
            "bs_x_1p1.bin",
            "bs_x_2p1.bin",
            "bs_x_2p2.bin",
            "bs_z_1p1.bin",
            "bs_z_2p1.bin",
            "bs_z_2p2.bin",
            "bd_n_bas.bin",
            "bd_x_bas.bin",
            "bd_n_1p1.bin",
            "bd_n_1p2.bin",
            "bd_n_2p1.bin",
            "bd_n_2p2.bin",
            "bd_x_1p1.bin",
            "bd_x_2p1.bin",
            "bd_x_2p2.bin",
            "pr_n_bas.bin",
            "pr_x_bas.bin",
            "pr_n_1p1.bin",
            "pr_n_1p2.bin",
            "pr_n_2p1.bin",
            "pr_n_2p2.bin",
            "pr_x_1p1.bin",
            "pr_x_2p1.bin",
            "pr_x_2p2.bin",
            "pp_n_bas.bin",
            "pp_e_bas.bin",
            "pp_x_bas.bin",
            "pp_x_bas.bin",
            "pp_n_1p1.bin",
            "pp_n_1p2.bin",
            "pp_n_2p1.bin",
            "pp_n_2p2.bin",
            "pp_e_1p1.bin",
            "pp_e_2p1.bin",
            "pp_e_2p2.bin",
            "pp_x_1p1.bin",
            "pp_x_2p1.bin",
            "pp_x_2p2.bin",
            "pp_z_1p1.bin",
            "pp_z_2p1.bin",
            "pp_z_2p2.bin",
            "cs_n_bas.bin",
            "cs_x_bas.bin",
            "cs_x_bas.bin",
            "cs_n_1p1.bin",
            "cs_n_1p2.bin",
            "cs_n_2p1.bin",
            "cs_n_2p2.bin",
            "cs_e_1p1.bin",
            "cs_e_2p1.bin",
            "cs_e_2p2.bin",
            "cs_x_1p1.bin",
            "cs_x_2p1.bin",
            "cs_x_2p2.bin",
            "cs_z_1p1.bin",
            "cs_z_2p1.bin",
            "cs_z_2p2.bin",
            "m1_n_1p1.bin",
            "m1_n_1p2.bin",
            "m1_n_2p1.bin",
            "m1_n_2p2.bin",
            "m1_x_1p1.bin",
            "m1_x_2p1.bin",
            "m1_x_2p2.bin",
            "m1_z_1p1.bin",
            "m1_z_2p1.bin",
            "m1_z_2p2.bin",
            "m2_n_1p1.bin",
            "m2_n_1p2.bin",
            "m2_n_2p1.bin",
            "m2_n_2p2.bin",
            "m2_x_1p1.bin",
            "m2_x_2p1.bin",
            "m2_x_2p2.bin",
            "m2_z_1p1.bin",
            "m2_z_2p1.bin",
            "m2_z_2p2.bin",
            "m3_n_1p1.bin",
            "m3_n_1p2.bin",
            "m3_n_2p1.bin",
            "m3_n_2p2.bin",
            "m3_x_1p1.bin",
            "m3_x_2p1.bin",
            "m3_x_2p2.bin",
            "m3_z_1p1.bin",
            "m3_z_2p1.bin",
            "m3_z_2p2.bin",
            "lf_n_1p1.bin",
            "lf_n_1p2.bin",
            "lf_n_2p1.bin",
            "lf_n_2p2.bin",
            "lf_x_1p1.bin",
            "lf_x_2p1.bin",
            "lf_x_2p2.bin",
            "lf_z_1p1.bin",
            "lf_z_2p1.bin",
            "lf_z_2p2.bin",
            "sm_n_bas.bin",
            "sm_x_bas.bin",
            "sm_x_bas.bin",
            "sm_n_1p1.bin",
            "sm_n_1p2.bin",
            "sm_n_2p1.bin",
            "sm_n_2p2.bin",
            "sm_x_1p1.bin",
            "sm_x_2p1.bin",
            "sm_x_2p2.bin",
            "sm_n_1p1.bin",
            "sm_n_2p1.bin",
            "sm_n_2p2.bin",
            "st_n_bas.bin",
            "st_x_bas.bin",
            "st_n_1p1.bin",
            "st_n_1p2.bin",
            "st_n_2p1.bin",
            "st_n_2p2.bin",
            "st_x_1p1.bin",
            "st_x_2p1.bin",
            "st_x_2p2.bin",
            "st_z_1p1.bin",
            "st_z_2p1.bin",
            "st_z_2p2.bin",
            "hi_n_bas.bin",
            "hi_x_bas.bin",
            "hi_n_1p1.bin",
            "hi_n_1p2.bin",
            "hi_n_2p1.bin",
            "hi_n_2p2.bin",
            "hi_x_1p1.bin",
            "hi_x_2p1.bin",
            "hi_x_2p2.bin",
            "hi_z_1p1.bin",
            "hi_z_2p1.bin",
            "hi_z_2p2.bin",
            "mv_n_bas.bin",
            "mv_x_bas.bin",
            "mv_n_1p1.bin",
            "mv_n_1p2.bin",
            "mv_n_2p1.bin",
            "mv_n_2p2.bin",
            "mv_x_1p1.bin",
            "mv_x_2p1.bin",
            "mv_x_2p2.bin",
            "mv_z_1p1.bin",
            "mv_z_2p1.bin",
            "mv_z_2p2.bin",
            "jo_n_bas.bin",
            "jo_x_bas.bin",
            "jo_x_bas.bin",
            "jo_n_1p1.bin",
            "jo_n_1p2.bin",
            "jo_n_2p1.bin",
            "jo_n_2p2.bin",
            "jo_x_1p1.bin",
            "jo_x_2p1.bin",
            "jo_x_2p2.bin",
            "jo_z_1p1.bin",
            "jo_z_2p1.bin",
            "jo_z_2p2.bin",
            "gt_n_bas.bin",
            "gt_x_bas.bin",
            "gt_z_bas.bin",
            "gt_n_1p1.bin",
            "gt_n_1p2.bin",
            "gt_n_2p1.bin",
            "gt_n_2p2.bin",
            "gt_x_1p1.bin",
            "gt_x_2p1.bin",
            "gt_x_2p2.bin",
            "gt_z_1p1.bin",
            "gt_z_2p1.bin",
            "gt_z_2p2.bin",
            "hu_n_bas.bin",
            "hu_x_bas.bin",
            "hu_z_bas.bin",
            "hu_n_1p1.bin",
            "hu_n_1p2.bin",
            "hu_n_2p1.bin",
            "hu_n_2p2.bin",
            "hu_x_1p1.bin",
            "hu_x_2p1.bin",
            "hu_x_2p2.bin",
            "hu_z_1p1.bin",
            "hu_z_2p1.bin",
            "hu_z_2p2.bin",
            "cl_n_bas.bin",
            "cl_x_bas.bin",
            "cl_x_bas.bin",
            "cl_n_1p1.bin",
            "cl_n_1p2.bin",
            "cl_n_2p1.bin",
            "cl_n_2p2.bin",
            "cl_x_1p1.bin",
            "cl_x_2p1.bin",
            "cl_x_2p2.bin",
            "cl_z_1p1.bin",
            "cl_z_2p1.bin",
            "cl_z_2p2.bin",
            "bo_e_bas.bin",
            "bo_x_bas.bin",
            "bo_z_bas.bin",
            "bo_e_1p1.bin",
            "bo_e_1p2.bin",
            "bo_e_2p1.bin",
            "bo_e_2p2.bin",
            "bo_x_1p1.bin",
            "bo_x_2p1.bin",
            "bo_x_2p2.bin",
            "bo_z_1p1.bin",
            "bo_z_2p1.bin",
            "bo_z_2p2.bin",
            "lj_n_1p1.bin",
            "lj_n_1p2.bin",
            "lj_n_2p1.bin",
            "lj_n_2p2.bin",
            "lj_x_1p1.bin",
            "lj_x_2p1.bin",
            "lj_x_2p2.bin",
            "lj_z_1p1.bin",
            "lj_z_2p1.bin",
            "lj_z_2p2.bin",
            "oa_n_bas.bin",
            "oa_x_bas.bin",
            "oa_n_1p1.bin",
            "oa_n_1p2.bin",
            "oa_n_2p1.bin",
            "oa_n_2p2.bin",
            "oa_x_1p1.bin",
            "oa_x_1p2.bin",
            "oa_x_2p1.bin",
            "oa_x_2p2.bin",
            "oa_z_1p1.bin",
            "oa_z_2p1.bin",
            "oa_z_2p2.bin",
            "hp_n_bas.bin",
            "hp_x_bas.bin",
            "hp_n_1p1.bin",
            "hp_n_1p2.bin",
            "hp_n_2p1.bin",
            "hp_n_2p2.bin",
            "hp_x_1p1.bin",
            "hp_x_2p1.bin",
            "hp_x_2p2.bin",
            "hp_z_1p1.bin",
            "hp_z_2p1.bin",
            "hp_z_2p2.bin",
            "br_n_bas.bin",
            "br_x_bas.bin",
            "br_n_1p1.bin",
            "br_n_1p2.bin",
            "br_n_2p1.bin",
            "br_n_2p2.bin",
            "br_x_1p1.bin",
            "br_x_2p1.bin",
            "br_x_2p2.bin",
            "br_z_1p1.bin",
            "br_z_2p1.bin",
            "br_z_2p2.bin",
            "bp_n_bas.bin",
            "bp_x_bas.bin",
            "bp_n_1p1.bin",
            "bp_n_1p2.bin",
            "bp_n_2p1.bin",
            "bp_n_2p2.bin",
            "bp_x_1p1.bin",
            "bp_x_2p1.bin",
            "bp_x_2p2.bin",
            "bp_z_1p1.bin",
            "bp_z_2p1.bin",
            "bp_z_2p2.bin",
            "md_n_bas.bin",
            "md_x_bas.bin",
            "md_n_1p1.bin",
            "md_n_1p2.bin",
            "md_n_2p1.bin",
            "md_n_2p2.bin",
            "md_x_1p1.bin",
            "md_x_2p1.bin",
            "md_x_2p2.bin",
            "md_z_1p1.bin",
            "md_z_2p1.bin",
            "md_z_2p2.bin",
            "sp_n_bas.bin",
            "sp_x_bas.bin",
            "sp_n_1p1.bin",
            "sp_n_1p2.bin",
            "sp_n_2p1.bin",
            "sp_n_2p2.bin",
            "sp_x_1p1.bin",
            "sp_x_2p1.bin",
            "sp_x_2p2.bin",
            "sp_z_1p1.bin",
            "sp_z_2p1.bin",
            "sp_z_2p2.bin",
            "lr_n_1p1.bin",
            "lr_n_1p2.bin",
            "lr_n_2p1.bin",
            "lr_n_2p2.bin",
            "lr_x_1p1.bin",
            "lr_x_2p1.bin",
            "lr_x_2p2.bin",
            "lr_z_1p1.bin",
            "lr_z_2p1.bin",
            "lr_z_2p2.bin",
            "p_riff1.bin",
            "p_riff2.bin",
            "p_riff3.bin",
            "sun_n_1p1.bin",
            "sun_n_1p2.bin",
            "sun_n_2p1.bin",
            "sun_n_2p2.bin",
            "sun_n_bas.bin",
            "bam_e_1p1.bin",
            "bam_e_1p2.bin",
            "bam_e_2p1.bin",
            "bam_e_2p2.bin",
            "bam_e_bas.bin",
            "spr_e_1p1.bin",
            "spr_e_1p2.bin",
            "spr_e_2p1.bin",
            "spr_e_2p2.bin",
            "spr_e_bas.bin",
            "sun_x_1p1.bin",
            "sun_x_1p2.bin",
            "sun_x_2p1.bin",
            "sun_x_2p2.bin",
            "sun_x_bas.bin",
            "bam_x_1p1.bin",
            "bam_x_1p2.bin",
            "bam_x_2p1.bin",
            "bam_x_2p2.bin",
            "bam_x_bas.bin",
            "spr_x_1p1.bin",
            "spr_x_1p2.bin",
            "spr_x_2p1.bin",
            "spr_x_2p2.bin",
            "spr_x_bas.bin",
        ]

    elif base_filename == "seqdata.dat":
        filename_lookup = {}

        for i in range(0, 1000):
            filename = "seq%03d" % (i)
            filename_lookup[get_filename_hash(filename)] = filename

            for p in ["", "prac", "easy", "norm", "real", "expr", "lnkn", "lnkx", "bnus"]:
                filename = "seq%03d%s" % (i, p)
                filename_lookup[get_filename_hash(filename)] = filename

            for p1 in ["", "1p", "2p", "1p1", "1p2", "2p1", "2p2", "bas"]:
                for p2 in ["", "bas", "pra", "nor", "exp", "ex1", "ex2", "ex3", "ex4"]:
                    filename = "seq%03d_%3s%3s" % (i, p1, p2)
                    filename_lookup[get_filename_hash(filename)] = filename

        filename_table = []
        with open("seqcode.dat", "rb") as infile:
            data = bytearray(infile.read())

            for i in range(0, len(data), 4):
                filename_hash = int.from_bytes(data[i:i+4], 'little')

                if filename_hash == 0xffffffff:
                    break

                filename_table.append(filename_lookup[filename_hash] + ".bin")

    output_path = args.output

    os.makedirs(output_path, exist_ok=True)

    with open(args.input, "rb") as infile:
        data = bytearray(infile.read())

        file_count = int.from_bytes(data[:4], 'little')
        cur_offset = 0x10

        for i in range(file_count):
            offset = int.from_bytes(data[cur_offset:cur_offset+4], 'little')
            cur_offset += 4

            chunk = data[offset & 0x7fffffff:]

            is_enc = (offset & 0x80000000) != 0

            output_filename = "%s" % (filename_table[i]) if filename_table and i < len(filename_table) else "output_%04d.bin" % i
            output_filename = os.path.join(output_path, output_filename)

            print("%08x: %s" % (offset & 0x7fffffff, output_filename))

            if is_enc:
                decoder = DecodeGfdm(chunk)
                chunk = decoder.decode()
                chunk = decode_lz(chunk)

            else:
                chunk = decode_lz(chunk)

            with open(output_filename, "wb") as outfile:
                outfile.write(chunk)
