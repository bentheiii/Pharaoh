from argparse import ArgumentParser

from pharaohlib import Phar

parser = ArgumentParser()

parser.add_argument('phar_path')
parser.add_argument('-del', action='set_true', default=False, dest='del_')


def main(args=None):
    args = parser.parse_args(args)
    phar = Phar.read(open(args.phar_path, 'rb'))
    managed = frozenset(v.file_name for v in phar.videos)
    for path in phar.destination_root.rglob('**/*.*'):
        if path.name in managed:
            continue
        if args.del_:
            path.unlink()
        print(path)


if __name__ == '__main__':
    main()
