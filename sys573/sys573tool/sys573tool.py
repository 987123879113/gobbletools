import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--mode', help='Operation mode', required=True, choices=['dump', 'build', 'checksum'])

    args, _ = parser.parse_known_args()

    if args.mode == "dump":
        import dump_sys573_gamefs
        dump_sys573_gamefs.main()

    elif args.mode == "build":
        import build_sys573_gamefs
        build_sys573_gamefs.main()

    elif args.mode == "checksum":
        import calc_checksum
        calc_checksum.main()

    else:
        print("Unknown mode:", args.mode)
